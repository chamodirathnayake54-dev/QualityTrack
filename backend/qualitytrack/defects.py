"""Capture and live read services; callers own the transaction boundary."""

from datetime import datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from qualitytrack.config import Settings
from qualitytrack.errors import Failure
from qualitytrack.models import Defect, DefectType, ProductionLine, Shift
from qualitytrack.schemas import Capture, DefectPage, DefectView, Filters
from qualitytrack.security import (
    Principal,
    decode_cursor,
    encode_cursor,
    load_principal,
    require,
)


# PUBLIC_INTERFACE
def capture_defect(session: Session, principal: Principal, capture: Capture):
    """Lock active type/line/shift in fixed order and persist captured snapshots."""
    require(principal, "defect.capture")
    lookups = []
    for model, identifier, field in (
        (DefectType, capture.defect_type_id, "defect_type_id"),
        (ProductionLine, capture.production_line_id, "production_line_id"),
        (Shift, capture.shift_id, "shift_id"),
    ):
        row = session.scalar(
            select(model)
            .where(model.id == identifier)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not row or row.retired:
            raise Failure(
                409,
                "lookup_unavailable",
                "A selected lookup is unavailable",
                {field: "Select an active configured value"},
            )
        lookups.append(row)
    # Recheck after waiting for locks rather than trusting a stale token grant.
    require(load_principal(session, principal.ref), "defect.capture")
    defect_type, line, shift = lookups
    defect = Defect(
        type_id=defect_type.id,
        type_code_at_capture=defect_type.code,
        type_label_at_capture=defect_type.label,
        part_number=capture.part_number,
        quantity_affected=capture.quantity_affected,
        production_line_id=line.id,
        production_line_code_at_capture=line.code,
        production_line_label_at_capture=line.label,
        shift_id=shift.id,
        shift_code_at_capture=shift.code,
        shift_label_at_capture=shift.label,
        severity=capture.severity.value,
        created_by_ref=principal.ref,
    )
    session.add(defect)
    session.flush()
    return defect


# PUBLIC_INTERFACE
def defect_view(row: Defect):
    """Project captured values only; no credential or child-table serialization."""
    return DefectView(
        id=row.id,
        part_number=row.part_number,
        defect_type={
            "id": row.type_id,
            "code_at_capture": row.type_code_at_capture,
            "label_at_capture": row.type_label_at_capture,
        },
        quantity_affected=row.quantity_affected,
        production_line={
            "id": row.production_line_id,
            "code_at_capture": row.production_line_code_at_capture,
            "label_at_capture": row.production_line_label_at_capture,
        },
        shift={
            "id": row.shift_id,
            "code_at_capture": row.shift_code_at_capture,
            "label_at_capture": row.shift_label_at_capture,
        },
        severity=row.severity,
        status=row.status,
        created_by_ref=row.created_by_ref,
        created_at=row.created_at,
        revision=row.revision,
    )


# PUBLIC_INTERFACE
def get_defect(session: Session, principal: Principal, identifier: UUID):
    """Require plant read access before revealing whether a record exists."""
    require(principal, "defect.read")
    row = session.get(Defect, identifier)
    if not row:
        raise Failure(404, "not_found", "Record was not found")
    return row


# PUBLIC_INTERFACE
def list_defects(
    session: Session,
    principal: Principal,
    settings: Settings,
    filters: Filters,
    cursor: str | None,
    limit: int,
):
    """Return a caller-bound descending keyset page with AND-combined filters."""
    require(principal, "defect.read")
    query = select(Defect)
    for name, column in (
        ("status", Defect.status),
        ("severity", Defect.severity),
        ("production_line_id", Defect.production_line_id),
        ("shift_id", Defect.shift_id),
        ("defect_type_id", Defect.type_id),
        ("part_number", Defect.part_number),
    ):
        value = getattr(filters, name)
        if value is not None:
            query = query.where(column == value)
    if filters.start_date:
        zone = ZoneInfo(settings.plant_zone)
        # Convert independent local boundaries: never add 24 UTC hours over DST.
        start = datetime.combine(filters.start_date, time.min, zone)
        end = datetime.combine(filters.end_date + timedelta(days=1), time.min, zone)
        query = query.where(Defect.created_at >= start, Defect.created_at < end)
    if cursor:
        instant, identifier = decode_cursor(settings, principal, filters, cursor)
        query = query.where(
            tuple_(Defect.created_at, Defect.id) < tuple_(instant, identifier)
        )
    rows = list(
        session.scalars(
            query.order_by(Defect.created_at.desc(), Defect.id.desc()).limit(limit + 1)
        )
    )
    more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        encode_cursor(settings, principal, filters, rows[-1].created_at, rows[-1].id)
        if more
        else None
    )
    return DefectPage(items=[defect_view(row) for row in rows], next_cursor=next_cursor)
