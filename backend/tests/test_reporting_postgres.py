"""Batch C PostgreSQL snapshots, authorization, rollback and lock races."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, event, select, text, update
from test_reporting_unit import _pdf_text
from test_workflow_postgres import _wait_for_lock

from qualitytrack import evidence as e
from qualitytrack import reporting as r
from qualitytrack.defects import capture_defect
from qualitytrack.errors import Failure
from qualitytrack.models import CorrectiveAction, Defect, DefectType, Permission, User
from qualitytrack.schemas import Capture
from qualitytrack.security import load_principal
from qualitytrack.workflow import add_action, add_cause, transition_defect
from qualitytrack.workflow_schemas import ActionCreate, CauseCreate, DefectTransition


@pytest.fixture
def captured(client, auth, capture_payload):
    headers = auth()
    response = client.post(
        "/api/v1/defects",
        headers=headers,
        files={"capture": (None, json.dumps(capture_payload), "application/json")},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"]), headers


def _grant(database):
    with database[0].begin() as connection:
        connection.execute(
            Permission.__table__.insert().values(
                user_ref="sample-engineer", operation="type.retire", scope="plant"
            )
        )


def _work(session, caller, identifier, due, status="Open"):
    return add_action(
        session,
        caller,
        identifier,
        ActionCreate(
            description="Inspect clamp",
            owner_ref="sample-engineer",
            due_date=due,
            status=status,
            completion_notes="Done" if status == "Complete" else None,
        ),
        True,
    )


# PUBLIC_INTERFACE
def test_overdue_pinned_date_and_owner(database, captured):
    """Midnight/DST pins the date; due today and Complete stay excluded."""
    identifier, _ = captured
    sessions = database[2]
    settings = replace(database[4], plant_zone="America/New_York")
    before = datetime(2026, 3, 9, 3, 59, tzinfo=timezone.utc)
    after = datetime(2026, 3, 9, 4, 1, tzinfo=timezone.utc)
    with sessions() as session, session.begin():
        caller = load_principal(session, "sample-engineer")
        first = _work(session, caller, identifier, date(2026, 3, 6))
        second = _work(session, caller, identifier, date(2026, 3, 7))
        _work(session, caller, identifier, date(2026, 3, 8))
        _work(session, caller, identifier, date(2026, 3, 1), "Complete")
    with sessions() as session, session.begin():
        page = r.overdue_actions(
            session,
            load_principal(session, "sample-engineer"),
            settings,
            limit=1,
            now=before,
        )
    assert page.evaluated_on == date(2026, 3, 8)
    assert page.items[0].action_id == first["id"]
    assert page.items[0].days_overdue == 2
    with database[0].begin() as connection:
        connection.execute(
            update(User)
            .where(User.ref == "sample-engineer")
            .values(display_name="New Name")
        )
    with sessions() as session, session.begin():
        page2 = r.overdue_actions(
            session,
            load_principal(session, "sample-engineer"),
            settings,
            page.next_cursor,
            now=after,
        )
    assert page2.evaluated_on == date(2026, 3, 8)
    assert [row.action_id for row in page2.items] == [second["id"]]
    assert page2.items[0].owner_name == "New Name"
    assert page2.items[0].days_overdue == 1


# PUBLIC_INTERFACE
def test_overdue_revocation_and_empty(client, database, captured):
    """Authorized empty is success, but revoked read scope is denied."""
    identifier, headers = captured
    path = "/api/v1/overdue-actions"
    assert client.get(path, headers=headers).json()["items"] == []
    with database[2]() as session, session.begin():
        caller = load_principal(session, "sample-engineer")
        for _ in range(2):
            _work(session, caller, identifier, date(2020, 1, 1))
    page = client.get(path, headers=headers, params={"limit": 1}).json()
    assert page["next_cursor"]
    with database[0].begin() as connection:
        connection.execute(
            delete(Permission).where(
                Permission.user_ref == "sample-engineer",
                Permission.operation == "defect.read",
            )
        )
    assert (
        client.get(
            path, headers=headers, params={"cursor": page["next_cursor"]}
        ).status_code
        == 403
    )


# PUBLIC_INTERFACE
def test_pdf_complete_evidence(client, database, captured):
    """All 55 causes, two actions and three transitions survive export."""
    identifier, headers = captured
    with database[2]() as session, session.begin():
        caller = load_principal(session, "sample-engineer")
        for index in range(55):
            add_cause(
                session,
                caller,
                identifier,
                CauseCreate(text=f"CAUSE{index} " + "text " * 100),
            )
        for _ in range(2):
            _work(session, caller, identifier, date(2020, 1, 1), "Complete")
        supervisor = load_principal(session, "sample-supervisor")
        for target, revision in (
            ("Under Investigation", 58),
            ("Closed", 59),
            ("Under Investigation", 60),
        ):
            transition_defect(
                session,
                supervisor,
                identifier,
                DefectTransition(target_status=target),
                f'"{revision}"',
                True,
            )
    result = client.get(f"/api/v1/defects/{identifier}/audit.pdf", headers=headers)
    assert result.status_code == 200, result.text
    assert result.headers["content-type"] == "application/pdf"
    assert result.headers["cache-control"] == "private, no-store"
    assert str(identifier) in result.headers["content-disposition"]
    content = _pdf_text(result.content)
    for index in range(55):
        assert f"CAUSE{index} ".encode() in content
    snapshot = e.load_snapshot(database[2], "sample-engineer", identifier, database[4])
    assert [section.count for section in snapshot.sections[1:]] == [55, 2, 2, 3]
    for section in snapshot.sections[1:]:
        for row in section.rows:
            assert row[0].split("\n")[0].encode() in content
    assert b"Etc/UTC" in content
    assert b"password" not in content


@pytest.mark.parametrize("missing", ["defect.read", "defect.export"])
# PUBLIC_INTERFACE
def test_export_requires_both_grants(client, database, captured, missing):
    """Either grant alone is insufficient before existence is disclosed."""
    identifier, headers = captured
    with database[0].begin() as connection:
        connection.execute(
            delete(Permission).where(
                Permission.user_ref == "sample-engineer",
                Permission.operation == missing,
            )
        )
    for target in (identifier, uuid4()):
        result = client.get(f"/api/v1/defects/{target}/audit.pdf", headers=headers)
        assert result.status_code == 403
        assert result.headers["content-type"] == "application/problem+json"


# PUBLIC_INTERFACE
def test_export_final_revocation(database, captured):
    """Revocation while rendering discards all already-rendered bytes."""
    identifier, _ = captured

    class RevokingRenderer:
        def render_complete(self, snapshot):
            output = e.PdfRenderer().render_complete(snapshot)
            with database[0].begin() as connection:
                connection.execute(
                    delete(Permission).where(
                        Permission.user_ref == "sample-engineer",
                        Permission.operation == "defect.export",
                    )
                )
            return output

    with pytest.raises(Failure) as caught:
        e.export_record(
            database[2],
            "sample-engineer",
            identifier,
            database[4],
            RevokingRenderer(),
        )
    assert caught.value.problem.status == 403


# PUBLIC_INTERFACE
def test_snapshot_concurrent_write(database, captured):
    """A commit between parent and child reads cannot mix revisions."""
    identifier, _ = captured
    triggered = []

    def write_during_read(conn, cursor, statement, parameters, context, executemany):
        if "FROM defect_photo" not in statement or triggered:
            return
        triggered.append(True)
        with database[2]() as session, session.begin():
            add_cause(
                session,
                load_principal(session, "sample-engineer"),
                identifier,
                CauseCreate(text="CONCURRENT"),
            )

    event.listen(database[1], "after_cursor_execute", write_during_read)
    try:
        snapshot = e.load_snapshot(
            database[2], "sample-engineer", identifier, database[4]
        )
    finally:
        event.remove(database[1], "after_cursor_execute", write_during_read)
    assert triggered and snapshot.sections[1].count == 0
    with database[2]() as session:
        assert session.get(Defect, identifier).revision == 2


# PUBLIC_INTERFACE
def test_render_off_transaction(client, database, captured, monkeypatch):
    """Renderer holds no snapshot transaction open."""
    identifier, headers = captured
    original = e.PdfRenderer.render_complete

    class ObservingRenderer:
        def render_complete(self, snapshot):
            with database[0].connect() as connection:
                assert (
                    connection.scalar(
                        text(
                            "SELECT count(*) FROM pg_stat_activity "
                            "WHERE datname=current_database() AND usename='qt_app' "
                            "AND state='idle in transaction'"
                        )
                    )
                    == 0
                )
            return original(self, snapshot)

    monkeypatch.setattr(
        e.PdfRenderer, "render_complete", ObservingRenderer.render_complete
    )
    result = client.get(f"/api/v1/defects/{identifier}/audit.pdf", headers=headers)
    assert result.status_code == 200
    assert result.content.startswith(b"%PDF")


@pytest.mark.parametrize(
    "header,status",
    [(None, 428), ('W/"1"', 400), ('"1","2"', 400), ('"2"', 412), ('"1"', 200)],
)
# PUBLIC_INTERFACE
def test_retirement_http(client, database, captured, capture_payload, header, status):
    """Type retirement has grant-first strong revision semantics."""
    _, headers = captured
    target = capture_payload["defect_type_id"]
    path = f"/api/v1/defect-types/{target}/retire"
    assert client.post(path, headers=headers, json={}).status_code == 403
    _grant(database)
    if header is not None:
        headers = {**headers, "If-Match": header}
    result = client.post(path, headers=headers, json={})
    assert result.status_code == status, result.text
    with database[2]() as session:
        row = session.get(DefectType, UUID(target))
        assert row.retired == (status == 200)
        assert row.revision == (2 if status == 200 else 1)
    if status == 200:
        assert result.headers["etag"] == '"2"'
        headers["If-Match"] = '"2"'
        assert client.post(path, headers=headers, json={}).status_code == 409


# PUBLIC_INTERFACE
def test_retirement_preserves_capture(client, database, captured, capture_payload):
    """No body extras/duplicate tokens; historical captured labels stay unchanged."""
    identifier, headers = captured
    _grant(database)
    path = f"/api/v1/defect-types/{capture_payload['defect_type_id']}/retire"
    good = {**headers, "If-Match": '"1"'}
    assert client.post(path, headers=good, json={"retired": True}).status_code == 422
    duplicates = [*headers.items(), ("If-Match", '"1"'), ("If-Match", '"1"')]
    assert client.post(path, headers=duplicates, json={}).status_code == 400
    before = client.get(f"/api/v1/defects/{identifier}", headers=headers).json()
    assert client.post(path, headers=good, json={}).status_code == 200
    assert client.get(f"/api/v1/defects/{identifier}", headers=headers).json() == before
    assert (
        client.post(
            "/api/v1/defects",
            headers=headers,
            files={"capture": (None, json.dumps(capture_payload), "application/json")},
        ).status_code
        == 409
    )


# PUBLIC_INTERFACE
def test_retirement_rollback(database, capture_payload):
    """Post-flush faults roll back retirement and revision together."""
    _grant(database)
    target = UUID(capture_payload["defect_type_id"])
    with database[2]() as session:

        def fail(*_):
            raise RuntimeError("injected")

        event.listen(session, "after_flush_postexec", fail)
        with pytest.raises(RuntimeError), session.begin():
            r.retire_type(
                session, load_principal(session, "sample-engineer"), target, '"1"'
            )
    with database[2]() as session:
        row = session.get(DefectType, target)
        assert not row.retired and row.revision == 1


@pytest.mark.parametrize("winner", ["retire", "capture", "revoke"])
# PUBLIC_INTERFACE
def test_retirement_capture_lock(database, capture_payload, winner):
    """Real type-row lock waits preserve ordering and refresh grants."""
    _grant(database)
    target, sessions = UUID(capture_payload["defect_type_id"]), database[2]
    with sessions() as holding:
        transaction = holding.begin()
        holding.scalar(
            select(DefectType).where(DefectType.id == target).with_for_update()
        )
        caller = load_principal(holding, "sample-engineer")
        if winner == "retire":
            r.retire_type(holding, caller, target, '"1"')
        elif winner == "capture":
            capture_defect(holding, caller, Capture(**capture_payload))
        with ThreadPoolExecutor(max_workers=1) as executor:

            def worker():
                try:
                    with sessions() as session, session.begin():
                        session.execute(text("SET LOCAL lock_timeout = '5s'"))
                        principal = load_principal(session, "sample-engineer")
                        if winner == "retire":
                            capture_defect(
                                session, principal, Capture(**capture_payload)
                            )
                        else:
                            r.retire_type(session, principal, target, '"1"')
                    return 200
                except Failure as exc:
                    return exc.problem.status

            future = executor.submit(worker)
            waiting = _wait_for_lock(database[0])
            if winner == "revoke":
                with database[0].begin() as connection:
                    connection.execute(
                        delete(Permission).where(
                            Permission.user_ref == "sample-engineer",
                            Permission.operation == "type.retire",
                        )
                    )
            transaction.commit()
            assert waiting
            assert (
                future.result(timeout=6)
                == {
                    "retire": 409,
                    "capture": 200,
                    "revoke": 403,
                }[winner]
            )


# PUBLIC_INTERFACE
def test_overdue_status_is_live(client, database, captured):
    """An action completed after page one is absent from its continuation."""
    identifier, headers = captured
    with database[2]() as session, session.begin():
        caller = load_principal(session, "sample-engineer")
        for _ in range(3):
            _work(session, caller, identifier, date(2020, 1, 1))
    path = "/api/v1/overdue-actions"
    page = client.get(path, headers=headers, params={"limit": 1}).json()
    with database[0].begin() as connection:
        connection.execute(
            update(CorrectiveAction)
            .where(CorrectiveAction.id != UUID(page["items"][0]["action_id"]))
            .values(status="Complete")
        )
    result = client.get(path, headers=headers, params={"cursor": page["next_cursor"]})
    assert result.status_code == 200
    assert result.json()["items"] == []


# PUBLIC_INTERFACE
def test_export_final_inactive(database, captured):
    """A user deactivated while rendering cannot receive completed bytes."""
    identifier, _ = captured

    class DeactivatingRenderer:
        def render_complete(self, snapshot):
            output = e.PdfRenderer().render_complete(snapshot)
            with database[0].begin() as connection:
                connection.execute(
                    update(User)
                    .where(User.ref == "sample-engineer")
                    .values(active=False)
                )
            return output

    with pytest.raises(Failure) as caught:
        e.export_record(
            database[2],
            "sample-engineer",
            identifier,
            database[4],
            DeactivatingRenderer(),
        )
    assert caught.value.problem.status == 403


# PUBLIC_INTERFACE
def test_pdf_render_failure_safe_http(client, captured, monkeypatch):
    """A renderer fault returns a safe Problem, never partial PDF or raw evidence."""
    identifier, headers = captured

    def fail(*_):
        raise RuntimeError("protected-evidence-marker")

    monkeypatch.setattr(e.PdfRenderer, "render_complete", fail)
    result = client.get(f"/api/v1/defects/{identifier}/audit.pdf", headers=headers)
    assert result.status_code == 500
    assert result.headers["content-type"] == "application/problem+json"
    assert result.headers["cache-control"] == "private, no-store"
    assert b"protected-evidence-marker" not in result.content
    assert not result.content.startswith(b"%PDF")
