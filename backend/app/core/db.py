from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings

settings = get_settings()
if settings.database_url.startswith("sqlite:///"):
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def upgrade_sqlite_schema() -> None:
    """给已经存在的 MVP SQLite 数据库做最小向后兼容升级。

    项目当前没有 Alembic。这里只为本次新增的可空字段执行 ADD COLUMN，
    新数据库仍由 SQLAlchemy create_all 正常创建。
    """
    if not settings.database_url.startswith("sqlite"):
        return

    additions: dict[str, dict[str, str]] = {
        "products": {
            "search_keyword": "VARCHAR(160)",
        },
        "competitors": {
            "shop_name": "VARCHAR(160)",
            "image_url": "TEXT",
        },
        "competitor_price_snapshots": {
            "sales": "INTEGER",
            "sales_text": "VARCHAR(80)",
        },
    }

    with engine.begin() as conn:
        tables = set(inspect(conn).get_table_names())
        for table, columns in additions.items():
            if table not in tables:
                continue
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for column, sql_type in columns.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
