from __future__ import annotations
import json, time
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from app.agent.prompts import JSON_FALLBACK_PROMPT, SYSTEM_PROMPT
from app.core.config import get_settings
from app.llm.gateway import LLMClient
from app.models import AgentRun, AgentToolCall, PricingEvent, PricingRecommendation, Product
from app.schemas.common import RecommendationPayload
from app.tools.pricing_tools import TOOL_SCHEMAS, execute_tool, min_safe_price

settings = get_settings()

def _extract_json_object(text: str) -> dict:
    """兼容纯 JSON、```json ... ``` 和前后带少量解释文字的模型输出。"""
    cleaned = (text or "").strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].strip().lower() in ("```json", "```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError(
                f"模型没有返回有效 JSON: {cleaned[:500]}"
            )

        return json.loads(cleaned[start:end + 1])
def _persist_tool(db: Session, run_id: int, name: str, args: dict, result: dict | None, ok: bool, duration_ms: int):
    db.add(AgentToolCall(run_id=run_id, tool_name=name, arguments_json=json.dumps(args, ensure_ascii=False),
                         result_summary=json.dumps(result, ensure_ascii=False)[:1500] if result else None,
                         success=ok, duration_ms=duration_ms))
    db.commit()


def _validate_recommendation(product: Product, rec: RecommendationPayload) -> RecommendationPayload:
    floor = min_safe_price(product)
    if rec.suggested_price is not None:
        if rec.suggested_price < floor:
            raise ValueError(f"suggested price {rec.suggested_price} below safe floor {floor}")
        pct = abs((rec.suggested_price - product.current_price) / product.current_price * 100)
        if pct > settings.default_max_price_change_percent:
            rec.risk_notes.append(f"单次调价幅度 {pct:.1f}% 超过默认 {settings.default_max_price_change_percent:.0f}% ，需人工特别确认")
    return rec


def _persist_recommendation(db: Session, run: AgentRun, rec: RecommendationPayload) -> PricingRecommendation:
    row = PricingRecommendation(
        run_id=run.id, action=rec.action, suggested_price=rec.suggested_price,
        promotion_json=json.dumps(rec.promotion, ensure_ascii=False),
        evidence_json=json.dumps(rec.evidence_summary, ensure_ascii=False),
        risks_json=json.dumps(rec.risk_notes, ensure_ascii=False),
        data_completeness=rec.data_completeness,
        next_check_after_hours=rec.next_check_after_hours,
        need_user_inputs_json=json.dumps(rec.need_user_inputs, ensure_ascii=False),
    )
    db.add(row)
    run.status = "succeeded"
    run.finished_at = datetime.utcnow()
    db.commit(); db.refresh(row)
    return row


def _demo_agent(
    db: Session,
    run: AgentRun,
    product: Product,
    analysis_start: date,
    analysis_end: date,
) -> PricingRecommendation:
    """确定性 fallback：仍严格走工具，并把最近7天真实趋势纳入定价。"""
    def call(name, args):
        t = time.perf_counter(); ok = True; result = None
        try:
            result = execute_tool(db, name, args); return result
        except Exception:
            ok = False; raise
        finally:
            _persist_tool(db, run.id, name, args, result, ok, int((time.perf_counter()-t)*1000))

    comp = call("get_competitor_context", {"product_id": product.id})
    trend = call(
        "get_price_trend",
        {
            "product_id": product.id,
            "start_date": analysis_start.isoformat(),
            "end_date": analysis_end.isoformat(),
        },
    )
    sales = call("get_sales_summary", {"product_id": product.id, "days": 7})
    inventory = call("get_inventory_status", {"product_id": product.id})
    current_margin = call("calculate_margin", {"product_id": product.id, "candidate_price": product.current_price})

    floor = min_safe_price(product)
    comp_prices = [
        float(c.get("current_price") or c.get("current_price_cny"))
        for c in comp.get("competitors", [])
        if c.get("current_price") is not None or c.get("current_price_cny") is not None
    ]
    market_stats = comp.get("market_stats") or {}
    trend_summary = trend.get("summary") or {}
    market_avg = (
        trend_summary.get("latest_market_avg_price")
        or market_stats.get("average_price")
        or (round(sum(comp_prices) / len(comp_prices), 2) if comp_prices else None)
    )
    market_min = market_stats.get("min_price") or (min(comp_prices) if comp_prices else None)
    market_max = market_stats.get("max_price") or (max(comp_prices) if comp_prices else None)
    trend_direction = trend_summary.get("trend") or "insufficient"
    trend_percent = trend_summary.get("trend_percent")
    price_gap_percent = (
        round((product.current_price - market_avg) / market_avg * 100, 2)
        if market_avg
        else None
    )

    # 先生成受安全底价和单次10%调价约束保护的候选价格。
    target = float(product.current_price)
    strategy = "稳定观察"
    action = "KEEP_PRICE"
    stock_pressure = product.stock >= 80 or (inventory.get("estimated_days_cover") or 0) > 20
    if market_avg is not None and price_gap_percent is not None:
        if price_gap_percent > 8 and stock_pressure:
            target = max(floor, min(product.current_price * 0.95, market_avg * 1.05))
            strategy = "适度降价"
            action = "ADJUST_PRICE"
        elif trend_direction == "up" and price_gap_percent < -5:
            target = max(floor, min(product.current_price * 1.03, market_avg))
            strategy = "小幅提价"
            action = "ADJUST_PRICE"
        elif stock_pressure and price_gap_percent > 3:
            target = max(floor, product.current_price * 0.97)
            strategy = "限时促销"
            action = "LIMITED_PROMOTION"

    min_allowed = product.current_price * (1 - settings.default_max_price_change_percent / 100)
    max_allowed = product.current_price * (1 + settings.default_max_price_change_percent / 100)
    target = round(max(floor, min(max(target, min_allowed), max_allowed)), 2)
    if abs(target - product.current_price) < 0.01:
        action = "KEEP_PRICE"
        strategy = "稳定观察"
        target = float(product.current_price)

    sims = call(
        "simulate_pricing_options",
        {"product_id": product.id, "candidate_list": [product.current_price, target], "strategy": "7_day_market_compare"},
    )
    target_option = next((x for x in sims["options"] if abs(x["candidate_price"] - target) < 0.011), sims["options"][-1])

    evidence = []
    if market_avg is not None:
        evidence.append(
            f"当前售价 {product.current_price:.2f} 元，最近可用市场参考均价约 {market_avg:.2f} 元，价差约 {price_gap_percent:.1f}%。"
        )
    if trend_direction != "insufficient" and trend_percent is not None:
        direction_text = {"up": "上涨", "down": "下降", "stable": "平稳"}.get(trend_direction, trend_direction)
        evidence.append(
            f"所选7天窗口内竞品市场均价趋势为{direction_text}，首末均价变化约 {trend_percent:.1f}%。"
        )
    else:
        evidence.append("真实竞品历史不足2个有效日期，本次趋势结论主要依赖当前竞品快照，不补造缺失历史。")
    evidence.append(
        f"当前成本 {product.cost:.2f} 元，安全底价 {floor:.2f} 元；建议价 {target:.2f} 元对应毛利率约 {target_option['margin_rate'] * 100:.1f}%。"
    )
    cover = inventory.get("estimated_days_cover")
    evidence.append(
        f"当前库存 {product.stock} 件" + (f"，按近7日销量估算可售约 {cover} 天。" if cover is not None else "；当前销量不足以可靠估算可售天数。")
    )

    risks = ["当前竞品样本仅代表已成功采集的拼多多搜索结果，不代表拼多多全平台绝对销量或全量价格。"]
    if trend.get("history_insufficient"):
        risks.append("真实7天历史样本不足，建议继续每日采集后再提高趋势判断权重。")
    if action in {"ADJUST_PRICE", "LIMITED_PROMOTION"}:
        risks.append("不建议直接跟随单个最低价，需持续观察调价后的销量和毛利变化。")

    market_days = int(trend_summary.get("market_data_days") or 0)
    completeness = "HIGH" if market_days >= 3 and sales["data_days"] >= 3 and comp_prices else "MEDIUM" if comp_prices else "LOW"
    confidence = 0.86 if completeness == "HIGH" else 0.72 if completeness == "MEDIUM" else 0.5
    risk_level = "LOW" if action == "KEEP_PRICE" and completeness == "HIGH" else "MEDIUM"
    summary = (
        f"建议将售价由 {product.current_price:.2f} 元调整至 {target:.2f} 元，采用“{strategy}”策略，在不低于安全底价的前提下兼顾市场竞争力与利润空间。"
        if action != "KEEP_PRICE"
        else f"建议暂时维持 {product.current_price:.2f} 元，采用“稳定观察”策略，并继续补充真实7天竞品历史后再评估调价。"
    )

    rec = RecommendationPayload(
        action=action,
        suggested_price=target,
        promotion={
            "strategy": strategy,
            "summary": summary,
            "confidence": confidence,
            "risk_level": risk_level,
            "analysis_window": {"start_date": analysis_start.isoformat(), "end_date": analysis_end.isoformat()},
            "key_metrics": {
                "current_price": float(product.current_price),
                "cost": float(product.cost),
                "current_margin_rate": current_margin["margin_rate"],
                "min_safe_price": floor,
                "market_avg_price": market_avg,
                "market_min_price": market_min,
                "market_max_price": market_max,
                "market_trend": trend_direction,
                "market_trend_percent": trend_percent,
                "market_data_days": market_days,
                "stock": product.stock,
                "estimated_days_cover": cover,
                "sales_trend": sales["trend"],
            },
        },
        evidence_summary=evidence,
        risk_notes=risks,
        data_completeness=completeness,
        next_check_after_hours=12 if action != "KEEP_PRICE" else 24,
        need_user_inputs=[],
    )
    run.step_count = 6
    return _persist_recommendation(db, run, _validate_recommendation(product, rec))


async def run_agent(
    db: Session,
    product_id: int,
    event_id: int | None = None,
    analysis_start: date | None = None,
    analysis_end: date | None = None,
) -> PricingRecommendation:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    analysis_end = analysis_end or date.today()
    analysis_start = analysis_start or (analysis_end - timedelta(days=6))
    if analysis_end < analysis_start or (analysis_end - analysis_start).days + 1 > 7:
        raise ValueError("Agent 单次分析窗口必须为最多7天")
    run = AgentRun(product_id=product_id, event_id=event_id,
                   provider=settings.llm_provider if settings.llm_configured else "demo_fallback",
                   model=settings.llm_model if settings.llm_configured else "deterministic-demo")
    db.add(run); db.commit(); db.refresh(run)

    if not settings.llm_configured:
        if settings.demo_fallback_enabled:
            return _demo_agent(db, run, product, analysis_start, analysis_end)
        run.status = "failed"; run.error = "LLM not configured"; run.finished_at = datetime.utcnow(); db.commit()
        raise RuntimeError("LLM not configured")

    client = LLMClient()
    event = db.get(PricingEvent, event_id) if event_id else None
    context = {
        "product_id": product.id, "name": product.name, "current_price": product.current_price,
        "cost": product.cost, "min_margin_rate": product.min_margin_rate, "stock": product.stock,
        "analysis_window": {"start_date": analysis_start.isoformat(), "end_date": analysis_end.isoformat()},
        "event": {"type": event.event_type, "old": event.old_value, "new": event.new_value} if event else {"type":"MANUAL_ANALYZE"},
    }
    native_mode = settings.llm_native_tool_calling
    messages = [
        {"role":"system", "content": SYSTEM_PROMPT + ("" if native_mode else "\n" + JSON_FALLBACK_PROMPT)},
        {"role":"user", "content": "请分析以下最小上下文。需要事实时调用工具，最后输出建议。\n" + json.dumps(context, ensure_ascii=False)}
    ]
    try:
        for step in range(1, settings.agent_max_steps + 1):
            run.step_count = step; db.commit()
            try:
                response = await client.chat(messages, tools=TOOL_SCHEMAS if native_mode else None)
            except Exception:
                # 某些第三方中转站支持普通对话但不转发 tools。原生工具调用失败时，
                # 在同一个 Agent Run 中自动降级到 JSON Action 模式，而不是让业务层感知供应商差异。
                if native_mode:
                    native_mode = False
                    messages[0]["content"] = SYSTEM_PROMPT + "\n" + JSON_FALLBACK_PROMPT
                    response = await client.chat(messages, tools=None)
                else:
                    raise
            if response.tool_calls:
                messages.append({"role":"assistant", "content": response.text or None,
                                 "tool_calls":[{"id":tc.id,"type":"function","function":{"name":tc.name,"arguments":json.dumps(tc.arguments, ensure_ascii=False)}} for tc in response.tool_calls]})
                for tc in response.tool_calls:
                    start=time.perf_counter(); ok=True; result=None
                    try:
                        result=execute_tool(db, tc.name, tc.arguments)
                    except Exception as e:
                        ok=False; result={"error":str(e)}
                    _persist_tool(db, run.id, tc.name, tc.arguments, result, ok, int((time.perf_counter()-start)*1000))
                    messages.append({"role":"tool","tool_call_id":tc.id,"content":json.dumps(result, ensure_ascii=False)})
                continue

            text = response.text.strip()

            # Native 模式下模型已经不再调用工具，
            # 此时应返回最终 Recommendation。
            if native_mode:
                try:
                    obj = _extract_json_object(text)
                    rec = RecommendationPayload.model_validate(obj)

                except Exception as first_error:
                    # 按规格允许一次格式修复请求
                    repair_prompt = f"""
            你刚才的最终结果不符合规定格式。

            错误：
            {str(first_error)}

            你必须重新输出且只输出一个 JSON 对象。
            禁止 Markdown 代码块，禁止解释文字。

            严格使用下面结构：

            {{
            "action": "KEEP_PRICE | ADJUST_PRICE | LIMITED_PROMOTION | BUNDLE_PROMOTION | NEED_MORE_DATA | PAUSE_AND_OBSERVE",
            "suggested_price": 55.0,
            "promotion": {{
                "strategy": "稳定观察",
                "summary": "一句话最终结论",
                "confidence": 0.8,
                "risk_level": "MEDIUM",
                "analysis_window": {{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}},
                "key_metrics": {{}}
            }},
            "evidence_summary": [
                "证据1",
                "证据2"
            ],
            "risk_notes": [
                "风险1"
            ],
            "data_completeness": "HIGH",
            "next_check_after_hours": 12,
            "need_user_inputs": []
            }}

            特别注意：
            1. action 必须是上述六个英文枚举值之一。
            2. action 不能是对象。
            3. suggested_price 只能是数字或 null。
            4. evidence_summary 和 risk_notes 必须是字符串数组。
            5. 只返回 JSON。
            """

                    repair_messages = messages + [
                        {
                            "role": "assistant",
                            "content": text
                        },
                        {
                            "role": "user",
                            "content": repair_prompt
                        }
                    ]

                    repaired = await client.chat(
                        repair_messages,
                        tools=None
                    )

                    repaired_obj = _extract_json_object(repaired.text)

                    rec = RecommendationPayload.model_validate(
                        repaired_obj
                    )

                return _persist_recommendation(
                    db,
                    run,
                    _validate_recommendation(product, rec)
                )

            # JSON action fallback
            obj = json.loads(text)
            if obj.get("action") == "final":
                rec = RecommendationPayload.model_validate(obj["result"])
                return _persist_recommendation(db, run, _validate_recommendation(product, rec))
            name = obj.get("action"); args = obj.get("arguments") or {}
            start=time.perf_counter(); ok=True; result=None
            try:
                result=execute_tool(db, name, args)
            except Exception as e:
                ok=False; result={"error":str(e)}
            _persist_tool(db, run.id, name, args, result, ok, int((time.perf_counter()-start)*1000))
            messages.append({"role":"assistant","content":text})
            messages.append({"role":"user","content":"工具观察：" + json.dumps(result, ensure_ascii=False) + "\n" + JSON_FALLBACK_PROMPT})
        raise RuntimeError("Agent exceeded max_steps")
    except Exception as e:
        run.status="failed"; run.error=str(e)[:1000]; run.finished_at=datetime.utcnow(); db.commit()
        if settings.demo_fallback_enabled:
            fallback_run = AgentRun(product_id=product_id, event_id=event_id, provider="demo_fallback_after_llm_error", model="deterministic-demo")
            db.add(fallback_run); db.commit(); db.refresh(fallback_run)
            return _demo_agent(db, fallback_run, product, analysis_start, analysis_end)
        raise
