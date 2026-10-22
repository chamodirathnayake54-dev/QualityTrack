"""Consistent photo-free evidence snapshots and complete local PDF rendering."""

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)
from sqlalchemy import select, text

from qualitytrack.defects import defect_view, get_defect
from qualitytrack.errors import Failure
from qualitytrack.models import (
    ActionEvent,
    CorrectiveAction,
    DefectPhoto,
    DefectStatusEvent,
    RcaEntry,
)
from qualitytrack.security import load_principal, require


# PUBLIC_INTERFACE
@dataclass(frozen=True)
class Section:
    """Immutable table including every selected row and its expected count."""

    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    count: int


# PUBLIC_INTERFACE
@dataclass(frozen=True)
class EvidenceSnapshot:
    """Detached record context and all evidence from one PostgreSQL snapshot."""

    defect_id: str
    zone: str
    exported_at: str
    sections: tuple[Section, ...]


def _authorize(session, ref):
    caller = load_principal(session, ref)
    require(caller, "defect.read")
    require(caller, "defect.export")
    return caller


def _display(value, zone):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Evidence timestamp lacks an offset")
        return f"{value.astimezone(zone).isoformat()} [{zone.key}]"
    return "" if value is None else str(value)


def _section(title, headers, rows):
    rows = tuple(tuple(row) for row in rows)
    return Section(title, tuple(headers), rows, len(rows))


# PUBLIC_INTERFACE
def load_snapshot(sessions, ref, identifier, settings):
    """Load all evidence in a dedicated read-only repeatable-read transaction."""
    zone = ZoneInfo(settings.plant_zone)
    with sessions() as session, session.begin():
        # Must be the first statement, before authentication or evidence reads.
        session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )
        caller = _authorize(session, ref)
        parent = get_defect(session, caller, identifier)
        if session.get(DefectPhoto, identifier):
            raise Failure(500, "unsupported_evidence", "Evidence could not be exported")
        view = defect_view(parent).model_dump(mode="json")
        details = []
        for key, value in view.items():
            if isinstance(value, dict):
                details.extend(
                    (f"{key}.{name}", str(item)) for name, item in value.items()
                )
            elif key == "created_at":
                details.append((key, _display(parent.created_at, zone)))
            else:
                details.append((key, str(value)))
        causes = list(
            session.scalars(
                select(RcaEntry)
                .where(RcaEntry.defect_id == identifier)
                .order_by(RcaEntry.recorded_at, RcaEntry.id)
            )
        )
        actions = list(
            session.scalars(
                select(CorrectiveAction)
                .where(CorrectiveAction.defect_id == identifier)
                .order_by(CorrectiveAction.id)
            )
        )
        events = list(
            session.scalars(
                select(ActionEvent)
                .join(CorrectiveAction, CorrectiveAction.id == ActionEvent.action_id)
                .where(CorrectiveAction.defect_id == identifier)
                .order_by(ActionEvent.aggregate_revision, ActionEvent.id)
            )
        )
        history = list(
            session.scalars(
                select(DefectStatusEvent)
                .where(DefectStatusEvent.defect_id == identifier)
                .order_by(DefectStatusEvent.aggregate_revision)
            )
        )

        def cells(row, names):
            return tuple(_display(getattr(row, name), zone) for name in names)

        sections = (
            _section("Defect details", ("Field", "Value"), details),
            _section(
                "RCA",
                ("ID / actor / time", "Recorded cause"),
                (
                    (
                        f"{row.id}\n{row.recorded_by_ref}\n"
                        f"{_display(row.recorded_at, zone)}",
                        row.cause_text,
                    )
                    for row in causes
                ),
            ),
            _section(
                "Actions",
                ("ID / owner / due / status", "Description"),
                (
                    (
                        f"{row.id}\n{row.owner_ref}\n{row.due_date}\n{row.status}",
                        row.description,
                    )
                    for row in actions
                ),
            ),
            _section(
                "Action history",
                ("Event / action / actor / time / revision", "Evidence"),
                (
                    (
                        "\n".join(
                            cells(
                                row,
                                (
                                    "id",
                                    "action_id",
                                    "actor_ref",
                                    "occurred_at",
                                    "aggregate_revision",
                                ),
                            )
                        ),
                        f"{row.old_status or '(creation)'} -> {row.new_status}\n"
                        f"Completion notes: {row.completion_notes or ''}\n"
                        f"Reopen reason: {row.reopen_reason or ''}",
                    )
                    for row in events
                ),
            ),
            _section(
                "Status history",
                ("Event / actor / time / revision", "Transition"),
                (
                    (
                        "\n".join(
                            cells(
                                row,
                                (
                                    "id",
                                    "actor_ref",
                                    "occurred_at",
                                    "aggregate_revision",
                                ),
                            )
                        ),
                        f"{row.old_status} -> {row.new_status}",
                    )
                    for row in history
                ),
            ),
        )
        # The read transaction closes before any layout/render work.
        return EvidenceSnapshot(
            str(identifier),
            zone.key,
            _display(datetime.now(timezone.utc), zone),
            sections,
        )


# PUBLIC_INTERFACE
class PdfRenderer:
    """Render all snapshot rows with escaped Latin text and repeating headers."""

    # PUBLIC_INTERFACE
    def render_complete(self, snapshot):
        """Return complete A4 bytes or raise; never publish a partial buffer."""
        expected = (
            "Defect details",
            "RCA",
            "Actions",
            "Action history",
            "Status history",
        )
        if tuple(section.title for section in snapshot.sections) != expected:
            raise ValueError("Required evidence sections missing")
        styles = getSampleStyleSheet()
        body = styles["BodyText"]
        body.fontSize = 8
        body.leading = 11
        body.splitLongWords = True

        def paragraph(value):
            # Helvetica's WinAnsi text repertoire supports the settled Latin
            # demo. Fail rather than silently substitute unsupported glyphs.
            value.encode("cp1252", errors="strict")
            return Paragraph(escape(value).replace("\n", "<br/>"), body)

        story = [
            Paragraph("QualityTrack audit record", styles["Title"]),
            paragraph(f"Defect: {snapshot.defect_id}"),
            paragraph(f"Exported: {snapshot.exported_at}"),
            paragraph(f"Plant timezone: {snapshot.zone}"),
        ]
        for section in snapshot.sections:
            if len(section.rows) != section.count or any(
                len(row) != len(section.headers) for row in section.rows
            ):
                raise ValueError("Incomplete evidence section")
            story.extend([Spacer(1, 12), Paragraph(section.title, styles["Heading2"])])
            data = [[paragraph(value) for value in section.headers]]
            data.extend([paragraph(value) for value in row] for row in section.rows)
            if not section.rows:
                data.append([paragraph("No entries"), paragraph("")])
            table = LongTable(
                data,
                colWidths=[210, A4[0] - 282],
                repeatRows=1,
                splitByRow=1,
                splitInRow=1,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(table)
        with BytesIO() as buffer:
            document = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                leftMargin=36,
                rightMargin=36,
                topMargin=36,
                bottomMargin=36,
                title="QualityTrack audit record",
            )
            document.build(story)
            result = buffer.getvalue()
        if not result.startswith(b"%PDF-") or not result.rstrip().endswith(b"%%EOF"):
            raise ValueError("Incomplete PDF")
        return result


# PUBLIC_INTERFACE
def export_record(sessions, ref, identifier, settings, renderer=None):
    """Authorize, snapshot, render off-transaction, then reauthorize delivery."""
    snapshot = load_snapshot(sessions, ref, identifier, settings)
    try:
        output = (renderer or PdfRenderer()).render_complete(snapshot)
        if not output.startswith(b"%PDF-") or not output.rstrip().endswith(b"%%EOF"):
            raise ValueError("Incomplete PDF")
    except Exception:
        raise Failure(500, "export_failed", "Evidence could not be exported") from None
    with sessions() as session, session.begin():
        _authorize(session, ref)
    return output
