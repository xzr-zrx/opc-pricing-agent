from __future__ import annotations
import json, time
from datetime import datetime
from sqlalchemy.orm import Session
from app.agent.prompts import JSON_FALLBACK_PROMPT, SYSTEM_PROMPT
from app.core.config import get_settings
from app.llm.gateway import LLMClient
from app.models import AgentRun, AgentToolCall, PricingEvent, PricingRecommendation, Product
from app.schemas.common import RecommendationPayload
from app.tools.pricing_tools import TOOL_SCHEMAS, calculate_margin, execute_tool, get_competitor_context, get_inventory_status, get_sales_summary, min_safe_price, simulate_pricing_options

settings = get_settings()


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


def _demo_agent(db: Session, run: AgentRun, product: Product) -> PricingRecommendation:
    # 演示 fallback 依然严格走“调用工具 -> 观察 -> 决策”并写审计。
    def call(name, args):
        t = time.perf_counter(); ok = True; result = None
        try:
            result = execute_tool(db, name, args); return result
        except Exception:
            ok = False; raise
        finally:
            _persist_tool(db, run.id, name, args, result, ok, int((time.perf_counter()-t)*1000))

    comp = call("get_competitor_context", {"product_id": product.id})
    sales = call("get_sales_summary", {"product_id": product.id, "days": 7})
    inventory = call("get_inventory_status", {"product_id": product.id})
    floor = min_safe_price(product)
    comp_prices = [c["current_price"] for c in comp["competitors"] if c.get("current_price")]
    min_comp = min(comp_prices) if comp_prices else product.current_price
    target = max(floor, round(min(product.current_price * 0.95, max(min_comp + 3, product.current_price * 0.9)), 2))
    sims = call("simulate_pricing_options", {"product_id": product.id, "candidate_list": [product.current_price, target], "strategy": "compare"})
    data_low = sales["data_days"] < 3
    if data_low:
        rec = RecommendationPayload(
            action="NEED_MORE_DATA", suggested_price=None,
            evidence_summary=[f"当前库存 {product.stock} 件", f"竞品最低价约 {min_comp:.2f} 元"],
            risk_notes=["近期销量数据不足，不建议仅凭竞品价格机械跟价"], data_completeness="LOW",
            need_user_inputs=["补充至少 3 天销量数据"], next_check_after_hours=12,
        )
    elif min_comp <= product.current_price * 0.9 and inventory.get("estimated_days_cover") and inventory["estimated_days_cover"] > 20:
        rec = RecommendationPayload(
            action="ADJUST_PRICE", suggested_price=target,
            evidence_summary=[f"竞品最低价约 {min_comp:.2f} 元", f"近7日销量趋势 {sales['trend']} ({sales['trend_percent']}%)", f"库存预计可售 {inventory['estimated_days_cover']} 天", f"安全底价 {floor:.2f} 元"],
            risk_notes=["不建议直接跟到竞品最低价，避免毛利过度压缩"], data_completeness="HIGH", next_check_after_hours=12,
        )
    else:
        rec = RecommendationPayload(
            action="KEEP_PRICE", suggested_price=product.current_price,
            evidence_summary=[f"竞品最低价约 {min_comp:.2f} 元", f"近7日销量趋势 {sales['trend']}", f"安全底价 {floor:.2f} 元"],
            risk_notes=["市场变化尚不足以支持更激进调价"], data_completeness="HIGH", next_check_after_hours=24,
        )
    run.step_count = 4
    return _persist_recommendation(db, run, _validate_recommendation(product, rec))


async def run_agent(db: Session, product_id: int, event_id: int | None = None) -> PricingRecommendation:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("product not found")
    run = AgentRun(product_id=product_id, event_id=event_id,
                   provider=settings.llm_provider if settings.llm_configured else "demo_fallback",
                   model=settings.llm_model if settings.llm_configured else "deterministic-demo")
    db.add(run); db.commit(); db.refresh(run)

    if not settings.llm_configured:
        if settings.demo_fallback_enabled:
            return _demo_agent(db, run, product)
        run.status = "failed"; run.error = "LLM not configured"; run.finished_at = datetime.utcnow(); db.commit()
        raise RuntimeError("LLM not configured")

    client = LLMClient()
    event = db.get(PricingEvent, event_id) if event_id else None
    context = {
        "product_id": product.id, "name": product.name, "current_price": product.current_price,
        "cost": product.cost, "min_margin_rate": product.min_margin_rate, "stock": product.stock,
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
            # Native 模式下期望直接返回 Recommendation JSON。
            if native_mode:
                rec = RecommendationPayload.model_validate_json(text)
                return _persist_recommendation(db, run, _validate_recommendation(product, rec))

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
            return _demo_agent(db, fallback_run, product)
        raise
