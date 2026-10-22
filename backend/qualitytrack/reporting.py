"""Plant-calendar overdue reads and serialized taxonomy retirement."""

from datetime import date, datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, tuple_

from qualitytrack.errors import Failure
from qualitytrack.models import CorrectiveAction, DefectType, User
from qualitytrack.security import load_principal, require
from qualitytrack.workflow import _cursor, check_revision
from qualitytrack.workflow_schemas import ActionStatus


# PUBLIC_INTERFACE
class EmptyCommand(BaseModel):
    """Retirement accepts an explicitly empty JSON object."""

    model_config = ConfigDict(extra="forbid")


# PUBLIC_INTERFACE
class OverdueItem(BaseModel):
    """Permitted overdue work, not an ownership-derived entitlement."""

    action_id: UUID = Field(description="Stable action identifier")
    defect_id: UUID = Field(description="Parent defect identifier")
    owner_name: str = Field(description="Current permitted owner display name")
    due_date: date = Field(description="Plant-calendar due date")
    status: ActionStatus = Field(description="Current incomplete status")
    days_overdue: int = Field(gt=0, description="Calendar dates since due date")


# PUBLIC_INTERFACE
class OverduePage(BaseModel):
    """Live work evaluated against one cursor-pinned local date."""

    evaluated_on: date = Field(description="Pinned plant-local evaluation date")
    plant_zone: str = Field(description="Resolved IANA calendar zone")
    items: list[OverdueItem] = Field(description="Permitted overdue work")
    next_cursor: str | None = Field(description="Signed continuation or null")


# PUBLIC_INTERFACE
def plant_today(settings, now=None):
    """Resolve one local date from an aware instant, never the process timezone."""
    try:
        zone = ZoneInfo(settings.plant_zone)
    except (ValueError, ZoneInfoNotFoundError):
        raise Failure(
            503, "calendar_unavailable", "Plant calendar is unavailable"
        ) from None
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("An aware clock is required")
    return instant.astimezone(zone).date()


# PUBLIC_INTERFACE
def overdue_actions(session, caller, settings, cursor=None, limit=50, now=None):
    """Authorize each live page and pin date/zone/order inside a signed cursor."""
    require(caller, "defect.read")
    require(load_principal(session, caller.ref), "defect.read")
    evaluated = plant_today(settings, now)
    context = f"overdue-v1:{settings.plant_zone}:due_date,id"
    key = None
    if cursor:
        raw = _cursor(settings, caller, context, token=cursor)
        try:
            if not isinstance(raw, list) or len(raw) != 3:
                raise ValueError
            evaluated, due, identifier = (
                date.fromisoformat(raw[0]),
                date.fromisoformat(raw[1]),
                UUID(raw[2]),
            )
            if due >= evaluated:
                raise ValueError
            key = (due, identifier)
        except (ValueError, TypeError):
            raise Failure(
                400, "invalid_cursor", "Page continuation is invalid"
            ) from None
    query = (
        select(CorrectiveAction, User.display_name)
        .join(User, User.ref == CorrectiveAction.owner_ref)
        .where(
            CorrectiveAction.status != "Complete",
            CorrectiveAction.due_date < evaluated,
        )
    )
    if key:
        query = query.where(
            tuple_(CorrectiveAction.due_date, CorrectiveAction.id) > tuple_(*key)
        )
    rows = list(
        session.execute(
            query.order_by(CorrectiveAction.due_date, CorrectiveAction.id).limit(
                limit + 1
            )
        )
    )
    more = len(rows) > limit
    rows = rows[:limit]
    continuation = None
    if more:
        last = rows[-1][0]
        continuation = _cursor(
            settings,
            caller,
            context,
            key=[evaluated.isoformat(), last.due_date.isoformat(), str(last.id)],
        )
    return OverduePage(
        evaluated_on=evaluated,
        plant_zone=settings.plant_zone,
        items=[
            OverdueItem(
                action_id=row.id,
                defect_id=row.defect_id,
                owner_name=name,
                due_date=row.due_date,
                status=row.status,
                days_overdue=(evaluated - row.due_date).days,
            )
            for row, name in rows
        ],
        next_cursor=continuation,
    )


# PUBLIC_INTERFACE
def retire_type(session, caller, identifier, header):
    """Authorize before lookup/token disclosure; share capture's type-row lock."""
    require(caller, "type.retire")
    row = session.scalar(
        select(DefectType)
        .where(DefectType.id == identifier)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    require(load_principal(session, caller.ref), "type.retire")
    if not row:
        raise Failure(404, "not_found", "Record was not found")
    check_revision(header, row.revision)
    if row.retired:
        raise Failure(409, "invalid_transition", "Type is already retired")
    row.retired = True
    row.revision += 1
    session.flush()
    return {
        "id": row.id,
        "code": row.code,
        "label": row.label,
        "retired": row.retired,
        "revision": row.revision,
    }
