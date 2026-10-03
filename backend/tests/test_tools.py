from datetime import date, timedelta
from app.models import Product, SalesDaily
from app.tools.pricing_tools import calculate_margin, get_sales_summary, min_safe_price

def test_min_safe_price(db):
    p=Product(name="x",cost=32,current_price=59,min_margin_rate=.3,stock=10); db.add(p); db.commit()
    assert min_safe_price(p)==45.71 or min_safe_price(p)==45.72
    m=calculate_margin(db,p.id,49)
    assert m["below_floor"] is False
    assert m["margin_rate"]>0.3

def test_sales_trend(db):
    p=Product(name="x",cost=10,current_price=20,min_margin_rate=.2,stock=10); db.add(p); db.flush()
    for i,q in enumerate([10,9,8,7,6,5,4]):
        db.add(SalesDaily(product_id=p.id,sale_date=date.today()-timedelta(days=6-i),quantity=q,revenue=q*20))
    db.commit()
    s=get_sales_summary(db,p.id,7)
    assert s["trend"]=="down"
