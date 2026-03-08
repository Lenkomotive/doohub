import os

# Override database URL before any app imports
os.environ["DOOHUB_DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON, StaticPool
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.auth import get_current_user
# Import all models so they register with Base.metadata
from app.models.user import User  # noqa: F401
from app.models.pipeline import Pipeline  # noqa: F401
from app.models.pipeline_template import PipelineTemplate  # noqa: F401
from app.models.pipeline_schedule import PipelineSchedule  # noqa: F401
from app.models.session import Session, SessionMessage  # noqa: F401


# Map JSONB columns to JSON for SQLite compatibility
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db):
    user = User(
        id=1,
        username="testuser",
        password_hash="fakehash",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def client(db, test_user):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return test_user

    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Mock lifespan background tasks to avoid real DB/network calls
    with patch("app.main._seed_default_template"), \
         patch("app.main._session_event_consumer", new_callable=AsyncMock), \
         patch("app.main.schedule_poller", new_callable=AsyncMock):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    app.dependency_overrides.clear()
