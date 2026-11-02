from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Department = Literal["IT", "HR", "Finance", "Sales"]


class EmployeeIn(BaseModel):
    name: Name
    email: EmailStr
    department: Department
    salary: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    department: str
    salary: Decimal
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")


class Page(BaseModel):
    content: list[EmployeeOut]
    page: int
    size: int
    totalElements: int
    totalPages: int


class Stats(BaseModel):
    total: int
    byDepartment: dict[str, int]
    averageSalary: Decimal | None