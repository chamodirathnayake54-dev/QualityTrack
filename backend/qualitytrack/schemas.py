"""Batch A wire contracts with strict capture validation."""

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Part = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]


# PUBLIC_INTERFACE
class Severity(str, Enum):
    """Allowed initial manual classifications."""

    critical = "Critical"
    major = "Major"
    minor = "Minor"


# PUBLIC_INTERFACE
class DefectStatus(str, Enum):
    """Allowed defect states, including spaces."""

    open = "Open"
    investigating = "Under Investigation"
    closed = "Closed"


# PUBLIC_INTERFACE
class Capture(BaseModel):
    """Photo-free capture, with trusted metadata forbidden in input."""

    model_config = ConfigDict(extra="forbid")
    part_number: Part = Field(description="Nonblank part number, at most 50 characters")
    defect_type_id: UUID = Field(description="Active configured type")
    quantity_affected: int = Field(
        strict=True, ge=1, le=1000000, description="Whole affected units"
    )
    production_line_id: UUID = Field(description="Active production line")
    shift_id: UUID = Field(description="Active shift")
    severity: Severity = Field(description="Required manual classification")


# PUBLIC_INTERFACE
class LoginRequest(BaseModel):
    """Local credential input; never echoed in errors."""

    model_config = ConfigDict(extra="forbid")
    username: Annotated[str, StringConstraints(min_length=1)] = Field(
        description="Case-sensitive local login name"
    )
    password: str = Field(description="Secret password", repr=False)

    @model_validator(mode="after")
    def _nonblank_username(self):
        if not self.username.strip():
            raise ValueError("Blank username")
        return self


# PUBLIC_INTERFACE
class TokenResponse(BaseModel):
    """Expiring bearer token issued after Argon2id verification."""

    access_token: str = Field(description="Signed access token")
    token_type: Literal["bearer"] = Field(default="bearer", description="Bearer scheme")
    expires_in: int = Field(default=3600, gt=0, description="Lifetime in seconds")


# PUBLIC_INTERFACE
class MeView(BaseModel):
    """Only the caller's current identity, explicit grants, and plant calendar."""

    ref: str = Field(description="Stable user reference")
    display_name: str = Field(description="Current caller display name")
    scope: Literal["plant"] = Field(default="plant", description="Single-plant scope")
    permissions: list[str] = Field(description="Current explicit operation names")
    plant_zone: str = Field(description="Resolved IANA plant timezone")


# PUBLIC_INTERFACE
class LookupView(BaseModel):
    """Active selectable production context."""

    id: UUID = Field(description="Stable lookup identifier")
    code: str = Field(description="Stable configured code")
    label: str = Field(description="Current display label")


# PUBLIC_INTERFACE
class TypeView(LookupView):
    """Type configuration view, not a configuration grant."""

    retired: bool = Field(description="Whether retired")
    revision: int = Field(description="Configuration revision")


# PUBLIC_INTERFACE
class LookupPage(BaseModel):
    """Complete small demo lookup collection."""

    items: list[LookupView] = Field(description="Active lookup choices")
    next_cursor: None = Field(default=None, description="No additional demo choices")


# PUBLIC_INTERFACE
class TypePage(BaseModel):
    """Selectable active types."""

    items: list[TypeView] = Field(description="Active type choices")
    next_cursor: None = Field(default=None, description="No additional demo choices")


# PUBLIC_INTERFACE
class CapturedLookup(BaseModel):
    """Historical code and label copied under lookup lock."""

    id: UUID = Field(description="Stable lookup identifier")
    code_at_capture: str = Field(description="Captured code")
    label_at_capture: str = Field(description="Captured label")


# PUBLIC_INTERFACE
class DefectView(BaseModel):
    """Captured defect context without photo bytes or inline children."""

    id: UUID = Field(description="Defect identifier")
    part_number: str = Field(description="Captured part number")
    defect_type: CapturedLookup = Field(description="Captured type context")
    quantity_affected: int = Field(description="Affected units")
    production_line: CapturedLookup = Field(description="Captured production line")
    shift: CapturedLookup = Field(description="Captured shift")
    severity: Severity = Field(description="Manual severity")
    status: DefectStatus = Field(description="Current state")
    created_by_ref: str = Field(description="Verified capture actor")
    created_at: datetime = Field(description="Server capture instant")
    has_photo: bool = Field(default=False, description="Always false in Batch A")
    revision: int = Field(description="Aggregate revision")


# PUBLIC_INTERFACE
class DefectPage(BaseModel):
    """Live keyset page, not an export snapshot."""

    items: list[DefectView] = Field(description="Permitted matching defects")
    next_cursor: str | None = Field(description="Signed continuation or null")


# PUBLIC_INTERFACE
class Filters(BaseModel):
    """AND-combined defect filters with paired inclusive local dates."""

    status: DefectStatus | None = None
    severity: Severity | None = None
    production_line_id: UUID | None = None
    shift_id: UUID | None = None
    defect_type_id: UUID | None = None
    part_number: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def _date_pair(self):
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("Supply both dates")
        if self.start_date and (
            self.start_date > self.end_date or self.end_date == date.max
        ):
            raise ValueError("Invalid date range")
        return self
