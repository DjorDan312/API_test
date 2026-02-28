"""Department and employee business logic."""
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentTreeResponse,
    DepartmentUpdate,
)
from app.schemas.employee import EmployeeCreate, EmployeeResponse

logger = get_logger(__name__)


class DepartmentNotFoundError(Exception):
    """Department not found."""

    pass


class ConflictError(Exception):
    """Business rule conflict (e.g. cycle, duplicate name)."""

    pass


def _get_department(db: Session, department_id: int) -> Department | None:
    return db.get(Department, department_id)


def _get_descendant_ids(db: Session, department_id: int) -> set[int]:
    """Return set of all descendant department IDs (children, grandchildren, ...)."""
    result: set[int] = set()
    stack = [department_id]
    while stack:
        current = stack.pop()
        rows = db.execute(
            select(Department.id).where(Department.parent_id == current)
        ).scalars().all()
        for child_id in rows:
            result.add(child_id)
            stack.append(child_id)
    return result


def _check_name_unique_under_parent(
    db: Session,
    name: str,
    parent_id: int | None,
    exclude_department_id: int | None = None,
) -> None:
    q = select(Department).where(
        Department.name == name,
        Department.parent_id == parent_id,
    )
    if exclude_department_id is not None:
        q = q.where(Department.id != exclude_department_id)
    existing = db.execute(q).unique().scalars().first()
    if existing is not None:
        raise ConflictError(
            f"Department with name {name!r} already exists under this parent"
        )


def create_department(db: Session, data: DepartmentCreate) -> Department:
    """Create a department. Validates parent exists and name is unique under parent."""
    if data.parent_id is not None:
        parent = _get_department(db, data.parent_id)
        if parent is None:
            raise DepartmentNotFoundError("Parent department not found")
    _check_name_unique_under_parent(db, data.name, data.parent_id)
    department = Department(name=data.name, parent_id=data.parent_id)
    db.add(department)
    db.commit()
    db.refresh(department)
    logger.info("Created department id=%s name=%s", department.id, department.name)
    return department


def create_employee(
    db: Session,
    department_id: int,
    data: EmployeeCreate,
) -> Employee:
    """Create an employee in a department. Fails if department does not exist."""
    department = _get_department(db, department_id)
    if department is None:
        raise DepartmentNotFoundError("Department not found")
    employee = Employee(
        department_id=department_id,
        full_name=data.full_name,
        position=data.position,
        hired_at=data.hired_at,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    logger.info(
        "Created employee id=%s department_id=%s",
        employee.id,
        employee.department_id,
    )
    return employee


def get_department_tree(
    db: Session,
    department_id: int,
    depth: int = 1,
    include_employees: bool = True,
    sort_employees_by: str = "created_at",
) -> DepartmentTreeResponse:
    """Get department with employees and children up to depth. 404 if not found."""
    department = _get_department(db, department_id)
    if department is None:
        raise DepartmentNotFoundError("Department not found")

    def _build_tree(dept: Department, current_depth: int) -> DepartmentTreeResponse:
        employees_list: list[EmployeeResponse] = []
        if include_employees:
            emps = list(dept.employees)
            if sort_employees_by == "full_name":
                emps.sort(key=lambda e: (e.full_name, e.id))
            else:
                emps.sort(key=lambda e: (e.created_at, e.id))
            employees_list = [EmployeeResponse.model_validate(e) for e in emps]
        children_list: list[DepartmentTreeResponse] = []
        if current_depth > 0 and dept.children:
            for child in sorted(dept.children, key=lambda c: (c.name, c.id)):
                children_list.append(_build_tree(child, current_depth - 1))
        return DepartmentTreeResponse(
            department=DepartmentResponse.model_validate(dept),
            employees=employees_list,
            children=children_list,
        )

    return _build_tree(department, depth)


def update_department(
    db: Session,
    department_id: int,
    data: DepartmentUpdate,
) -> Department:
    """Update department name and/or parent. Validates no self-parent and no cycle."""
    department = _get_department(db, department_id)
    if department is None:
        raise DepartmentNotFoundError("Department not found")

    new_parent_id = data.parent_id if data.parent_id is not None else department.parent_id
    new_name = data.name if data.name is not None else department.name

    if new_parent_id == department_id:
        raise ConflictError("Department cannot be its own parent")
    if new_parent_id is not None:
        descendants = _get_descendant_ids(db, department_id)
        if new_parent_id in descendants:
            raise ConflictError(
                "Cannot move department into its own subtree (would create a cycle)"
            )
        parent = _get_department(db, new_parent_id)
        if parent is None:
            raise DepartmentNotFoundError("Target parent department not found")

    _check_name_unique_under_parent(
        db, new_name, new_parent_id, exclude_department_id=department_id
    )

    department.name = new_name
    department.parent_id = new_parent_id
    db.commit()
    db.refresh(department)
    logger.info("Updated department id=%s", department.id)
    return department


def delete_department(
    db: Session,
    department_id: int,
    mode: str,
    reassign_to_department_id: int | None = None,
) -> None:
    """
    Delete department.
    - cascade: delete department, all employees and all descendants.
    - reassign: move employees to reassign_to_department_id, then delete department
      and handle children (spec says "удалить подразделение, а сотрудников перевести").
      For reassign we reassign only direct employees; child departments remain but
      their parent_id would need to be updated to reassign_to_department_id or we
      delete only this node and move its employees. Spec: "удалить подразделение, а
      сотрудников перевести в reassign_to_department_id" — so we delete this department
      and reassign its employees. What about child departments? Spec doesn't say to
      move them. So in reassign mode: delete this department only (and we need to
      reassign its direct employees to reassign_to_department_id, and set children's
      parent_id to reassign_to_department_id so the tree doesn't break). So:
      - Reassign this department's employees to target.
      - Set all direct children's parent_id to reassign_to_department_id.
      - Delete this department (no cascade delete of children).
    """
    department = _get_department(db, department_id)
    if department is None:
        raise DepartmentNotFoundError("Department not found")

    if mode == "cascade":
        db.delete(department)
        db.commit()
        logger.info("Deleted department id=%s (cascade)", department_id)
        return

    if mode == "reassign":
        if reassign_to_department_id is None:
            raise ValueError("reassign_to_department_id required when mode=reassign")
        target = _get_department(db, reassign_to_department_id)
        if target is None:
            raise DepartmentNotFoundError("Target department for reassign not found")
        if reassign_to_department_id == department_id:
            raise ConflictError("Cannot reassign to the same department")

        # Bulk update so cascade delete won't touch reassigned employees/children
        db.execute(
            update(Employee)
            .where(Employee.department_id == department_id)
            .values(department_id=reassign_to_department_id)
        )
        db.execute(
            update(Department)
            .where(Department.parent_id == department_id)
            .values(parent_id=reassign_to_department_id)
        )
        db.delete(department)
        db.commit()
        logger.info(
            "Deleted department id=%s (reassign to %s)",
            department_id,
            reassign_to_department_id,
        )
        return

    raise ValueError(f"Invalid mode: {mode}")
