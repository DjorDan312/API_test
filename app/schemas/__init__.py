"""Pydantic schemas."""
from app.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentTreeResponse,
    DepartmentUpdate,
)
from app.schemas.employee import EmployeeCreate, EmployeeResponse

# Resolve forward references in DepartmentTreeResponse (employees: list[EmployeeResponse])
DepartmentTreeResponse.model_rebuild(_types_namespace={"EmployeeResponse": EmployeeResponse})

__all__ = [
    "DepartmentCreate",
    "DepartmentResponse",
    "DepartmentTreeResponse",
    "DepartmentUpdate",
    "EmployeeCreate",
    "EmployeeResponse",
]
