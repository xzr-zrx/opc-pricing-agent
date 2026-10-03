from __future__ import annotations
import json
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Competitor, Product, SalesDaily
from app.services.monitor import collect_competitor


def seed_demo(db: Session) -> Product:
    existing = db.scalar(select(Product).where(Product.sku == "DEMO-TSHIRT"))
    if existing:
        return existing
    p = Product(name="毕业纪念 T 恤", sku="DEMO-TSHIRT", cost=32, current_price=59,
                min_margin_rate=0.30, stock=120, active=True)
    db.add(p); db.flush()
    configs = [
        ("竞品 A", [59,49,49], ["", "限时直降", "限时直降"]),
        ("竞品 B", [55,55,55], ["", "", "第二件优惠"]),
        ("竞品 C", [62,62,58], ["", "", "小幅降价"]),
    ]
    comps=[]
    for name, prices, promos in configs:
        c=Competitor(product_id=p.id,name=name,source_type="mock",mock_prices_json=json.dumps(prices),mock_promos_json=json.dumps(promos),mock_index=0)
        db.add(c); comps.append(c)
    for i, qty in enumerate([10,9,8,8,7,6,5]):
        d = date.today() - timedelta(days=6-i)
        db.add(SalesDaily(product_id=p.id, sale_date=d, quantity=qty, revenue=qty*p.current_price))
    db.commit(); db.refresh(p)
    for c in comps:
        db.refresh(c); collect_competitor(db,c.id,advance=False)
    return p


def advance_demo(db: Session, product_id: int) -> list[dict]:
    comps = db.scalars(select(Competitor).where(Competitor.product_id==product_id, Competitor.source_type=="mock")).all()
    out=[]
    for c in comps:
        snap,event = collect_competitor(db,c.id,advance=True)
        out.append({"competitor_id":c.id,"price":snap.price,"promo_text":snap.promo_text,"event_id":event.id if event else None})
    return out
