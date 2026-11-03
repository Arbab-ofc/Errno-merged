import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
import models
from firebase_auth import authenticated_user
from main import app


@pytest.fixture
def client_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    worker = models.User(firebase_uid="worker-profile-test", role="worker", is_active=True)
    shopkeeper = models.User(firebase_uid="shop-profile-test", role="shopkeeper", is_active=True)
    session.add_all([worker, shopkeeper]); session.commit()
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[authenticated_user] = lambda: worker
    yield TestClient(app), session, worker, shopkeeper
    app.dependency_overrides.clear()
    session.close(); Base.metadata.drop_all(engine); engine.dispose()


def test_worker_skills_round_trip_and_deduplicate(client_context):
    client, session, worker, _ = client_context
    assert client.get("/api/v1/workers/me/profile").json() == {"preferredSkills": []}
    response = client.patch("/api/v1/workers/me/profile", json={"preferredSkills": [" Delivery Partner ", "Delivery Partner", "Cashier"]})
    assert response.status_code == 200
    assert response.json()["preferredSkills"] == ["Delivery Partner", "Cashier"]
    assert session.query(models.WorkerProfilePreferences).filter_by(user_id=worker.id).one().preferred_skills == ["Delivery Partner", "Cashier"]


def test_worker_skills_reject_blank_and_extra_fields(client_context):
    client, *_ = client_context
    assert client.patch("/api/v1/workers/me/profile", json={"preferredSkills": [" "]}).status_code == 422
    assert client.patch("/api/v1/workers/me/profile", json={"preferredSkills": [], "userId": "other"}).status_code == 422


def test_non_worker_cannot_read_worker_profile(client_context):
    client, _, _, shopkeeper = client_context
    app.dependency_overrides[authenticated_user] = lambda: shopkeeper
    assert client.get("/api/v1/workers/me/profile").status_code == 403


def test_worker_profile_requires_authentication(client_context):
    client, *_ = client_context
    app.dependency_overrides.pop(authenticated_user)
    response = client.get("/api/v1/workers/me/profile")
    assert response.status_code == 401
