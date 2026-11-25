"""Pydantic v2 schemas for the HR directory service.

BaseModel only — no SQLAlchemy/Alembic (per research/verify/04-orm.md).
Email fields are plain `str` so `requirements-hr.txt` needs no extra
`email-validator` dependency.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class Candidate(BaseModel):
    candidate_id: str
    name: str
    email: str
    team: str  # e.g. "platform", "support-night"
    status: str = "interview"  # interview | offer | hired | rejected


class EmployeeCreate(BaseModel):
    name: str
    email: str
    team: str
    start_date: date
    role: str = "engineer"


class Employee(EmployeeCreate):
    employee_id: str
    created_at: datetime


class Shift(BaseModel):
    team: str
    employee_id: str
    date: date
    shift: str = Field(pattern="^(day|night)$")
    on_call: bool = False


class OnCall(BaseModel):  # H5 live-discover response_model
    team: str
    employee_id: str
    name: str
    email: str
    at: datetime
