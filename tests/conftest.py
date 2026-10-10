import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def anon_client(app):
    """Client without credentials."""
    return app.test_client()


@pytest.fixture
def client(app):
    """Client already logged in as the default admin user."""
    c = app.test_client()
    token = c.post("/login", json={"username": "admin", "password": "admin"}).get_json()["token"]
    c.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return c
