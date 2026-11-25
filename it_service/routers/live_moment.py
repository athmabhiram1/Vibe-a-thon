# it_service/routers/live_moment.py — additive LIVE-discover moment (L1).
# GET /it/oncall-coverage?team=&at= : joins the H5 on-call person
# (hr_service.db.get_oncall — same canonical seed/demo.db) against open
# breaching tickets (it_service.db.breach_list). Answers "who covers what
# right now": the on-call owner plus which breaching tickets they already
# own vs need a reroute.
#
# Detection contract (research/build/02-api-design.md): literal path,
# explicit it_* operation_id, response_model, docstring. No dynamic loops,
# no include_in_schema=False, no required Header, no File/Form.
# Static path (no /{param} in this router) — no shadowing risk.
#
# Synapse choreography: baseline builds EXCLUDE this route via --endpoints
# allowlist (11 functional ops: H1-H5 + I1-I6); live
# `synapse build --discover` with the EXPANDED allowlist (+it_oncall_coverage
# = 12 functional) picks it up. /demo/* (6 ops) is excluded from BOTH
# allowlists so G2/G6 gates hold. Health (2 ops) excluded for the
# functional-only surface, included for the 13/14 totals.
# Verbatim allowlists live in docs/CLIENTS.md §7 (+ plan.md §4).
import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from hr_service import db as hr_db
from it_service import db as it_db

router = APIRouter(prefix="/it", tags=["it"])


class OnCallPerson(BaseModel):
    team: str
    employee_id: str
    name: str
    email: str
    at: dt.datetime


class CoverageTicket(BaseModel):
    ticket_id: str
    title: str
    assignee_email: str
    team: str
    status: str
    owned_by_oncall: bool = False


class OnCallCoverage(BaseModel):  # L1 live-discover response_model
    team: str
    at: dt.datetime
    oncall: OnCallPerson
    breaching_tickets: list[CoverageTicket]
    owned_by_oncall: list[str]
    needs_reroute: list[str]
    breach_count: int


@router.get(
    "/oncall-coverage",
    operation_id="it_oncall_coverage",
    summary="On-call coverage: who covers which breaches",
    description="Join the H5 on-call person for `team` at `at` (default now)"
    " against open SLA-breaching tickets. `team` scopes the on-call roster;"
    " breaches are cross-team open items the on-call covers. Tickets already"
    " assigned to the on-call land in `owned_by_oncall`, the rest in"
    " `needs_reroute` (reroute via it_reroute_ticket).",
    response_model=OnCallCoverage,
)
async def it_oncall_coverage(
    team: Annotated[str, Query()] = "support-night",
    at: Annotated[dt.datetime | None, Query()] = None,
) -> OnCallCoverage:
    """Join the on-call person for a team against open breaching tickets."""
    moment = at or dt.datetime.now(dt.timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.timezone.utc)
    oncall_row = await hr_db.get_oncall(team=team, moment=moment)
    if oncall_row is None:
        raise HTTPException(status_code=404, detail="no on-call roster for team/date")
    oncall = OnCallPerson.model_validate(
        {
            "team": oncall_row["team"],
            "employee_id": oncall_row["employee_id"],
            "name": oncall_row["name"],
            "email": oncall_row["email"],
            "at": moment.isoformat(),
        }
    )
    breach_rows = await it_db.breach_list()
    tickets: list[CoverageTicket] = []
    for r in breach_rows:
        owned = (r.get("assignee_email") or "").lower() == oncall.email.lower()
        tickets.append(
            CoverageTicket(
                ticket_id=r["ticket_id"],
                title=r["title"],
                assignee_email=r.get("assignee_email") or "",
                team=r.get("team") or "",
                status=r["status"],
                owned_by_oncall=owned,
            )
        )
    owned_ids = [t.ticket_id for t in tickets if t.owned_by_oncall]
    reroute_ids = [t.ticket_id for t in tickets if not t.owned_by_oncall]
    return OnCallCoverage(
        team=team,
        at=moment,
        oncall=oncall,
        breaching_tickets=tickets,
        owned_by_oncall=owned_ids,
        needs_reroute=reroute_ids,
        breach_count=len(tickets),
    )
