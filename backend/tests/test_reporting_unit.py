"""Batch C isolated calendar, cursor, retirement, PDF and API contracts."""

import base64
import re
import zlib
from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from qualitytrack import evidence as e
from qualitytrack import reporting as r
from qualitytrack.config import Settings
from qualitytrack.errors import Failure
from qualitytrack.main import create_app
from qualitytrack.security import Principal

SETTINGS = Settings("", "unit-only-" * 8, "America/New_York", True)
CALLER = Principal("test-reader", "Reader", frozenset({"defect.read", "type.retire"}))


def _pdf_text(output):
    """Decode ReportLab content streams without an extra PDF dependency."""
    streams = re.findall(rb"stream\r?\n(.*?)endstream", output, re.S)
    return b"\n".join(
        zlib.decompress(base64.a85decode(stream.strip(), adobe=True))
        for stream in streams
    )


def _snapshot(rows=()):
    titles = ("Defect details", "RCA", "Actions", "Action history", "Status history")
    return e.EvidenceSnapshot(
        str(uuid4()),
        "Etc/UTC",
        "2026-01-01T00:00:00+00:00 [Etc/UTC]",
        tuple(
            e.Section(title, ("Identity", "Evidence"), rows, len(rows))
            for title in titles
        ),
    )


@pytest.mark.parametrize(
    "instant,expected",
    [
        ("2026-03-08T04:59:00+00:00", "2026-03-07"),
        ("2026-03-08T05:00:00+00:00", "2026-03-08"),
        ("2026-03-09T04:00:00+00:00", "2026-03-09"),
        ("2026-11-01T05:30:00+00:00", "2026-11-01"),
        ("2026-11-01T06:30:00+00:00", "2026-11-01"),
    ],
)
# PUBLIC_INTERFACE
def test_calendar_dst_boundaries(instant, expected):
    """Local dates survive short days and both occurrences of a repeated hour."""
    assert (
        r.plant_today(SETTINGS, datetime.fromisoformat(instant)).isoformat() == expected
    )


# PUBLIC_INTERFACE
def test_calendar_invalid_and_naive():
    """Unavailable zones fail safely and naive clocks cannot leak process timezone."""
    with pytest.raises(Failure) as caught:
        r.plant_today(replace(SETTINGS, plant_zone="not/a-zone"))
    assert caught.value.problem.status == 503
    with pytest.raises(ValueError):
        r.plant_today(SETTINGS, datetime(2026, 1, 1))


@pytest.mark.parametrize("change", ["tamper", "caller", "zone", "kind", "shape"])
# PUBLIC_INTERFACE
def test_overdue_cursor_rejects_context(monkeypatch, change):
    """Signed continuations reject tampering, cross-caller/zone/kind and bad keys."""
    monkeypatch.setattr(r, "load_principal", lambda *_: CALLER)
    context = f"overdue-v1:{SETTINGS.plant_zone}:due_date,id"
    raw = ["2026-01-02", "2026-01-01", str(uuid4())]
    if change == "shape":
        raw = ["2026-01-01"]
    token = r._cursor(
        SETTINGS, CALLER, context if change != "kind" else "other", key=raw
    )
    settings, caller = SETTINGS, CALLER
    if change == "tamper":
        token = token[:-8] + "tampered"
    elif change == "caller":
        caller = replace(CALLER, ref="someone-else")
    elif change == "zone":
        settings = replace(SETTINGS, plant_zone="Etc/UTC")
    with pytest.raises(Failure) as caught:
        r.overdue_actions(MagicMock(), caller, settings, token)
    assert caught.value.problem.status == 400


@pytest.mark.parametrize(
    "header,retired,status",
    [
        (None, False, 428),
        ('W/"1"', False, 400),
        ('"2"', False, 412),
        ('"1"', True, 409),
        ('"1"', False, 200),
    ],
)
# PUBLIC_INTERFACE
def test_retirement_preconditions(monkeypatch, header, retired, status):
    """Retirement distinguishes missing/malformed/stale/same-state and success."""
    monkeypatch.setattr(r, "load_principal", lambda *_: CALLER)
    row = SimpleNamespace(
        id=uuid4(), code="TYPE", label="Type", revision=1, retired=retired
    )
    session = MagicMock()
    session.scalar.return_value = row
    if status == 200:
        assert r.retire_type(session, CALLER, row.id, header)["revision"] == 2
        assert row.retired
        session.flush.assert_called_once()
    else:
        with pytest.raises(Failure) as caught:
            r.retire_type(session, CALLER, row.id, header)
        assert caught.value.problem.status == status
        assert row.revision == 1
        session.flush.assert_not_called()


# PUBLIC_INTERFACE
def test_retirement_denial_before_query():
    """A caller with no retirement grant cannot probe existence or preconditions."""
    session = MagicMock()
    with pytest.raises(Failure) as caught:
        r.retire_type(session, replace(CALLER, permissions=frozenset()), uuid4(), None)
    assert caught.value.problem.status == 403
    session.scalar.assert_not_called()


# PUBLIC_INTERFACE
def test_pdf_required_sections_and_counts():
    """A missing section or mismatched expected row count cannot render success."""
    snapshot = _snapshot()
    for invalid in (
        replace(snapshot, sections=snapshot.sections[:-1]),
        replace(
            snapshot,
            sections=(replace(snapshot.sections[0], count=1), *snapshot.sections[1:]),
        ),
    ):
        with pytest.raises(ValueError):
            e.PdfRenderer().render_complete(invalid)


# PUBLIC_INTERFACE
def test_pdf_immutable_snapshot():
    """Snapshot and section collections cannot be changed during rendering."""
    snapshot = _snapshot()
    with pytest.raises(FrozenInstanceError):
        snapshot.zone = "other"
    with pytest.raises(FrozenInstanceError):
        snapshot.sections[0].count = 3


# PUBLIC_INTERFACE
def test_pdf_empty_sections_a4_and_complete():
    """Empty evidence is explicit and output is complete A4 with all headings."""
    output = e.PdfRenderer().render_complete(_snapshot())
    content = _pdf_text(output)
    assert output.startswith(b"%PDF-") and output.rstrip().endswith(b"%%EOF")
    assert b"/MediaBox [ 0 0 595.2756 841.8898 ]" in output
    for heading in (
        b"RCA",
        b"Actions",
        b"Action history",
        b"Status history",
        b"No entries",
    ):
        assert heading in content


# PUBLIC_INTERFACE
def test_pdf_long_text_repeated_headers_and_escape():
    """Every row survives multipage layout; markup and URL text remain literal."""
    rows = tuple(
        (f"row-{index}", f"START{index} " + "long text " * 180 + f" END{index}")
        for index in range(12)
    ) + (("markup", '<b>literal</b> & <img src="https://invalid.example/x"/>'),)
    output = e.PdfRenderer().render_complete(_snapshot(rows))
    content = _pdf_text(output)
    for index in range(12):
        assert f"START{index}".encode() in content and f"END{index}".encode() in content
    assert b"(literal)" in content and b"(/b)" in content
    assert b"invalid.example" in content
    assert content.count(b"(Identity)") > 5
    assert output.count(b"/Type /Page\n") > 1


# PUBLIC_INTERFACE
def test_pdf_single_oversized_row():
    """An individual row longer than a page is split rather than clipped."""
    content = _pdf_text(
        e.PdfRenderer().render_complete(_snapshot((("one", "word " * 1600 + "TAIL"),)))
    )
    assert content.count(b"TAIL") == 5


@pytest.mark.parametrize("mode", ["exception", "partial", "revoked"])
# PUBLIC_INTERFACE
def test_export_failure_discards_bytes(monkeypatch, mode):
    """Renderer failure/partial output and final revocation cannot deliver PDF."""
    monkeypatch.setattr(e, "load_snapshot", lambda *_: _snapshot())
    renderer = MagicMock()
    renderer.render_complete.return_value = b"%PDF-partial"
    if mode == "exception":
        renderer.render_complete.side_effect = RuntimeError("private evidence")
    if mode == "revoked":
        renderer.render_complete.return_value = b"%PDF-complete\n%%EOF"
        monkeypatch.setattr(
            e,
            "_authorize",
            lambda *_: (_ for _ in ()).throw(
                Failure(403, "forbidden", "Not permitted")
            ),
        )
    with pytest.raises(Failure) as caught:
        e.export_record(MagicMock(), CALLER.ref, uuid4(), SETTINGS, renderer)
    assert caught.value.problem.status == (403 if mode == "revoked" else 500)
    assert "private evidence" not in str(caught.value.problem)


# PUBLIC_INTERFACE
def test_openapi_security_and_error_media():
    """All twenty operations describe security and actual safe Problem media."""
    schema = create_app().openapi()
    operations = [
        (path, op)
        for path, methods in schema["paths"].items()
        for op in methods.values()
    ]
    assert len(operations) == 20
    for path, op in operations:
        assert op["summary"] and op["description"]
        assert op["security"] == (
            [] if path.endswith("/login") else [{"BearerAuth": []}]
        )
        assert "application/problem+json" in op["responses"]["403"]["content"]


# PUBLIC_INTERFACE
def test_openapi_transition_headers():
    """If-Match explains 428 runtime semantics; successful writes document ETag."""
    schema = create_app().openapi()
    for path, methods in schema["paths"].items():
        if path.endswith(("/transitions", "/retire")):
            op = methods["post"]
            match = next(p for p in op["parameters"] if p["name"] == "If-Match")
            assert "428" in match["description"]
            assert all(str(code) in op["responses"] for code in (400, 409, 412, 428))
            assert "ETag" in op["responses"]["200"]["headers"]


# PUBLIC_INTERFACE
def test_openapi_required_outputs_and_capture():
    """Serialized defaults are required; capture fields remain explicit."""
    schema = create_app().openapi()["components"]["schemas"]
    assert "has_photo" in schema["DefectView"]["required"]
    assert "token_type" in schema["TokenResponse"]["required"]
    assert "next_cursor" in schema["OwnerPage"]["required"]
    assert set(schema["Capture"]["required"]) == {
        "part_number",
        "defect_type_id",
        "production_line_id",
        "shift_id",
        "quantity_affected",
        "severity",
    }
    assert schema["Capture"]["properties"]["severity"]["$ref"].startswith(
        "#/components/"
    )


# PUBLIC_INTERFACE
def test_openapi_pdf_and_no_stretch_routes():
    """PDF declares binary media and no photo/analytics routes are activated."""
    paths = create_app().openapi()["paths"]
    assert set(
        paths["/api/v1/defects/{defect_id}/audit.pdf"]["get"]["responses"]["200"][
            "content"
        ]
    ) == {"application/pdf"}
    assert not any("analytics" in path or path.endswith("/photo") for path in paths)


# PUBLIC_INTERFACE
def test_openapi_references_resolve():
    """Every generated schema reference resolves within the actual OpenAPI document."""
    schema = create_app().openapi()

    def walk(value):
        if isinstance(value, dict):
            if "$ref" in value:
                target = schema
                for part in value["$ref"].removeprefix("#/").split("/"):
                    target = target[part]
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)


# PUBLIC_INTERFACE
def test_pdf_latin_text_and_unsupported_glyph():
    """Accented Latin renders; unsupported glyphs cannot silently lose evidence."""
    output = e.PdfRenderer().render_complete(_snapshot((("id", "café"),)))
    assert b"caf" in _pdf_text(output)
    with pytest.raises(UnicodeEncodeError):
        e.PdfRenderer().render_complete(_snapshot((("id", "☃"),)))
