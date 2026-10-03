from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.db import Base, SessionLocal, engine, upgrade_sqlite_schema
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.services.demo import seed_demo_catalog


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    upgrade_sqlite_schema()
    with SessionLocal() as db:
        seed_demo_catalog(db)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="OPC Pricing Agent", version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
