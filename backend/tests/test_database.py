from sqlalchemy import create_engine, inspect

from app.db.base import Base
from app.models import asset, image, journal, user  # noqa: F401


def test_metadata_creates_expected_tables():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    Base.metadata.create_all(bind=engine)

    tables = set(inspect(engine).get_table_names())
    assert {
        "assets",
        "images",
        "journal_images",
        "journals",
        "users",
    }.issubset(tables)
