"""Department schemas."""
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from app.schemas.employee import EmployeeResponse


def _trim_str(v: str) -> str:
    return v.strip() if isinstance(v, str) else v


class DepartmentBase(BaseModel):
    """Base department schema."""

    name: str = Field(..., min_length=1, max_length=200)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("name must not be empty")
        return v


class DepartmentCreate(DepartmentBase):
    """Schema for creating a department."""

    parent_id: int | None = None


class DepartmentUpdate(BaseModel):
    """Schema for updating a department (PATCH)."""

    name: str | None = Field(None, min_length=1, max_length=200)
    parent_id: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip() or None
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty_if_present(cls, v: str | None) -> str | None:
        if v is not None and not v:
            raise ValueError("name must not be empty")
        return v


class DepartmentResponse(BaseModel):
    """Department as returned by API (flat)."""

    id: int
    name: str
    parent_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentTreeResponse(BaseModel):
    """Department with employees and children (recursive)."""

    department: DepartmentResponse
    employees: list["EmployeeResponse"] = Field(default_factory=list)
    children: list["DepartmentTreeResponse"] = Field(default_factory=list)

    model_config = {"from_attributes": True}




