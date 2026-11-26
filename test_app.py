from app import app


def test_home():
    client = app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    assert res.get_json()["message"] == "Hello from Jenkins demo app!"


def test_health():
    client = app.test_client()
    res = client.get("/health")
    assert res.get_json() == {"status": "ok"}


def test_add():
    client = app.test_client()
    res = client.get("/add/2/3")
    assert res.get_json()["result"] == 5