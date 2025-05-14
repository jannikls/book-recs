import pytest
from app.models import Cluster, Book, User, UserBook, ClusterBook, Base
from app.main import compute_cluster_niche_scores, app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import tempfile
import math

@pytest.fixture(scope="function")
def db_session():
    # Setup in-memory SQLite DB
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


def test_compute_cluster_niche_scores(db_session):
    # Create cluster, users, books, userbooks
    cluster = Cluster(id=1, name="ML Club")
    db_session.add(cluster)
    users = [User(id=1), User(id=2), User(id=3)]
    db_session.add_all(users)
    books = [Book(id=1, title="A", author="a", vector=[1,0], cover_url=""),
             Book(id=2, title="B", author="b", vector=[0,1], cover_url="")]
    db_session.add_all(books)
    db_session.commit()
    # Simulate cluster.users relationship
    cluster.users = users
    # User 1 and 2 read book 1, user 3 read book 2
    db_session.add_all([
        UserBook(user_id=1, book_id=1, rating=5),
        UserBook(user_id=2, book_id=1, rating=4),
        UserBook(user_id=3, book_id=2, rating=5)
    ])
    db_session.commit()
    compute_cluster_niche_scores(db_session)
    # Check ClusterBook entries
    cb1 = db_session.query(ClusterBook).filter_by(cluster_id=1, book_id=1).first()
    cb2 = db_session.query(ClusterBook).filter_by(cluster_id=1, book_id=2).first()
    assert cb1.read_count == 2
    assert math.isclose(cb1.cluster_niche_score, 1 / math.log(1 + 2))
    assert cb2.read_count == 1
    assert math.isclose(cb2.cluster_niche_score, 1 / math.log(1 + 1))

def test_niche_spots_api(monkeypatch):
    client = TestClient(app)
    # Patch db.get_db to use in-memory DB
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    # Setup test data
    cluster = Cluster(id=1, name="ML Club")
    session.add(cluster)
    book = Book(id=1, title="A", author="a", vector=[1,0], cover_url="cover.png")
    session.add(book)
    cb = ClusterBook(id=1, cluster_id=1, book_id=1, read_count=5, cluster_niche_score=0.7)
    session.add(cb)
    session.commit()
    def fake_get_db():
        yield session
    monkeypatch.setattr("app.db.get_db", fake_get_db)
    resp = client.get("/api/clusters/1/niche-spots?k=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "A"
    assert data[0]["read_count"] == 5
    assert "cluster_niche_score" in data[0]
