from datetime import datetime

from pydantic import BaseModel, EmailStr


class Laptop(BaseModel):
    serial: str
    model: str
    status: str = "free"  # free | assigned


class AssignLaptop(BaseModel):
    serial: str
    employee_id: str


class Assignment(BaseModel):
    serial: str
    employee_id: str
    assigned_at: datetime


class TicketCreate(BaseModel):
    title: str
    assignee_email: EmailStr
    team: str
    sla_hours: int = 24


class Reroute(BaseModel):
    to_email: EmailStr
    reason: str = "sla-breach-reroute-to-oncall"


class Ticket(BaseModel):
    ticket_id: str  # e.g. T-5001
    title: str
    assignee_email: EmailStr
    team: str
    status: str  # open | resolved
    created_at: datetime
    deadline_at: datetime
    breached: bool = False
