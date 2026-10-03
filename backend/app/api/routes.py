from __future__ import annotations

import csv
import io
import json
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.agent.runner import run_agent
from app.collectors.marketplace import MarketplaceCollectorError
from app.core.config import get_settings
from app.core.db import get_db
from app.llm.gateway import LLMClient
from app.models import (
    AgentRun,
    AgentToolCall,
    Competitor,
    CompetitorPriceSnapshot,
    PricingRecommendation,
    Product,
    SalesDaily,
)
from app.schemas.competitors import CompetitorCreate, CompetitorOut
from app.schemas.products import ProductCreate, ProductOut, ProductUpdate
from app.services.demo import advance_demo, seed_demo
from app.services.monitor import collect_competitor
from app.services.marketplace import get_latest_marketplace_competitors, search_and_store_marketplace

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.scalars(select(Product).order_by(Product.id)).all()


@router.post("/products", response_model=ProductOut)
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    row = Product(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    row = db.get(Product, product_id)
    if not row:
        raise HTTPException(404, "product not found")
    return row


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    row = db.get(Product, product_id)
    if not row:
        raise HTTPException(404, "product not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    row = db.get(Product, product_id)
    if not row:
        raise HTTPException(404, "product not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/products/{product_id}/sales/import")
async def import_sales(product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Product, product_id):
        raise HTTPException(404, "product not found")
    text = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    count = 0
    for row in reader:
        db.add(
            SalesDaily(
                product_id=product_id,
                sale_date=date.fromisoformat(row["sale_date"]),
                quantity=int(row["quantity"]),
                revenue=float(row.get("revenue") or 0),
            )
        )
        count += 1
    db.commit()
    return {"imported": count}


@router.get("/products/{product_id}/competitors", response_model=list[CompetitorOut])
def list_competitors(product_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(Competitor).where(
            Competitor.product_id == product_id,
            Competitor.active.is_(True),
        )
    ).all()


@router.post("/products/{product_id}/competitors", response_model=CompetitorOut)
def add_competitor(product_id: int, body: CompetitorCreate, db: Session = Depends(get_db)):
    if not db.get(Product, product_id):
        raise HTTPException(404, "product not found")
    data = body.model_dump(exclude={"mock_prices", "mock_promos"})
    row = Competitor(
        product_id=product_id,
        **data,
        mock_prices_json=json.dumps(body.mock_prices),
        mock_promos_json=json.dumps(body.mock_promos),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/products/{product_id}/competitors/marketplace/latest")
def latest_marketplace_competitors(product_id: int, db: Session = Depends(get_db)):
    try:
        return get_latest_marketplace_competitors(db, product_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/products/{product_id}/competitors/search-marketplace")
async def search_marketplace_competitors(product_id: int, db: Session = Depends(get_db)):
    try:
        return await search_and_store_marketplace(db, product_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except MarketplaceCollectorError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post("/competitors/{competitor_id}/collect")
def collect_one(competitor_id: int, advance: bool = False, db: Session = Depends(get_db)):
    competitor = db.get(Competitor, competitor_id)
    if competitor and competitor.source_type in {"taobao", "google_shopping"}:
        raise HTTPException(400, "外部电商竞品仅支持商品级手动查询接口")
    try:
        snap, event = collect_competitor(db, competitor_id, advance=advance)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "snapshot_id": snap.id,
        "price": snap.price,
        "promo_text": snap.promo_text,
        "success": snap.success,
        "event_id": event.id if event else None,
    }


@router.get("/products/{product_id}/price-history")
def price_history(product_id: int, db: Session = Depends(get_db)):
    comps = db.scalars(
        select(Competitor).where(
            Competitor.product_id == product_id,
            Competitor.active.is_(True),
        )
    ).all()
    output = []
    for competitor in comps:
        snaps = db.scalars(
            select(CompetitorPriceSnapshot)
            .where(CompetitorPriceSnapshot.competitor_id == competitor.id)
            .order_by(CompetitorPriceSnapshot.collected_at)
        ).all()
        output.append(
            {
                "competitor_id": competitor.id,
                "name": competitor.name,
                "source_type": competitor.source_type,
                "points": [
                    {
                        "time": snap.collected_at.isoformat(),
                        "price": snap.price,
                        "promo": snap.promo_text,
                        "sales": snap.sales,
                        "success": snap.success,
                    }
                    for snap in snaps
                ],
            }
        )
    return output


@router.post("/products/{product_id}/analyze")
async def analyze(product_id: int, event_id: int | None = None, db: Session = Depends(get_db)):
    try:
        rec = await run_agent(db, product_id, event_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return recommendation_to_dict(rec)


@router.get("/products/{product_id}/recommendations")
def recommendations(product_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(PricingRecommendation)
        .join(AgentRun, AgentRun.id == PricingRecommendation.run_id)
        .where(AgentRun.product_id == product_id)
        .order_by(desc(PricingRecommendation.created_at))
    ).all()
    return [recommendation_to_dict(row) for row in rows]


@router.post("/recommendations/{rec_id}/accept")
def accept(rec_id: int, db: Session = Depends(get_db)):
    row = db.get(PricingRecommendation, rec_id)
    if not row:
        raise HTTPException(404, "recommendation not found")
    row.status = "accepted"
    db.commit()
    return {"ok": True}


@router.post("/recommendations/{rec_id}/reject")
def reject(rec_id: int, db: Session = Depends(get_db)):
    row = db.get(PricingRecommendation, rec_id)
    if not row:
        raise HTTPException(404, "recommendation not found")
    row.status = "rejected"
    db.commit()
    return {"ok": True}


@router.get("/products/{product_id}/runs")
def runs(product_id: int, db: Session = Depends(get_db)):
    run_rows = db.scalars(
        select(AgentRun).where(AgentRun.product_id == product_id).order_by(desc(AgentRun.started_at))
    ).all()
    output = []
    for run in run_rows:
        calls = db.scalars(
            select(AgentToolCall).where(AgentToolCall.run_id == run.id).order_by(AgentToolCall.id)
        ).all()
        output.append(
            {
                "id": run.id,
                "status": run.status,
                "provider": run.provider,
                "model": run.model,
                "step_count": run.step_count,
                "started_at": run.started_at.isoformat(),
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "error": run.error,
                "tool_calls": [
                    {
                        "tool_name": call.tool_name,
                        "arguments": json.loads(call.arguments_json),
                        "result_summary": call.result_summary,
                        "success": call.success,
                        "duration_ms": call.duration_ms,
                    }
                    for call in calls
                ],
            }
        )
    return output


@router.post("/settings/llm/test")
async def llm_test():
    settings = get_settings()
    if not settings.llm_configured:
        return {"ok": False, "error": "LLM not configured", "model": settings.llm_model}
    try:
        response = await LLMClient().chat([{"role": "user", "content": "只回复 OK"}])
        return {"ok": True, "model": settings.llm_model, "reply": response.text[:200]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300], "model": settings.llm_model}


@router.post("/demo/seed")
def demo_seed(db: Session = Depends(get_db)):
    product = seed_demo(db)
    return {"product_id": product.id}


@router.post("/demo/products/{product_id}/advance")
def demo_advance(product_id: int, db: Session = Depends(get_db)):
    return {"results": advance_demo(db, product_id)}


def recommendation_to_dict(row: PricingRecommendation):
    return {
        "id": row.id,
        "run_id": row.run_id,
        "action": row.action,
        "suggested_price": row.suggested_price,
        "promotion": json.loads(row.promotion_json),
        "evidence_summary": json.loads(row.evidence_json),
        "risk_notes": json.loads(row.risks_json),
        "data_completeness": row.data_completeness,
        "next_check_after_hours": row.next_check_after_hours,
        "need_user_inputs": json.loads(row.need_user_inputs_json),
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    }
