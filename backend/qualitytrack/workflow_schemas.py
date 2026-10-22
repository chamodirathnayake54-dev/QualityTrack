"""Batch B workflow contracts; all actors and revisions are server supplied."""

from datetime import date, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from qualitytrack.schemas import DefectStatus

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]


# PUBLIC_INTERFACE
class ActionStatus(str, Enum):
    """Explicit action entry and transition states."""

    open = "Open"
    progressing = "In Progress"
    complete = "Complete"


# PUBLIC_INTERFACE
class CauseCreate(BaseModel):
    """One recorded preliminary cause, not an automatic RCA conclusion."""

    model_config = ConfigDict(extra="forbid")
    text: Text = Field(description="Trimmed nonblank cause, at most 2000 characters")


# PUBLIC_INTERFACE
class DefectTransition(BaseModel):
    """Requested target; current state and cause/closure gates are server checked."""

    model_config = ConfigDict(extra="forbid")
    target_status: DefectStatus = Field(description="Requested defect state")


# PUBLIC_INTERFACE
class ActionCreate(BaseModel):
    """Explicit action entry; completion conditions are checked after parent locking."""

    model_config = ConfigDict(extra="forbid")
    description: Text = Field(description="Trimmed nonblank work description")
    owner_ref: str = Field(
        min_length=1, description="Eligible stable demo owner reference"
    )
    due_date: date = Field(description="Calendar due date; past dates are permitted")
    status: ActionStatus = Field(description="Explicit initial state")
    completion_notes: Text | None = Field(
        default=None, description="Required only for initial Complete"
    )


# PUBLIC_INTERFACE
class ActionTransition(BaseModel):
    """Action target and conditional evidence, never caller attribution."""

    model_config = ConfigDict(extra="forbid")
    target_status: ActionStatus = Field(description="Requested action state")
    completion_notes: Text | None = Field(
        default=None, description="Required only on entry to Complete"
    )
    reopen_reason: Text | None = Field(
        default=None, description="Required only for Complete to In Progress"
    )


# PUBLIC_INTERFACE
class CauseView(BaseModel):
    """Recorded cause and current parent revision."""

    id: UUID = Field(description="Cause identifier")
    defect_id: UUID = Field(description="Parent defect")
    text: str = Field(description="Saved cause")
    recorded_by_ref: str = Field(description="Verified recording actor")
    recorded_at: datetime = Field(description="Server recording instant")
    revision: int = Field(description="Current parent revision")


# PUBLIC_INTERFACE
class ActionView(BaseModel):
    """Current action, without overwriting its retained event evidence."""

    id: UUID = Field(description="Action identifier")
    defect_id: UUID = Field(description="Parent defect")
    description: str = Field(description="Assigned work")
    owner_ref: str = Field(description="Stable owner reference")
    due_date: date = Field(description="Calendar due date")
    status: ActionStatus = Field(description="Current action state")
    revision: int = Field(description="Current parent revision")


# PUBLIC_INTERFACE
class DefectEventView(BaseModel):
    """Successful immutable defect transition evidence."""

    id: UUID = Field(description="Event identifier")
    old_status: DefectStatus = Field(description="Previous state")
    new_status: DefectStatus = Field(description="Committed state")
    actor_ref: str = Field(description="Verified actor")
    occurred_at: datetime = Field(description="Server event instant")
    aggregate_revision: int = Field(description="Causal parent revision")


# PUBLIC_INTERFACE
class ActionEventView(BaseModel):
    """Every action creation/completion/reopening cycle in causal order."""

    id: UUID = Field(description="Event identifier")
    action_id: UUID = Field(description="Action identifier")
    defect_id: UUID = Field(description="Parent resolved through action")
    old_status: ActionStatus | None = Field(description="Null only at creation")
    new_status: ActionStatus = Field(description="Committed state")
    actor_ref: str = Field(description="Verified actor")
    occurred_at: datetime = Field(description="Server event instant")
    aggregate_revision: int = Field(description="Causal parent revision")
    completion_notes: str | None = Field(description="Notes only on entering Complete")
    reopen_reason: str | None = Field(description="Reason only on reopening")


# PUBLIC_INTERFACE
class CausePage(BaseModel):
    """Live ordered cause page."""

    items: list[CauseView] = Field(
        description="Causes ordered by recording instant and ID"
    )
    next_cursor: str | None = Field(
        description="Signed caller/parent-bound continuation"
    )


# PUBLIC_INTERFACE
class ActionPage(BaseModel):
    """Live ordered action page."""

    items: list[ActionView] = Field(description="Actions ordered by ID")
    next_cursor: str | None = Field(
        description="Signed caller/parent-bound continuation"
    )


# PUBLIC_INTERFACE
class DefectEventPage(BaseModel):
    """Retained defect history page."""

    items: list[DefectEventView] = Field(
        description="Events ordered by aggregate revision"
    )
    next_cursor: str | None = Field(
        description="Signed caller/parent-bound continuation"
    )


# PUBLIC_INTERFACE
class ActionEventPage(BaseModel):
    """Retained action history page."""

    items: list[ActionEventView] = Field(
        description="Events ordered by aggregate revision"
    )
    next_cursor: str | None = Field(
        description="Signed caller/action-bound continuation"
    )


# PUBLIC_INTERFACE
class OwnerView(BaseModel):
    """Eligible owner's permitted display, never credentials or grants."""

    ref: str = Field(description="Stable eligible owner reference")
    display_name: str = Field(description="Current permitted display name")


# PUBLIC_INTERFACE
class OwnerPage(BaseModel):
    """Complete bounded demo eligibility fixture."""

    items: list[OwnerView] = Field(description="Active explicitly eligible demo owners")
    next_cursor: None = Field(default=None, description="Complete demo fixture")
