"""Service-layer tests: business rules, called directly with a DB session."""
from decimal import Decimal

import pytest

from app import service
from app.errors import DuplicateEmail, EmployeeNotFound
from app.schemas import EmployeeIn


def make(**overrides) -> EmployeeIn:
    body = {"name": "Asha K", "email": "asha@corp.com", "department": "IT", "salary": "50000"}
    body.update(overrides)
    return EmployeeIn(**body)


# ---------- create ----------

def test_create_saves_employee_and_lowercases_email(session):
    emp = service.create(session, make(email="Asha@Corp.com"))
    assert emp.id is not None
    assert emp.email == "asha@corp.com"
    assert emp.created_at is not None


def test_create_rejects_duplicate_email(session):
    service.create(session, make())
    with pytest.raises(DuplicateEmail):
        service.create(session, make(name="Someone Else"))


def test_create_duplicate_check_ignores_case(session):
    service.create(session, make())
    with pytest.raises(DuplicateEmail):
        service.create(session, make(email="ASHA@CORP.COM"))


# ---------- get ----------

def test_get_returns_employee(session):
    created = service.create(session, make())
    assert service.get(session, created.id).name == "Asha K"


def test_get_missing_raises_not_found(session):
    with pytest.raises(EmployeeNotFound):
        service.get(session, 999)


# ---------- update ----------

def test_update_changes_fields(session):
    emp = service.create(session, make())
    updated = service.update(
        session, emp.id, make(name="Asha Kumar", department="HR", salary="65000.50")
    )
    assert updated.name == "Asha Kumar"
    assert updated.department == "HR"
    assert updated.salary == Decimal("65000.50")


def test_update_can_keep_own_email(session):
    emp = service.create(session, make())
    assert service.update(session, emp.id, make(name="New Name")).email == "asha@corp.com"


def test_update_to_another_employees_email_raises(session):
    service.create(session, make())
    other = service.create(session, make(name="Ravi", email="ravi@corp.com"))
    with pytest.raises(DuplicateEmail):
        service.update(session, other.id, make(name="Ravi", email="asha@corp.com"))


def test_update_missing_raises_not_found(session):
    with pytest.raises(EmployeeNotFound):
        service.update(session, 999, make())


# ---------- delete ----------

def test_delete_removes_employee(session):
    emp = service.create(session, make())
    service.delete(session, emp.id)
    with pytest.raises(EmployeeNotFound):
        service.get(session, emp.id)


def test_delete_missing_raises_not_found(session):
    with pytest.raises(EmployeeNotFound):
        service.delete(session, 999)


# ---------- list: search, filter, sort, paging ----------

@pytest.fixture()
def three_employees(session):
    service.create(session, make(name="Asha K", email="asha@corp.com", department="IT", salary="50000"))
    service.create(session, make(name="Ravi M", email="ravi@corp.com", department="HR", salary="70000"))
    service.create(session, make(name="Meena S", email="meena@sales.com", department="Sales", salary="60000"))


def test_list_without_filters_returns_all(session, three_employees):
    rows, total = service.list_page(session, None, None, 0, 10, None)
    assert total == 3
    assert [r.name for r in rows] == ["Asha K", "Meena S", "Ravi M"]  # default sort: name asc


def test_search_matches_name_case_insensitively(session, three_employees):
    rows, total = service.list_page(session, "RAVI", None, 0, 10, "name,asc")
    assert total == 1 and rows[0].name == "Ravi M"


def test_search_matches_email(session, three_employees):
    rows, total = service.list_page(session, "sales.com", None, 0, 10, "name,asc")
    assert total == 1 and rows[0].name == "Meena S"


def test_filter_by_department(session, three_employees):
    rows, total = service.list_page(session, None, "HR", 0, 10, "name,asc")
    assert total == 1 and rows[0].department == "HR"


def test_sort_by_salary_desc(session, three_employees):
    rows, _ = service.list_page(session, None, None, 0, 10, "salary,desc")
    assert [r.name for r in rows] == ["Ravi M", "Meena S", "Asha K"]


def test_unknown_sort_field_falls_back_to_name(session, three_employees):
    rows, _ = service.list_page(session, None, None, 0, 10, "password,asc")
    assert [r.name for r in rows] == ["Asha K", "Meena S", "Ravi M"]


def test_paging(session, three_employees):
    rows, total = service.list_page(session, None, None, 1, 2, "name,asc")
    assert total == 3
    assert [r.name for r in rows] == ["Ravi M"]  # page 1 of size 2 -> third item


# ---------- stats ----------

def test_stats_on_empty_database(session):
    assert service.stats(session) == {"total": 0, "byDepartment": {}, "averageSalary": None}


def test_stats_counts_and_average(session, three_employees):
    result = service.stats(session)
    assert result["total"] == 3
    assert result["byDepartment"] == {"IT": 1, "HR": 1, "Sales": 1}
    assert Decimal(str(result["averageSalary"])) == Decimal("60000")