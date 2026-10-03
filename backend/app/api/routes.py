from __future__ import annotations
import csv, io, json
from datetime import date
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app.agent.runner import run_agent
from app.core.config import get_settings
from app.core.db import get_db
from app.llm.gateway import LLMClient
from app.models import AgentRun, AgentToolCall, Competitor, CompetitorPriceSnapshot, PricingEvent, PricingRecommendation, Product, SalesDaily
from app.schemas.competitors import CompetitorCreate, CompetitorOut
from app.schemas.products import ProductCreate, ProductOut, ProductUpdate
from app.services.demo import advance_demo, seed_demo
from app.services.monitor import collect_competitor

router = APIRouter(prefix="/api")

@router.get("/health")
def health(): return {"ok":True}

@router.get("/products", response_model=list[ProductOut])
def list_products(db:Session=Depends(get_db)):
    return db.scalars(select(Product).order_by(Product.id)).all()

@router.post("/products", response_model=ProductOut)
def create_product(body:ProductCreate, db:Session=Depends(get_db)):
    row=Product(**body.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id:int, db:Session=Depends(get_db)):
    row=db.get(Product,product_id)
    if not row: raise HTTPException(404,"product not found")
    return row

@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id:int, body:ProductUpdate, db:Session=Depends(get_db)):
    row=db.get(Product,product_id)
    if not row: raise HTTPException(404,"product not found")
    for k,v in body.model_dump(exclude_unset=True).items(): setattr(row,k,v)
    db.commit(); db.refresh(row); return row

@router.delete("/products/{product_id}")
def delete_product(product_id:int, db:Session=Depends(get_db)):
    row=db.get(Product,product_id)
    if not row: raise HTTPException(404,"product not found")
    db.delete(row); db.commit(); return {"ok":True}

@router.post("/products/{product_id}/sales/import")
async def import_sales(product_id:int, file:UploadFile=File(...), db:Session=Depends(get_db)):
    if not db.get(Product,product_id): raise HTTPException(404,"product not found")
    text=(await file.read()).decode("utf-8-sig")
    reader=csv.DictReader(io.StringIO(text)); count=0
    for r in reader:
        db.add(SalesDaily(product_id=product_id,sale_date=date.fromisoformat(r["sale_date"]),quantity=int(r["quantity"]),revenue=float(r.get("revenue") or 0))); count+=1
    db.commit(); return {"imported":count}

@router.get("/products/{product_id}/competitors", response_model=list[CompetitorOut])
def list_competitors(product_id:int, db:Session=Depends(get_db)):
    return db.scalars(select(Competitor).where(Competitor.product_id==product_id)).all()

@router.post("/products/{product_id}/competitors", response_model=CompetitorOut)
def add_competitor(product_id:int, body:CompetitorCreate, db:Session=Depends(get_db)):
    if not db.get(Product,product_id): raise HTTPException(404,"product not found")
    d=body.model_dump(exclude={"mock_prices","mock_promos"})
    row=Competitor(product_id=product_id,**d,mock_prices_json=json.dumps(body.mock_prices),mock_promos_json=json.dumps(body.mock_promos))
    db.add(row); db.commit(); db.refresh(row); return row

@router.post("/competitors/{competitor_id}/collect")
def collect_one(competitor_id:int, advance:bool=False, db:Session=Depends(get_db)):
    try: snap,event=collect_competitor(db,competitor_id,advance=advance)
    except ValueError as e: raise HTTPException(404,str(e))
    return {"snapshot_id":snap.id,"price":snap.price,"promo_text":snap.promo_text,"success":snap.success,"event_id":event.id if event else None}

@router.get("/products/{product_id}/price-history")
def price_history(product_id:int, db:Session=Depends(get_db)):
    comps=db.scalars(select(Competitor).where(Competitor.product_id==product_id)).all(); out=[]
    for c in comps:
        snaps=db.scalars(select(CompetitorPriceSnapshot).where(CompetitorPriceSnapshot.competitor_id==c.id).order_by(CompetitorPriceSnapshot.collected_at)).all()
        out.append({"competitor_id":c.id,"name":c.name,"points":[{"time":s.collected_at.isoformat(),"price":s.price,"promo":s.promo_text,"success":s.success} for s in snaps]})
    return out

@router.post("/products/{product_id}/analyze")
async def analyze(product_id:int, event_id:int|None=None, db:Session=Depends(get_db)):
    try: rec=await run_agent(db,product_id,event_id)
    except ValueError as e: raise HTTPException(404,str(e))
    return recommendation_to_dict(rec)

@router.get("/products/{product_id}/recommendations")
def recommendations(product_id:int, db:Session=Depends(get_db)):
    rows=db.scalars(select(PricingRecommendation).join(AgentRun,AgentRun.id==PricingRecommendation.run_id).where(AgentRun.product_id==product_id).order_by(desc(PricingRecommendation.created_at))).all()
    return [recommendation_to_dict(r) for r in rows]

@router.post("/recommendations/{rec_id}/accept")
def accept(rec_id:int,db:Session=Depends(get_db)):
    r=db.get(PricingRecommendation,rec_id)
    if not r: raise HTTPException(404,"recommendation not found")
    r.status="accepted"; db.commit(); return {"ok":True}

@router.post("/recommendations/{rec_id}/reject")
def reject(rec_id:int,db:Session=Depends(get_db)):
    r=db.get(PricingRecommendation,rec_id)
    if not r: raise HTTPException(404,"recommendation not found")
    r.status="rejected"; db.commit(); return {"ok":True}

@router.get("/products/{product_id}/runs")
def runs(product_id:int,db:Session=Depends(get_db)):
    rs=db.scalars(select(AgentRun).where(AgentRun.product_id==product_id).order_by(desc(AgentRun.started_at))).all(); out=[]
    for r in rs:
        calls=db.scalars(select(AgentToolCall).where(AgentToolCall.run_id==r.id).order_by(AgentToolCall.id)).all()
        out.append({"id":r.id,"status":r.status,"provider":r.provider,"model":r.model,"step_count":r.step_count,"started_at":r.started_at.isoformat(),"finished_at":r.finished_at.isoformat() if r.finished_at else None,"error":r.error,
                    "tool_calls":[{"tool_name":c.tool_name,"arguments":json.loads(c.arguments_json),"result_summary":c.result_summary,"success":c.success,"duration_ms":c.duration_ms} for c in calls]})
    return out

@router.post("/settings/llm/test")
async def llm_test():
    s=get_settings()
    if not s.llm_configured: return {"ok":False,"error":"LLM not configured","model":s.llm_model}
    try:
        r=await LLMClient().chat([{"role":"user","content":"只回复 OK"}])
        return {"ok":True,"model":s.llm_model,"reply":r.text[:200]}
    except Exception as e: return {"ok":False,"error":str(e)[:300],"model":s.llm_model}

@router.post("/demo/seed")
def demo_seed(db:Session=Depends(get_db)):
    p=seed_demo(db); return {"product_id":p.id}

@router.post("/demo/products/{product_id}/advance")
def demo_advance(product_id:int,db:Session=Depends(get_db)):
    return {"results":advance_demo(db,product_id)}

def recommendation_to_dict(r:PricingRecommendation):
    return {"id":r.id,"run_id":r.run_id,"action":r.action,"suggested_price":r.suggested_price,"promotion":json.loads(r.promotion_json),"evidence_summary":json.loads(r.evidence_json),"risk_notes":json.loads(r.risks_json),"data_completeness":r.data_completeness,"next_check_after_hours":r.next_check_after_hours,"need_user_inputs":json.loads(r.need_user_inputs_json),"status":r.status,"created_at":r.created_at.isoformat()}
