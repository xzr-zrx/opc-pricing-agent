import json
from app.models import Competitor, Product
from app.services.monitor import collect_competitor

def test_mock_price_event(db):
    p=Product(name="x",cost=10,current_price=20,min_margin_rate=.2,stock=10); db.add(p); db.flush()
    c=Competitor(product_id=p.id,name="c",source_type="mock",mock_prices_json=json.dumps([20,15]),mock_promos_json="[]")
    db.add(c); db.commit(); db.refresh(c)
    _,e1=collect_competitor(db,c.id,False); assert e1 is None
    _,e2=collect_competitor(db,c.id,True); assert e2 is not None
    assert e2.event_type=="PRICE_CHANGE"
