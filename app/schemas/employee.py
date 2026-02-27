"""Employee schemas."""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


def _trim_str(v: str) -> str:
    return v.strip() if isinstance(v, str) else v


class EmployeeBase(BaseModel):
    """Base employee schema."""

    full_name: str = Field(..., min_length=1, max_length=200)
    position: str = Field(..., min_length=1, max_length=200)
    hired_at: date | None = None

    @field_validator("full_name", "position", mode="before")
    @classmethod
    def trim_str(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("full_name", "position")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("field must not be empty")
        return v


class EmployeeCreate(EmployeeBase):
    """Schema for creating an employee."""

    pass


class EmployeeResponse(BaseModel):
    """Employee as returned by API."""

    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: date | None
    created_at: datetime

    model_config = {"from_attributes": True}
