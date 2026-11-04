"""API tests: status codes, the JSON error shape, and validation through HTTP."""
import pytest

BASE = "/api/employees"


def assert_error_shape(body, status):
    assert body["status"] == status
    for key in ("timestamp", "error", "message", "fieldErrors"):
        assert key in body


# ---------- create ----------

def test_create_returns_201_with_location(client, employee_payload):
    r = client.post(BASE, json=employee_payload())
    assert r.status_code == 200
    body = r.json()
    assert r.headers["Location"] == f"{BASE}/{body['id']}"
    assert body["email"] == "asha@corp.com"
    assert "createdAt" in body and "updatedAt" in body


def test_create_duplicate_email_returns_409(client, employee_payload):
    client.post(BASE, json=employee_payload())
    r = client.post(BASE, json=employee_payload(email="ASHA@corp.com"))
    assert r.status_code == 409
    assert_error_shape(r.json(), 409)
    assert r.json()["message"] == "Email already exists"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", "A"),
        ("name", "x" * 101),
        ("email", "not-an-email"),
        ("salary", 0),
        ("salary", -5),
        ("department", "Marketing"),
    ],
)
def test_create_invalid_field_returns_400(client, employee_payload, field, value):
    r = client.post(BASE, json=employee_payload(**{field: value}))
    assert r.status_code == 400  # contract says 400, not FastAPI's default 422
    body = r.json()
    assert_error_shape(body, 400)
    assert [e["field"] for e in body["fieldErrors"]] == [field]


def test_create_missing_fields_lists_every_field(client):
    r = client.post(BASE, json={})
    assert r.status_code == 400
    fields = {e["field"] for e in r.json()["fieldErrors"]}
    assert fields == {"name", "email", "department", "salary"}


def test_malformed_json_returns_400(client):
    r = client.post(BASE, content="{not json", headers={"content-type": "application/json"})
    assert r.status_code == 400


# ---------- read ----------

def test_get_by_id(client, employee_payload):
    emp_id = client.post(BASE, json=employee_payload()).json()["id"]
    r = client.get(f"{BASE}/{emp_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Asha K"


def test_get_unknown_id_returns_404(client):
    r = client.get(f"{BASE}/999")
    assert r.status_code == 404
    assert_error_shape(r.json(), 404)


def test_list_search_filter_and_page_shape(client, employee_payload):
    client.post(BASE, json=employee_payload())
    client.post(BASE, json=employee_payload(name="Ravi M", email="ravi@corp.com", department="HR"))

    r = client.get(BASE, params={"search": "ravi", "page": 0, "size": 10, "sort": "name,asc"})
    assert r.status_code == 200
    body = r.json()
    assert body["totalElements"] == 1
    assert body["totalPages"] == 1
    assert body["content"][0]["name"] == "Ravi M"

    by_dept = client.get(BASE, params={"department": "IT"}).json()
    assert [e["name"] for e in by_dept["content"]] == ["Asha K"]


def test_list_rejects_bad_paging(client):
    assert client.get(BASE, params={"size": 0}).status_code == 400
    assert client.get(BASE, params={"page": -1}).status_code == 400


def test_stats(client, employee_payload):
    client.post(BASE, json=employee_payload(salary=50000))
    client.post(BASE, json=employee_payload(
        name="Ravi M", email="ravi@corp.com", department="HR", salary=70000))
    r = client.get(f"{BASE}/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["byDepartment"] == {"IT": 1, "HR": 1}
    assert float(body["averageSalary"]) == 60000


# ---------- update ----------

def test_update_returns_200(client, employee_payload):
    emp_id = client.post(BASE, json=employee_payload()).json()["id"]
    r = client.put(f"{BASE}/{emp_id}", json=employee_payload(name="Asha Kumar"))
    assert r.status_code == 200
    assert r.json()["name"] == "Asha Kumar"


def test_update_invalid_returns_400(client, employee_payload):
    emp_id = client.post(BASE, json=employee_payload()).json()["id"]
    assert client.put(f"{BASE}/{emp_id}", json=employee_payload(salary=0)).status_code == 400


def test_update_unknown_returns_404(client, employee_payload):
    assert client.put(f"{BASE}/999", json=employee_payload()).status_code == 404


def test_update_to_duplicate_email_returns_409(client, employee_payload):
    client.post(BASE, json=employee_payload())
    other = client.post(BASE, json=employee_payload(name="Ravi M", email="ravi@corp.com")).json()["id"]
    r = client.put(f"{BASE}/{other}", json=employee_payload(name="Ravi M", email="asha@corp.com"))
    assert r.status_code == 409


# ---------- delete ----------

def test_delete_returns_204_then_404(client, employee_payload):
    emp_id = client.post(BASE, json=employee_payload()).json()["id"]
    assert client.delete(f"{BASE}/{emp_id}").status_code == 204
    assert client.delete(f"{BASE}/{emp_id}").status_code == 404


# ---------- health, errors, static ----------

def test_health_up(client):
    r = client.get("/actuator/health")
    assert r.status_code == 200
    assert r.json() == {"status": "UP"}


def test_health_down_when_database_unreachable(client, engine, monkeypatch):
    def broken_connect(*args, **kwargs):
        raise RuntimeError("database is down")

    monkeypatch.setattr(engine, "connect", broken_connect)
    r = client.get("/actuator/health")
    assert r.status_code == 503
    assert r.json() == {"status": "DOWN"}


def test_wrong_method_uses_error_shape(client):
    r = client.patch(BASE)
    assert r.status_code == 405
    assert_error_shape(r.json(), 405)


def test_unexpected_error_returns_generic_500(engine, monkeypatch):
    from fastapi.testclient import TestClient

    from app import service
    from app.main import app

    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(service, "stats", boom)
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get(f"{BASE}/stats")
    assert r.status_code == 500
    assert r.json()["message"] == "Unexpected error"
    assert "secret" not in r.text  # never leak internals


def test_static_index_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]