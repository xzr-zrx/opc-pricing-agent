import os
os.environ["DATABASE_URL"]="sqlite:///:memory:"
os.environ["DEMO_FALLBACK_ENABLED"]="true"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.db import Base

@pytest.fixture()
def db():
    engine=create_engine("sqlite:///:memory:",connect_args={"check_same_thread":False})
    Base.metadata.create_all(engine)
    Session=sessionmaker(bind=engine,expire_on_commit=False)
    s=Session()
    try: yield s
    finally: s.close()
