from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app import service
from app.db import get_db
from app.schemas import EmployeeIn, EmployeeOut, Page, Stats

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.post("", status_code=201, response_model=EmployeeOut)
def create_employee(body: EmployeeIn, response: Response, db: Session = Depends(get_db)):
    emp = service.create(db, body)
    response.headers["Location"] = f"/api/employees/{emp.id}"
    return emp


@router.get("", response_model=Page)
def list_employees(
    search: str | None = None,
    department: str | None = None,
    page: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=100),
    sort: str = "name,asc",
    db: Session = Depends(get_db),
):
    rows, total = service.list_page(db, search, department, page, size, sort)
    return Page(
        content=[EmployeeOut.model_validate(r) for r in rows],
        page=page,
        size=size,
        totalElements=total,
        totalPages=(total + size - 1) // size,
    )


@router.get("/stats", response_model=Stats)  # must stay ABOVE /{emp_id}
def get_stats(db: Session = Depends(get_db)):
    return service.stats(db)


@router.get("/{emp_id}", response_model=EmployeeOut)
def get_employee(emp_id: int, db: Session = Depends(get_db)):
    return service.get(db, emp_id)


@router.put("/{emp_id}", response_model=EmployeeOut)
def update_employee(emp_id: int, body: EmployeeIn, db: Session = Depends(get_db)):
    return service.update(db, emp_id, body)


@router.delete("/{emp_id}", status_code=204)
def delete_employee(emp_id: int, db: Session = Depends(get_db)):
    service.delete(db, emp_id)