from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.errors import DuplicateEmail, EmployeeNotFound
from app.models import Employee
from app.schemas import EmployeeIn

# Whitelist of sortable fields — user input never picks a column directly
SORTABLE = {
    "id": Employee.id,
    "name": Employee.name,
    "email": Employee.email,
    "department": Employee.department,
    "salary": Employee.salary,
    "createdAt": Employee.created_at,
}


def create(db: Session, data: EmployeeIn) -> Employee:
    email = data.email.lower()
    if db.scalar(select(Employee.id).where(Employee.email == email)):
        raise DuplicateEmail(email)
    emp = Employee(**data.model_dump(exclude={"email"}), email=email)
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def get(db: Session, emp_id: int) -> Employee:
    emp = db.get(Employee, emp_id)
    if emp is None:
        raise EmployeeNotFound(emp_id)
    return emp


def update(db: Session, emp_id: int, data: EmployeeIn) -> Employee:
    emp = get(db, emp_id)
    email = data.email.lower()
    clash = db.scalar(select(Employee.id).where(Employee.email == email, Employee.id != emp_id))
    if clash:
        raise DuplicateEmail(email)
    for field, value in data.model_dump(exclude={"email"}).items():
        setattr(emp, field, value)
    emp.email = email
    db.commit()
    db.refresh(emp)
    return emp


def delete(db: Session, emp_id: int) -> None:
    db.delete(get(db, emp_id))
    db.commit()


def list_page(db: Session, search: str | None, department: str | None,
              page: int, size: int, sort: str | None):
    q = select(Employee)
    if search:
        like = f"%{search}%"
        q = q.where(or_(Employee.name.ilike(like), Employee.email.ilike(like)))
    if department:
        q = q.where(Employee.department == department)
    field, _, direction = (sort or "name,asc").partition(",")
    column = SORTABLE.get(field, Employee.name)
    q = q.order_by(column.desc() if direction == "desc" else column.asc(), Employee.id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.offset(page * size).limit(size)).all()
    return rows, total


def stats(db: Session) -> dict:
    by_dept = dict(
        db.execute(select(Employee.department, func.count()).group_by(Employee.department)).all()
    )
    avg = db.scalar(select(func.avg(Employee.salary)))
    return {
        "total": sum(by_dept.values()),
        "byDepartment": by_dept,
        "averageSalary": round(avg, 2) if avg is not None else None,
    }