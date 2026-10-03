from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.db import Base, engine
from app.jobs.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app:FastAPI):
    Base.metadata.create_all(engine)
    start_scheduler()
    yield
    stop_scheduler()

app=FastAPI(title="OPC Pricing Agent",version="1.0.0",lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(router)
