"""Stage 5 G01-G10 additions; photo and analytics scope deliberately excluded.

Defect QA-B3-001 (fixed in working tree based on b26c9888): UUID positions
must be strings before conversion inside the controlled invalid_cursor
boundary. The active G10 regression covers child cursors; related defects
and overdue cursor regressions cover the same previously unsafe conversion.
"""

import hashlib
import hmac
import json
from dataclasses import replace
from datetime import date
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from test_reporting_postgres import _grant
from test_reporting_unit import _pdf_text
from test_workflow_postgres import _action, _counts

from qualitytrack import evidence, reporting
from qualitytrack.errors import Problem
from qualitytrack.main import create_app
from qualitytrack.models import (
    ActionEvent,
    CorrectiveAction,
    Defect,
    DefectStatusEvent,
    DefectType,
    Permission,
    RcaEntry,
    User,
)
from qualitytrack.reporting import OverduePage
from qualitytrack.schemas import (
    DefectPage,
    DefectView,
    LookupPage,
    MeView,
    TokenResponse,
    TypePage,
    TypeView,
)
from qualitytrack.workflow_schemas import (
    ActionEventPage,
    ActionPage,
    ActionView,
    CausePage,
    CauseView,
    DefectEventPage,
    OwnerPage,
)

PREFIX = "/api/v1"
MODELS = {
    model.__name__: model
    for model in (
        Problem,
        OverduePage,
        DefectPage,
        DefectView,
        LookupPage,
        MeView,
        TokenResponse,
        TypePage,
        TypeView,
        ActionEventPage,
        ActionPage,
        ActionView,
        CausePage,
        CauseView,
        DefectEventPage,
        OwnerPage,
    )
}


def _wire(client, response, template, method="get", status=200, code=None):
    """Check wire details against published required fields and response DTOs."""
    assert response.status_code == status
    assert response.headers["cache-control"] == "private, no-store"
    operation = client.app.openapi()["paths"][PREFIX + template][method]
    content = operation["responses"][str(status)]["content"]
    media = response.headers["content-type"].split(";")[0]
    assert media in content
    if media == "application/pdf":
        assert response.content.startswith(b"%PDF-")
        assert response.content.rstrip().endswith(b"%%EOF")
        identifier = response.request.url.path.split("/")[-2]
        assert response.headers["content-disposition"] == (
            f'attachment; filename="defect-{identifier}.pdf"'
        )
        return response.content
    name = content[media]["schema"]["$ref"].split("/")[-1]
    body = response.json()
    published = client.app.openapi()["components"]["schemas"][name]
    # DTO validation plus published required fields prevents defaults from
    # concealing missing wire properties. This is not full JSON Schema evidence.
    assert set(published.get("required", ())) <= body.keys()
    assert body.keys() <= published["properties"].keys()
    MODELS[name].model_validate(body, strict=False)
    if code is not None:
        assert media == "application/problem+json"
        assert body["status"] == status and body["code"] == code
        assert {"type", "title", "status", "code"} <= body.keys()
        assert body["type"] == "about:blank"
        if "field_errors" in body:
            assert isinstance(body["field_errors"], dict)
        assert "content-disposition" not in response.headers
        assert not response.content.startswith(b"%PDF")
        for marker in ("private-fault-marker", "password_hash", "SELECT ", "Traceback"):
            assert marker not in response.text
    elif "ETag" in operation["responses"][str(status)].get("headers", {}):
        assert type(body["revision"]) is int and body["revision"] > 0
        assert response.headers["etag"] == f'"{body["revision"]}"'
    return body


def _capture(client, headers, payload):
    return client.post(
        PREFIX + "/defects",
        headers=headers,
        files={"capture": (None, json.dumps(payload), "application/json")},
    )


@pytest.fixture
# PUBLIC_INTERFACE
def gap_record(client, auth, capture_payload):
    """Create one isolated parent and callers for missing HTTP scenarios."""
    headers = auth()
    supervisor = auth("sample-supervisor")
    result = _capture(client, headers, capture_payload)
    body = _wire(client, result, "/defects", "post", 201)
    return body["id"], headers, supervisor


def _requests(identifier, action_id, type_id):
    """Describe E08-E20 with valid input for auth/existence checks."""
    return [
        ("get", f"/defects/{identifier}", "/defects/{defect_id}", {}),
        (
            "post",
            f"/defects/{identifier}/causes",
            "/defects/{defect_id}/causes",
            {"json": {"text": "Saved"}},
        ),
        ("get", f"/defects/{identifier}/causes", "/defects/{defect_id}/causes", {}),
        (
            "post",
            f"/defects/{identifier}/transitions",
            "/defects/{defect_id}/transitions",
            {"json": {"target_status": "Under Investigation"}},
        ),
        (
            "post",
            f"/defects/{identifier}/actions",
            "/defects/{defect_id}/actions",
            {"json": _action()},
        ),
        ("get", f"/defects/{identifier}/actions", "/defects/{defect_id}/actions", {}),
        (
            "get",
            "/assignable-users",
            "/assignable-users",
            {"params": {"defect_id": identifier}},
        ),
        (
            "post",
            f"/actions/{action_id}/transitions",
            "/actions/{action_id}/transitions",
            {"json": {"target_status": "Complete", "completion_notes": "Done"}},
        ),
        ("get", f"/defects/{identifier}/history", "/defects/{defect_id}/history", {}),
        ("get", f"/actions/{action_id}/history", "/actions/{action_id}/history", {}),
        ("get", "/overdue-actions", "/overdue-actions", {}),
        (
            "get",
            f"/defects/{identifier}/audit.pdf",
            "/defects/{defect_id}/audit.pdf",
            {},
        ),
        (
            "post",
            f"/defect-types/{type_id}/retire",
            "/defect-types/{type_id}/retire",
            {"json": {}},
        ),
    ]


# PUBLIC_INTERFACE
def test_g02_missing_bearer_remaining_operations(client):
    """E08-E20 reject absent bearer before lookup or revision checks."""
    for method, path, template, kwargs in _requests(uuid4(), uuid4(), uuid4()):
        result = client.request(method, PREFIX + path, **kwargs)
        _wire(client, result, template, method, 401, "invalid_token")


@pytest.mark.parametrize("header", ["Bearer corrupt", "Basic private-fault-marker"])
# PUBLIC_INTERFACE
def test_g02_invalid_bearer_http(client, header):
    """Representative invalid-token transport rejects without echo."""
    result = client.get(PREFIX + "/me", headers={"Authorization": header})
    _wire(client, result, "/me", status=401, code="invalid_token")
    assert header not in result.text


# PUBLIC_INTERFACE
def test_g03_authorized_absent_resources(client, auth, database):
    """Missing workflow, owner, PDF and type resources produce exact safe 404."""
    headers = auth()
    _grant(database)
    for method, path, template, kwargs in _requests(uuid4(), uuid4(), uuid4()):
        if path == "/overdue-actions" or template == "/defects/{defect_id}":
            continue  # Existing detail 404 is already covered.
        result = client.request(method, PREFIX + path, headers=headers, **kwargs)
        _wire(client, result, template, method, 404, "not_found")


@pytest.mark.parametrize("field", ["defect_type_id", "production_line_id", "shift_id"])
# PUBLIC_INTERFACE
def test_g03_missing_capture_lookup(client, auth, capture_payload, database, field):
    """Each missing lookup rejects capture with safe feedback and no inserted row."""
    capture_payload[field] = str(uuid4())
    result = _capture(client, auth(), capture_payload)
    body = _wire(client, result, "/defects", "post", 409, "lookup_unavailable")
    assert set(body["field_errors"]) == {field}
    with database[2]() as session:
        assert session.scalar(select(func.count()).select_from(Defect)) == 0


# PUBLIC_INTERFACE
def test_g04_capture_accepted_http_boundaries(client, auth, capture_payload):
    """The missing 50-character part and quantity-one HTTP acceptance is explicit."""
    capture_payload.update(part_number=" " + "P" * 50 + " ", quantity_affected=1)
    body = _wire(
        client, _capture(client, auth(), capture_payload), "/defects", "post", 201
    )
    assert body["part_number"] == "P" * 50 and body["quantity_affected"] == 1


@pytest.mark.parametrize("length", [1, 2000, 2001])
# PUBLIC_INTERFACE
def test_g04_cause_http_boundaries(client, gap_record, database, length):
    """Cause HTTP bounds bridge unit validation and unchanged aggregate evidence."""
    identifier, headers, _ = gap_record
    before = _counts(database, identifier)
    result = client.post(
        f"{PREFIX}/defects/{identifier}/causes",
        headers=headers,
        json={"text": " " + "C" * length + " "},
    )
    if length > 2000:
        _wire(
            client,
            result,
            "/defects/{defect_id}/causes",
            "post",
            422,
            "validation_failed",
        )
        assert _counts(database, identifier) == before
    else:
        body = _wire(client, result, "/defects/{defect_id}/causes", "post", 201)
        assert body["text"] == "C" * length
        assert _counts(database, identifier) == ("Open", 2, 1, 0, 0, 0)


@pytest.mark.parametrize("length", [1, 2000])
# PUBLIC_INTERFACE
def test_g04_action_accepted_text_and_cycle_boundaries(
    client, gap_record, database, length
):
    """Accepted trimmed description, completion notes and reopen reasons persist."""
    identifier, headers, supervisor = gap_record
    value = "X" * length
    result = client.post(
        f"{PREFIX}/defects/{identifier}/actions",
        headers=headers,
        json=_action(
            "Complete",
            description=" " + value + " ",
            completion_notes=" " + value + " ",
        ),
    )
    body = _wire(client, result, "/defects/{defect_id}/actions", "post", 201)
    assert body["description"] == value
    action_id = body["id"]
    result = client.post(
        f"{PREFIX}/actions/{action_id}/transitions",
        headers={**supervisor, "If-Match": result.headers["etag"]},
        json={"target_status": "In Progress", "reopen_reason": " " + value + " "},
    )
    _wire(client, result, "/actions/{action_id}/transitions", "post")
    result = client.post(
        f"{PREFIX}/actions/{action_id}/transitions",
        headers={**headers, "If-Match": result.headers["etag"]},
        json={"target_status": "Complete", "completion_notes": " " + value + " "},
    )
    _wire(client, result, "/actions/{action_id}/transitions", "post")
    with database[2]() as session:
        rows = list(
            session.scalars(
                select(ActionEvent)
                .where(ActionEvent.action_id == UUID(action_id))
                .order_by(ActionEvent.aggregate_revision)
            )
        )
        assert [row.completion_notes for row in rows] == [value, None, value]
        assert [row.reopen_reason for row in rows] == [None, value, None]


@pytest.mark.parametrize("field", ["completion_notes", "reopen_reason"])
@pytest.mark.parametrize("value", [None, " ", "X" * 2001])
# PUBLIC_INTERFACE
def test_g04_conditional_transition_rejections(
    client, gap_record, database, field, value
):
    """Missing/blank/oversized conditional evidence leaves rows and events intact."""
    identifier, headers, supervisor = gap_record
    reopening = field == "reopen_reason"
    created = client.post(
        f"{PREFIX}/defects/{identifier}/actions",
        headers=headers,
        json=_action("Complete", completion_notes="Done") if reopening else _action(),
    )
    _wire(client, created, "/defects/{defect_id}/actions", "post", 201)
    before = _counts(database, identifier)
    body = {"target_status": "In Progress" if reopening else "Complete", field: value}
    result = client.post(
        f"{PREFIX}/actions/{created.json()['id']}/transitions",
        headers={
            **(supervisor if reopening else headers),
            "If-Match": created.headers["etag"],
        },
        json=body,
    )
    code = "reopening_reason_required" if reopening else "completion_notes_required"
    _wire(
        client,
        result,
        "/actions/{action_id}/transitions",
        "post",
        422,
        code if value is None else "validation_failed",
    )
    assert _counts(database, identifier) == before


@pytest.mark.parametrize("value", [" ", "X" * 2001])
# PUBLIC_INTERFACE
def test_g04_initial_complete_notes_rejection(client, gap_record, database, value):
    """Previously unasserted initial Complete notes text bounds reject atomically."""
    identifier, headers, _ = gap_record
    before = _counts(database, identifier)
    result = client.post(
        f"{PREFIX}/defects/{identifier}/actions",
        headers=headers,
        json=_action("Complete", completion_notes=value),
    )
    _wire(
        client, result, "/defects/{defect_id}/actions", "post", 422, "validation_failed"
    )
    assert _counts(database, identifier) == before


# PUBLIC_INTERFACE
def test_g05_page_size_contracts(client, gap_record, database):
    """51 rows distinguish default50, accepted1/100 and rejected0/101 at HTTP."""
    identifier, headers, _ = gap_record
    parent_id, action_id = UUID(identifier), uuid4()
    # Fixture rows avoid rebuilding already-covered command/keyset behavior.
    with database[2]() as session, session.begin():
        source = session.get(Defect, parent_id)
        for index in range(51):
            if index:
                session.add(
                    Defect(
                        **{
                            column.name: getattr(source, column.name)
                            for column in Defect.__table__.columns
                            if column.name != "id"
                        },
                        id=uuid4(),
                    )
                )
            session.add(
                RcaEntry(
                    defect_id=parent_id,
                    cause_text=f"Cause {index}",
                    recorded_by_ref="sample-engineer",
                )
            )
            session.add(
                CorrectiveAction(
                    id=action_id if index == 0 else uuid4(),
                    defect_id=parent_id,
                    description=f"Work {index}",
                    owner_ref="sample-engineer",
                    due_date=date(2000, 1, 1),
                    status="Open",
                )
            )
            session.add(
                DefectStatusEvent(
                    defect_id=parent_id,
                    old_status="Open",
                    new_status="Under Investigation",
                    actor_ref="sample-engineer",
                    aggregate_revision=index + 2,
                )
            )
        session.flush()
        for index in range(51):
            session.add(
                ActionEvent(
                    action_id=action_id,
                    old_status=None,
                    new_status="Open",
                    actor_ref="sample-engineer",
                    aggregate_revision=index + 2,
                )
            )
    paths = [
        ("/defects", "/defects"),
        (f"/defects/{identifier}/causes", "/defects/{defect_id}/causes"),
        (f"/defects/{identifier}/actions", "/defects/{defect_id}/actions"),
        (f"/defects/{identifier}/history", "/defects/{defect_id}/history"),
        (f"/actions/{action_id}/history", "/actions/{action_id}/history"),
        ("/overdue-actions", "/overdue-actions"),
    ]
    for path, template in paths:
        for limit, expected in ((None, 50), (1, 1), (100, 51)):
            result = client.get(
                PREFIX + path,
                headers=headers,
                params={} if limit is None else {"limit": limit},
            )
            body = _wire(client, result, template)
            assert len(body["items"]) == expected
            assert bool(body["next_cursor"]) == (expected < 51)
        for limit in (0, 101):
            result = client.get(PREFIX + path, headers=headers, params={"limit": limit})
            _wire(client, result, template, status=422, code="validation_failed")


# PUBLIC_INTERFACE
def test_g05_invalid_resource_identifiers(client, auth):
    """Detail, children, action history and required owner UUID fail at HTTP."""
    headers = auth()
    for suffix in ("", "/causes", "/actions", "/history"):
        result = client.get(f"{PREFIX}/defects/bad{suffix}", headers=headers)
        _wire(
            client,
            result,
            "/defects/{defect_id}" + suffix,
            status=422,
            code="validation_failed",
        )
    result = client.get(PREFIX + "/actions/bad/history", headers=headers)
    _wire(
        client,
        result,
        "/actions/{action_id}/history",
        status=422,
        code="validation_failed",
    )
    for params in ({}, {"defect_id": "bad"}):
        result = client.get(
            PREFIX + "/assignable-users", headers=headers, params=params
        )
        _wire(client, result, "/assignable-users", status=422, code="validation_failed")


# PUBLIC_INTERFACE
def test_g06_future_and_reopened_overdue_http(client, gap_record, monkeypatch):
    """Future work stays excluded; supervisor reopen restores deterministic overdue."""
    identifier, headers, supervisor = gap_record
    monkeypatch.setattr(reporting, "plant_today", lambda *_: date(2026, 1, 2))
    future = client.post(
        f"{PREFIX}/defects/{identifier}/actions",
        headers=headers,
        json=_action(due_date="2026-01-03"),
    )
    _wire(client, future, "/defects/{defect_id}/actions", "post", 201)
    complete = client.post(
        f"{PREFIX}/defects/{identifier}/actions",
        headers=headers,
        json=_action("Complete", due_date="2026-01-01", completion_notes="Done"),
    )
    _wire(client, complete, "/defects/{defect_id}/actions", "post", 201)
    page = _wire(
        client,
        client.get(PREFIX + "/overdue-actions", headers=headers),
        "/overdue-actions",
    )
    assert page["items"] == []
    reopened = client.post(
        f"{PREFIX}/actions/{complete.json()['id']}/transitions",
        headers={**supervisor, "If-Match": complete.headers["etag"]},
        json={"target_status": "In Progress", "reopen_reason": "More work"},
    )
    _wire(client, reopened, "/actions/{action_id}/transitions", "post")
    page = _wire(
        client,
        client.get(PREFIX + "/overdue-actions", headers=headers),
        "/overdue-actions",
    )
    assert page["evaluated_on"] == "2026-01-02" and page["plant_zone"] == "Etc/UTC"
    assert len(page["items"]) == 1
    row = page["items"][0]
    assert row["action_id"] == complete.json()["id"]
    assert row["defect_id"] == identifier and row["days_overdue"] == 1
    assert row["status"] == "In Progress"
    me = client.get(PREFIX + "/me", headers=headers).json()
    assert row["owner_name"] == me["display_name"]


# PUBLIC_INTERFACE
def test_g07_two_record_pdf_isolation(client, auth, capture_payload):
    """Each PDF contains its own record/cause/action/notes and none of the other's."""
    headers = auth()
    records = []
    for marker in ("ONLYALPHA", "ONLYBRAVO"):
        result = _capture(client, headers, {**capture_payload, "part_number": marker})
        identifier = _wire(client, result, "/defects", "post", 201)["id"]
        cause = client.post(
            f"{PREFIX}/defects/{identifier}/causes",
            headers=headers,
            json={"text": marker + "CAUSE"},
        )
        _wire(client, cause, "/defects/{defect_id}/causes", "post", 201)
        action = client.post(
            f"{PREFIX}/defects/{identifier}/actions",
            headers=headers,
            json=_action(
                "Complete",
                description=marker + "WORK",
                completion_notes=marker + "NOTES",
            ),
        )
        _wire(client, action, "/defects/{defect_id}/actions", "post", 201)
        records.append((identifier, marker, cause.json()["id"], action.json()["id"]))
    for identifier, marker, cause_id, action_id in records:
        result = client.get(f"{PREFIX}/defects/{identifier}/audit.pdf", headers=headers)
        content = _pdf_text(_wire(client, result, "/defects/{defect_id}/audit.pdf"))
        for value in (identifier, marker, cause_id, action_id):
            assert value.encode() in content
        for other_id, other_marker, other_cause, other_action in records:
            if other_id != identifier:
                for value in (other_id, other_marker, other_cause, other_action):
                    assert value.encode() not in content


@pytest.mark.parametrize("mode", ["partial", "inactive", "revoked"])
# PUBLIC_INTERFACE
def test_g08_export_delivery_failure_http(
    client, gap_record, database, monkeypatch, mode
):
    """Incomplete output or final identity/grant loss cannot escape as PDF success."""
    identifier, headers, _ = gap_record
    original = evidence.PdfRenderer.render_complete

    def render(renderer, snapshot):
        if mode == "partial":
            return b"%PDF-private-fault-marker"
        output = original(renderer, snapshot)
        with database[0].begin() as connection:
            if mode == "inactive":
                connection.execute(
                    update(User)
                    .where(User.ref == "sample-engineer")
                    .values(active=False)
                )
            else:
                connection.execute(
                    delete(Permission).where(
                        Permission.user_ref == "sample-engineer",
                        Permission.operation == "defect.export",
                    )
                )
        return output

    monkeypatch.setattr(evidence.PdfRenderer, "render_complete", render)
    result = client.get(f"{PREFIX}/defects/{identifier}/audit.pdf", headers=headers)
    code = {
        "partial": "export_failed",
        "inactive": "inactive_user",
        "revoked": "forbidden",
    }[mode]
    _wire(
        client,
        result,
        "/defects/{defect_id}/audit.pdf",
        status=500 if mode == "partial" else 403,
        code=code,
    )


@pytest.mark.parametrize("stage", ["principal", "snapshot", "final"])
# PUBLIC_INTERFACE
def test_g09_persistence_read_failures(
    client, gap_record, database, monkeypatch, stage
):
    """Principal, snapshot and final-authority SQL failures map safely to HTTP503."""
    identifier, headers, _ = gap_record

    def fail(*_):
        raise SQLAlchemyError("private-fault-marker SELECT protected")

    if stage == "principal":
        event.listen(database[1], "before_cursor_execute", fail)
    elif stage == "snapshot":
        monkeypatch.setattr(evidence, "load_snapshot", fail)
    else:
        original = evidence.PdfRenderer.render_complete

        def render(renderer, snapshot):
            output = original(renderer, snapshot)
            monkeypatch.setattr(evidence, "_authorize", fail)
            return output

        monkeypatch.setattr(evidence.PdfRenderer, "render_complete", render)
    try:
        path = "/me" if stage == "principal" else f"/defects/{identifier}/audit.pdf"
        template = "/me" if stage == "principal" else "/defects/{defect_id}/audit.pdf"
        result = client.get(PREFIX + path, headers=headers)
        _wire(client, result, template, status=503, code="persistence_unavailable")
    finally:
        if stage == "principal":
            event.remove(database[1], "before_cursor_execute", fail)


@pytest.mark.parametrize(
    "command", ["capture", "cause", "defect", "action", "action-transition", "retire"]
)
# PUBLIC_INTERFACE
def test_g09_post_flush_http_rollback(
    client, gap_record, database, capture_payload, command
):
    """Injected SQL faults after real flush preserve all command persistence."""
    identifier, headers, _ = gap_record
    path, template, kwargs = (
        f"/defects/{identifier}/causes",
        "/defects/{defect_id}/causes",
        {"json": {"text": "New cause"}},
    )
    if command == "capture":
        path = template = "/defects"
        kwargs = {
            "files": {
                "capture": (None, json.dumps(capture_payload), "application/json")
            }
        }
    elif command == "defect":
        saved = client.post(PREFIX + path, headers=headers, json={"text": "Saved"})
        _wire(client, saved, template, "post", 201)
        path, template = (
            f"/defects/{identifier}/transitions",
            "/defects/{defect_id}/transitions",
        )
        kwargs = {"json": {"target_status": "Under Investigation"}}
        headers = {**headers, "If-Match": saved.headers["etag"]}
    elif command in {"action", "action-transition"}:
        path, template = (
            f"/defects/{identifier}/actions",
            "/defects/{defect_id}/actions",
        )
        kwargs = {"json": _action()}
        if command == "action-transition":
            created = client.post(PREFIX + path, headers=headers, **kwargs)
            _wire(client, created, template, "post", 201)
            path = f"/actions/{created.json()['id']}/transitions"
            template = "/actions/{action_id}/transitions"
            headers = {**headers, "If-Match": created.headers["etag"]}
            kwargs = {"json": {"target_status": "Complete", "completion_notes": "Done"}}
    elif command == "retire":
        _grant(database)
        path = f"/defect-types/{capture_payload['defect_type_id']}/retire"
        template = "/defect-types/{type_id}/retire"
        headers = {**headers, "If-Match": '"1"'}
        kwargs = {"json": {}}
    before = _counts(database, identifier)
    with database[2]() as session:
        total = session.scalar(select(func.count()).select_from(Defect))

    def fail(*_):
        raise SQLAlchemyError("private-fault-marker")

    event.listen(database[2].class_, "after_flush_postexec", fail)
    try:
        result = client.post(PREFIX + path, headers=headers, **kwargs)
        _wire(client, result, template, "post", 503, "persistence_unavailable")
    finally:
        event.remove(database[2].class_, "after_flush_postexec", fail)
    assert _counts(database, identifier) == before
    with database[2]() as session:
        assert session.scalar(select(func.count()).select_from(Defect)) == total
        row = session.get(DefectType, UUID(capture_payload["defect_type_id"]))
        assert not row.retired and row.revision == 1


# PUBLIC_INTERFACE
def test_g09_policy_and_calendar_http(client, gap_record):
    """Missing runtime policy/calendar fail closed at actual HTTP boundaries."""
    identifier, headers, _ = gap_record
    settings = client.app.state.settings
    client.app.state.settings = replace(settings, demo=False)
    result = client.get(
        PREFIX + "/assignable-users", headers=headers, params={"defect_id": identifier}
    )
    _wire(client, result, "/assignable-users", status=503, code="policy_unavailable")
    result = client.post(
        f"{PREFIX}/defects/{identifier}/actions", headers=headers, json=_action()
    )
    _wire(
        client,
        result,
        "/defects/{defect_id}/actions",
        "post",
        503,
        "policy_unavailable",
    )
    client.app.state.settings = replace(settings, plant_zone="invalid/zone")
    result = client.get(PREFIX + "/overdue-actions", headers=headers)
    _wire(client, result, "/overdue-actions", status=503, code="calendar_unavailable")


# PUBLIC_INTERFACE
def test_g09_unexpected_failure_http(database, auth, monkeypatch):
    """Generic errors are internal_failure500, not invented persistence503."""
    headers = auth()

    def fail(*_):
        raise RuntimeError("private-fault-marker")

    with TestClient(
        create_app(database[4], database[2]), raise_server_exceptions=False
    ) as transport:
        monkeypatch.setattr("qualitytrack.main.load_principal", fail)
        result = transport.get(PREFIX + "/me", headers=headers)
        _wire(transport, result, "/me", status=500, code="internal_failure")


@pytest.mark.parametrize(
    "kind,keys",
    [
        (
            "causes",
            [
                None,
                {},
                [],
                ["bad", "bad"],
                ["2026-01-01T00:00:00", str(uuid4())],
                [1, str(uuid4())],
                ["2026-01-01T00:00:00+00:00", 1],
                ["2026-01-01T00:00:00+00:00", "bad"],
            ],
        ),
        ("actions", [None, {}, [], ["bad"], [1], [str(uuid4()), "extra"]]),
        ("history", [None, {}, [], [True], [0], ["1"], [1, 2]]),
        ("action-history", [None, {}, [], [True], [-1], ["1"], [1, 2]]),
    ],
)
# PUBLIC_INTERFACE
def test_g10_signed_malformed_child_payloads(client, gap_record, database, kind, keys):
    """QA-B3-001: signed malformed positions must be HTTP400, never HTTP500."""
    identifier, headers, _ = gap_record
    if kind == "action-history":
        created = client.post(
            f"{PREFIX}/defects/{identifier}/actions", headers=headers, json=_action()
        )
        identifier = _wire(
            client, created, "/defects/{defect_id}/actions", "post", 201
        )["id"]
        path = f"/actions/{identifier}/history"
        template = "/actions/{action_id}/history"
    else:
        path = f"/defects/{identifier}/{kind}"
        template = "/defects/{defect_id}/" + kind
    signing_key = hmac.new(
        database[4].secret.encode(), b"qualitytrack:children:v1", hashlib.sha256
    ).digest()
    bound = {
        "caller": "sample-engineer",
        "scope": "plant",
        "context": f"{kind}:{identifier}",
    }
    # Observe the real HTTP error response rather than re-raising application
    # exceptions. Do not xfail: this must become green only after source repair.
    with TestClient(
        create_app(database[4], database[2]), raise_server_exceptions=False
    ) as transport:
        for payload in [bound, *({**bound, "key": key} for key in keys)]:
            cursor = jwt.encode(payload, signing_key, algorithm="HS256")
            result = transport.get(
                PREFIX + path, headers=headers, params={"cursor": cursor}
            )
            _wire(transport, result, template, status=400, code="invalid_cursor")
            assert cursor not in result.text


@pytest.mark.parametrize("kind", ["defects", "overdue"])
@pytest.mark.parametrize("position", [1, None, True, {}, [], "bad"])
# PUBLIC_INTERFACE
def test_signed_malformed_list_uuid_positions(client, auth, database, kind, position):
    """QA-B3-001: other list UUID positions reject malformed signed values safely."""
    headers = auth()
    settings = database[4]
    if kind == "defects":
        domain = b"qualitytrack:defect-cursor:v1"
        payload = {
            "kind": "defects-v1",
            "caller": "sample-engineer",
            "scope": "plant",
            "zone": settings.plant_zone,
            "filters": {
                "status": None,
                "severity": None,
                "production_line_id": None,
                "shift_id": None,
                "defect_type_id": None,
                "part_number": None,
                "start_date": None,
                "end_date": None,
            },
            "order": "created_at DESC,id DESC",
            "at": "2026-01-01T00:00:00+00:00",
            "id": position,
        }
        path = "/defects"
    else:
        domain = b"qualitytrack:children:v1"
        payload = {
            "caller": "sample-engineer",
            "scope": "plant",
            "context": f"overdue-v1:{settings.plant_zone}:due_date,id",
            "key": ["2026-01-02", "2026-01-01", position],
        }
        path = "/overdue-actions"
    signing_key = hmac.new(settings.secret.encode(), domain, hashlib.sha256).digest()
    cursor = jwt.encode(payload, signing_key, algorithm="HS256")
    with TestClient(
        create_app(settings, database[2]), raise_server_exceptions=False
    ) as transport:
        result = transport.get(
            PREFIX + path, headers=headers, params={"cursor": cursor}
        )
        _wire(transport, result, path, status=400, code="invalid_cursor")
        assert cursor not in result.text


# PUBLIC_INTERFACE
def test_g01_remaining_identity_lookup_wire_assertions(client, auth, database):
    """Extend existing E01-E07 cases only with missing exact wire assertions."""
    password = database[3]["sample-engineer"]
    result = client.post(
        PREFIX + "/auth/login",
        json={"username": "sample-engineer", "password": password},
    )
    token = _wire(client, result, "/auth/login", "post")
    assert token["access_token"] and token["expires_in"] == 3600
    assert password not in result.text
    headers = auth()
    for path in ("/me", "/production-lines", "/shifts", "/defect-types", "/defects"):
        _wire(client, client.get(PREFIX + path, headers=headers), path)
        result = client.get(PREFIX + path)
        _wire(client, result, path, status=401, code="invalid_token")
    for username, status, code in (
        ("missing", 401, "invalid_credentials"),
        (" ", 422, "validation_failed"),
    ):
        result = client.post(
            PREFIX + "/auth/login", json={"username": username, "password": password}
        )
        _wire(client, result, "/auth/login", "post", status, code)
        assert password not in result.text
    for query, status, code in (
        ({"status": "bad"}, 422, "invalid_filters"),
        ({"cursor": "bad"}, 400, "invalid_cursor"),
    ):
        result = client.get(PREFIX + "/defects", headers=headers, params=query)
        _wire(client, result, "/defects", status=status, code=code)


# PUBLIC_INTERFACE
def test_g01_remaining_success_wire_assertions(
    client, gap_record, database, capture_payload
):
    """Fill schema/header assertions for remaining success operations E08-E20."""
    identifier, headers, _ = gap_record
    _wire(
        client,
        client.get(f"{PREFIX}/defects/{identifier}", headers=headers),
        "/defects/{defect_id}",
    )
    cause = client.post(
        f"{PREFIX}/defects/{identifier}/causes", headers=headers, json={"text": "Saved"}
    )
    _wire(client, cause, "/defects/{defect_id}/causes", "post", 201)
    transition = client.post(
        f"{PREFIX}/defects/{identifier}/transitions",
        headers={**headers, "If-Match": cause.headers["etag"]},
        json={"target_status": "Under Investigation"},
    )
    _wire(client, transition, "/defects/{defect_id}/transitions", "post")
    action = client.post(
        f"{PREFIX}/defects/{identifier}/actions", headers=headers, json=_action()
    )
    action_id = _wire(client, action, "/defects/{defect_id}/actions", "post", 201)["id"]
    changed = client.post(
        f"{PREFIX}/actions/{action_id}/transitions",
        headers={**headers, "If-Match": action.headers["etag"]},
        json={"target_status": "Complete", "completion_notes": "Done"},
    )
    _wire(client, changed, "/actions/{action_id}/transitions", "post")
    for path, template, params in (
        (f"/defects/{identifier}/causes", "/defects/{defect_id}/causes", {}),
        (f"/defects/{identifier}/actions", "/defects/{defect_id}/actions", {}),
        (f"/defects/{identifier}/history", "/defects/{defect_id}/history", {}),
        (f"/actions/{action_id}/history", "/actions/{action_id}/history", {}),
        ("/assignable-users", "/assignable-users", {"defect_id": identifier}),
    ):
        _wire(
            client, client.get(PREFIX + path, headers=headers, params=params), template
        )
    _grant(database)
    retired = client.post(
        f"{PREFIX}/defect-types/{capture_payload['defect_type_id']}/retire",
        headers={**headers, "If-Match": '"1"'},
        json={},
    )
    _wire(client, retired, "/defect-types/{type_id}/retire", "post")
