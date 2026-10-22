"""Full LLD physical model; workflow commands beyond capture are not exposed."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

OPERATIONS = (
    "defect.capture",
    "defect.read",
    "cause.create",
    "defect.investigate",
    "defect.close",
    "defect.reopen",
    "action.assign",
    "action.progress",
    "action.complete",
    "action.reopen",
    "defect.export",
    "type.retire",
    "analytics.read",
)
DEFECT_STATES = "'Open', 'Under Investigation', 'Closed'"
ACTION_STATES = "'Open', 'In Progress', 'Complete'"


def _fk(target):
    return ForeignKey(target, ondelete="RESTRICT")


def _text_check(column, maximum=None):
    # POSIX whitespace agrees with Python strip for the demo's Latin text.
    expression = f"{column} ~ '[^[:space:]]'"
    if maximum:
        expression += f" AND char_length({column}) <= {maximum}"
    return CheckConstraint(expression, name=f"ck_{column}_content")


# PUBLIC_INTERFACE
class Base(DeclarativeBase):
    """SQLAlchemy model metadata shared with Alembic."""


# PUBLIC_INTERFACE
class User(Base):
    """Stable identity and local Argon2id credential mapping."""

    __tablename__ = "users"
    ref: Mapped[str] = mapped_column(Text, primary_key=True)
    issuer: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    username: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="uq_users_identity"),
        _text_check("username"),
        _text_check("display_name"),
    )


# PUBLIC_INTERFACE
class Permission(Base):
    """Explicit installation-wide operation grant; no implicit persona grants."""

    __tablename__ = "permissions"
    user_ref: Mapped[str] = mapped_column(_fk("users.ref"), primary_key=True)
    operation: Mapped[str] = mapped_column(Text, primary_key=True)
    scope: Mapped[str] = mapped_column(Text, primary_key=True, server_default="plant")
    __table_args__ = (
        CheckConstraint("scope = 'plant'", name="ck_permission_scope"),
        CheckConstraint(
            "operation IN (" + ",".join(repr(x) for x in OPERATIONS) + ")",
            name="ck_permission_operation",
        ),
    )


class _Lookup:
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(Text, unique=True)
    label: Mapped[str] = mapped_column(Text)
    retired: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )


# PUBLIC_INTERFACE
class ProductionLine(_Lookup, Base):
    """Configured production line with retained historical references."""

    __tablename__ = "production_line"
    __table_args__ = (_text_check("code"), _text_check("label"))


# PUBLIC_INTERFACE
class Shift(_Lookup, Base):
    """Named shift category, not a shift schedule."""

    __tablename__ = "shift"
    __table_args__ = (_text_check("code"), _text_check("label"))


# PUBLIC_INTERFACE
class DefectType(_Lookup, Base):
    """Stable defect taxonomy with retirement revision."""

    __tablename__ = "defect_type"
    revision: Mapped[int] = mapped_column(BigInteger, default=1, server_default="1")
    __table_args__ = (
        _text_check("code"),
        _text_check("label"),
        CheckConstraint("revision > 0", name="ck_type_revision"),
    )


# PUBLIC_INTERFACE
class Defect(Base):
    """Defect aggregate root and immutable captured production context."""

    __tablename__ = "defect"
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, default=uuid4)
    type_id: Mapped[UUID] = mapped_column(_fk("defect_type.id"))
    type_code_at_capture: Mapped[str] = mapped_column(Text)
    type_label_at_capture: Mapped[str] = mapped_column(Text)
    part_number: Mapped[str] = mapped_column(String(50))
    quantity_affected: Mapped[int] = mapped_column(BigInteger)
    production_line_id: Mapped[UUID] = mapped_column(_fk("production_line.id"))
    shift_id: Mapped[UUID] = mapped_column(_fk("shift.id"))
    production_line_code_at_capture: Mapped[str] = mapped_column(Text)
    production_line_label_at_capture: Mapped[str] = mapped_column(Text)
    shift_code_at_capture: Mapped[str] = mapped_column(Text)
    shift_label_at_capture: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="Open", server_default="Open")
    created_by_ref: Mapped[str] = mapped_column(_fk("users.ref"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revision: Mapped[int] = mapped_column(BigInteger, default=1, server_default="1")
    __table_args__ = (
        _text_check("part_number", 50),
        CheckConstraint(
            "quantity_affected BETWEEN 1 AND 1000000", name="ck_defect_quantity"
        ),
        CheckConstraint(
            "severity IN ('Critical','Major','Minor')", name="ck_defect_severity"
        ),
        CheckConstraint(f"status IN ({DEFECT_STATES})", name="ck_defect_status"),
        CheckConstraint("revision > 0", name="ck_defect_revision"),
        Index("ix_defect_created", "created_at", "id"),
        Index("ix_defect_line", "production_line_id"),
        Index("ix_defect_shift", "shift_id"),
    )


# PUBLIC_INTERFACE
class DefectPhoto(Base):
    """Reserved full-ERD photo storage; Batch A rejects every photo part."""

    __tablename__ = "defect_photo"
    defect_id: Mapped[UUID] = mapped_column(_fk("defect.id"), primary_key=True)
    media_type: Mapped[str] = mapped_column(Text)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    __table_args__ = (
        CheckConstraint(
            "media_type IN ('image/jpeg','image/png')", name="ck_photo_type"
        ),
        CheckConstraint("octet_length(content) <= 10485760", name="ck_photo_size"),
    )


# PUBLIC_INTERFACE
class RcaEntry(Base):
    """Append-only recorded cause attributed to its verified actor."""

    __tablename__ = "rca_entry"
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, default=uuid4)
    defect_id: Mapped[UUID] = mapped_column(_fk("defect.id"))
    cause_text: Mapped[str] = mapped_column(Text)
    recorded_by_ref: Mapped[str] = mapped_column(_fk("users.ref"))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        _text_check("cause_text", 2000),
        Index("ix_rca_parent", "defect_id", "recorded_at", "id"),
    )


# PUBLIC_INTERFACE
class CorrectiveAction(Base):
    """Assigned work with an explicit initial state and calendar due date."""

    __tablename__ = "corrective_action"
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, default=uuid4)
    defect_id: Mapped[UUID] = mapped_column(_fk("defect.id"))
    description: Mapped[str] = mapped_column(Text)
    owner_ref: Mapped[str] = mapped_column(_fk("users.ref"))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        _text_check("description", 2000),
        CheckConstraint(f"status IN ({ACTION_STATES})", name="ck_action_status"),
        Index("ix_action_parent", "defect_id", "id"),
        Index("ix_action_owner", "owner_ref", "id"),
        Index(
            "ix_action_due_incomplete",
            "due_date",
            "id",
            postgresql_where=(status != "Complete"),
        ),
    )


# PUBLIC_INTERFACE
class DefectStatusEvent(Base):
    """Immutable successful status transition in aggregate revision order."""

    __tablename__ = "defect_status_event"
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, default=uuid4)
    defect_id: Mapped[UUID] = mapped_column(_fk("defect.id"))
    old_status: Mapped[str] = mapped_column(Text)
    new_status: Mapped[str] = mapped_column(Text)
    actor_ref: Mapped[str] = mapped_column(_fk("users.ref"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    aggregate_revision: Mapped[int] = mapped_column(BigInteger)
    __table_args__ = (
        CheckConstraint(
            f"old_status IN ({DEFECT_STATES}) AND new_status IN ({DEFECT_STATES})"
            " AND old_status <> new_status",
            name="ck_defect_event_states",
        ),
        CheckConstraint("aggregate_revision > 0", name="ck_defect_event_revision"),
        UniqueConstraint(
            "defect_id", "aggregate_revision", name="uq_defect_event_revision"
        ),
    )


# PUBLIC_INTERFACE
class ActionEvent(Base):
    """Immutable creation/progress/completion/reopening evidence."""

    __tablename__ = "action_event"
    id: Mapped[UUID] = mapped_column(PGUUID, primary_key=True, default=uuid4)
    action_id: Mapped[UUID] = mapped_column(_fk("corrective_action.id"))
    old_status: Mapped[str | None] = mapped_column(Text)
    new_status: Mapped[str] = mapped_column(Text)
    actor_ref: Mapped[str] = mapped_column(_fk("users.ref"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    aggregate_revision: Mapped[int] = mapped_column(BigInteger)
    completion_notes: Mapped[str | None] = mapped_column(Text)
    reopen_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint(
            f"new_status IN ({ACTION_STATES}) AND "
            f"(old_status IS NULL OR old_status IN ({ACTION_STATES})) AND "
            "(old_status IS NULL OR old_status <> new_status)",
            name="ck_action_event_states",
        ),
        CheckConstraint("aggregate_revision > 0", name="ck_action_event_revision"),
        CheckConstraint(
            "(new_status = 'Complete' AND completion_notes IS NOT NULL AND "
            "completion_notes ~ '[^[:space:]]' AND "
            "char_length(completion_notes) <= 2000) OR "
            "(new_status <> 'Complete' AND completion_notes IS NULL)",
            name="ck_action_completion_notes",
        ),
        CheckConstraint(
            "(old_status = 'Complete' AND new_status = 'In Progress' AND "
            "reopen_reason IS NOT NULL AND reopen_reason ~ '[^[:space:]]' AND "
            "char_length(reopen_reason) <= 2000) OR "
            "((old_status IS DISTINCT FROM 'Complete' OR "
            "new_status <> 'In Progress') AND reopen_reason IS NULL)",
            name="ck_action_reopen_reason",
        ),
        UniqueConstraint(
            "action_id", "aggregate_revision", name="uq_action_event_revision"
        ),
    )
