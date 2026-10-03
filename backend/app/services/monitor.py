from __future__ import annotations
import hashlib
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app.collectors.providers import collect
from app.core.config import get_settings
from app.models import Competitor, CompetitorPriceSnapshot, PricingEvent

settings = get_settings()


def detect_event(old: CompetitorPriceSnapshot | None, new: CompetitorPriceSnapshot, product_id: int, competitor_id: int) -> PricingEvent | None:
    if not old or not old.success or not new.success or old.price is None or new.price is None:
        return None
    price_pct = abs((new.price - old.price) / old.price * 100) if old.price else 0
    promo_changed = (old.promo_text or "") != (new.promo_text or "")
    if price_pct >= settings.price_change_trigger_percent:
        return PricingEvent(product_id=product_id, competitor_id=competitor_id, event_type="PRICE_CHANGE",
                            old_value=str(old.price), new_value=str(new.price))
    if promo_changed:
        return PricingEvent(product_id=product_id, competitor_id=competitor_id, event_type="PROMO_CHANGE",
                            old_value=old.promo_text, new_value=new.promo_text)
    return None


def collect_competitor(db: Session, competitor_id: int, advance: bool = False) -> tuple[CompetitorPriceSnapshot, PricingEvent | None]:
    c = db.get(Competitor, competitor_id)
    if not c:
        raise ValueError("competitor not found")
    old = db.scalar(select(CompetitorPriceSnapshot).where(
        CompetitorPriceSnapshot.competitor_id == c.id
    ).order_by(desc(CompetitorPriceSnapshot.collected_at)).limit(1))
    result = collect(c, advance=advance)
    raw_hash = hashlib.sha256((result.raw or result.error or "").encode()).hexdigest()
    snap = CompetitorPriceSnapshot(competitor_id=c.id, price=result.price, promo_text=result.promo_text,
                                   success=result.success, raw_hash=raw_hash)
    db.add(snap)
    db.flush()
    event = detect_event(old, snap, c.product_id, c.id)
    if event:
        db.add(event)
    db.commit()
    db.refresh(snap)
    if event:
        db.refresh(event)
    return snap, event


def monitor_all(db: Session) -> list[int]:
    event_ids = []
    competitors = db.scalars(
        select(Competitor).where(
            Competitor.active.is_(True),
            Competitor.source_type.notin_(["taobao", "google_shopping"]),
        )
    ).all()
    for c in competitors:
        _, event = collect_competitor(db, c.id, advance=False)
        if event:
            event_ids.append(event.id)
    return event_ids
