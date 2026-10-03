import asyncio
from app.agent.runner import run_agent
from app.services.demo import seed_demo, advance_demo

def test_demo_agent_closed_loop(db):
    p=seed_demo(db)
    advanced=advance_demo(db,p.id)
    event_id=next((x["event_id"] for x in advanced if x["event_id"]),None)
    rec=asyncio.run(run_agent(db,p.id,event_id))
    assert rec.action in {"ADJUST_PRICE","KEEP_PRICE","LIMITED_PROMOTION","BUNDLE_PROMOTION","NEED_MORE_DATA","PAUSE_AND_OBSERVE"}
    assert rec.suggested_price is None or rec.suggested_price>=45.7
