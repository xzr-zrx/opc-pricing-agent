from __future__ import annotations
import asyncio
try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:  # 允许未安装依赖时先启动 API；正式安装 requirements 后会启用调度器
    BackgroundScheduler = None

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.monitor import monitor_all
from app.agent.runner import run_agent

settings=get_settings()
scheduler=BackgroundScheduler(timezone="Asia/Shanghai") if BackgroundScheduler else None

def monitor_job():
    with SessionLocal() as db:
        event_ids = monitor_all(db)
        for event_id in event_ids:
            from app.models import PricingEvent
            event = db.get(PricingEvent, event_id)
            if event:
                asyncio.run(run_agent(db, event.product_id, event.id))

def start_scheduler():
    if scheduler is None or scheduler.running:
        return
    scheduler.add_job(monitor_job,"interval",minutes=settings.monitor_interval_minutes,id="monitor_job",replace_existing=True,max_instances=1)
    scheduler.start()

def stop_scheduler():
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
