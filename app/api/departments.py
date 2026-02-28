"""Department and employee endpoints."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentTreeResponse,
    DepartmentUpdate,
)
from app.schemas.employee import EmployeeCreate, EmployeeResponse
from app.services.department import (
    ConflictError,
    DepartmentNotFoundError,
    create_department,
    create_employee,
    delete_department,
    get_department_tree,
    update_department,
)

router = APIRouter(prefix="/departments", tags=["departments"])


@router.post("/", response_model=DepartmentResponse)
def post_department(data: DepartmentCreate, db: Session = Depends(get_db)) -> DepartmentResponse:
    """Create a department."""
    department = create_department(db, data)
    return DepartmentResponse.model_validate(department)


@router.post("/{department_id}/employees/", response_model=EmployeeResponse)
def post_employee(
    department_id: int,
    data: EmployeeCreate,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    """Create an employee in a department."""
    employee = create_employee(db, department_id, data)
    return EmployeeResponse.model_validate(employee)


@router.get("/{department_id}", response_model=DepartmentTreeResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    depth: int = Query(1, ge=1, le=5, description="Depth of nested departments (max 5)"),
    include_employees: bool = Query(True, description="Include employees list"),
    sort_employees: Literal["created_at", "full_name"] = Query(
        "created_at",
        description="Sort employees by created_at or full_name",
    ),
) -> DepartmentTreeResponse:
    """Get department with details, employees and subtree up to depth."""
    return get_department_tree(
        db,
        department_id,
        depth=depth,
        include_employees=include_employees,
        sort_employees_by=sort_employees,
    )


@router.patch("/{department_id}", response_model=DepartmentResponse)
def patch_department(
    department_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    """Update department (name and/or parent)."""
    department = update_department(db, department_id, data)
    return DepartmentResponse.model_validate(department)


@router.delete("/{department_id}", status_code=204)
def delete_department_endpoint(
    department_id: int,
    db: Session = Depends(get_db),
    mode: Literal["cascade", "reassign"] = Query(
        ...,
        description="cascade — delete with all employees and children; reassign — move employees to target",
    ),
    reassign_to_department_id: int | None = Query(
        None,
        description="Required when mode=reassign",
    ),
) -> None:
    """Delete department. cascade: delete all. reassign: move employees to target."""
    if mode == "reassign" and reassign_to_department_id is None:
        raise HTTPException(
            status_code=400,
            detail="reassign_to_department_id is required when mode=reassign",
        )
    delete_department(
        db,
        department_id,
        mode=mode,
        reassign_to_department_id=reassign_to_department_id,
    )
