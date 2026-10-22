"""Batch B real PostgreSQL commands, API contracts, rollback and locking."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, event, func, select, text, update

from qualitytrack import workflow as w
from qualitytrack.defects import capture_defect
from qualitytrack.errors import Failure
from qualitytrack.models import (
    ActionEvent,
    CorrectiveAction,
    Defect,
    DefectStatusEvent,
    Permission,
    RcaEntry,
    User,
)
from qualitytrack.schemas import Capture
from qualitytrack.security import load_principal
from qualitytrack.workflow_schemas import (
    ActionCreate,
    ActionTransition,
    CauseCreate,
    DefectTransition,
)


@pytest.fixture
def record(client, auth, capture_payload):
    """Create an isolated captured record with separately authenticated operators."""
    engineer = auth()
    supervisor = auth("sample-supervisor")
    result = client.post(
        "/api/v1/defects",
        headers=engineer,
        files={"capture": (None, json.dumps(capture_payload), "application/json")},
    )
    assert result.status_code == 201, result.text
    return result.json()["id"], engineer, supervisor


def _action(status="Open", **extra):
    return {
        "description": " Inspect clamp ",
        "owner_ref": "sample-engineer",
        "due_date": "2020-01-01",
        "status": status,
        **extra,
    }


def _transition(client, identifier, headers, target, revision):
    path = f"/api/v1/defects/{identifier}/transitions"
    if revision is not None:
        headers = {**headers, "If-Match": revision}
    return client.post(path, headers=headers, json={"target_status": target})


def _counts(database, identifier):
    with database[2]() as session:
        parent = session.get(Defect, UUID(identifier))
        actions = select(CorrectiveAction.id).where(
            CorrectiveAction.defect_id == parent.id
        )

        def count(model, predicate):
            return session.scalar(
                select(func.count()).select_from(model).where(predicate)
            )

        return (
            parent.status,
            parent.revision,
            count(RcaEntry, RcaEntry.defect_id == parent.id),
            count(CorrectiveAction, CorrectiveAction.defect_id == parent.id),
            count(DefectStatusEvent, DefectStatusEvent.defect_id == parent.id),
            count(ActionEvent, ActionEvent.action_id.in_(actions)),
        )


def _investigate(client, record):
    identifier, engineer, _ = record
    cause = client.post(
        f"/api/v1/defects/{identifier}/causes",
        headers=engineer,
        json={"text": " Preliminary clamp cause "},
    )
    assert cause.status_code == 201, cause.text
    result = _transition(
        client, identifier, engineer, "Under Investigation", cause.headers["etag"]
    )
    assert result.status_code == 200, result.text
    return result.headers["etag"]


# PUBLIC_INTERFACE
def test_cause_reads_and_additive_headers(client, record, database):
    """Cause creation ignores If-Match and records actor/time with atomic revision."""
    identifier, engineer, _ = record
    path = f"/api/v1/defects/{identifier}/causes"
    assert client.get(path, headers=engineer).json()["items"] == []
    for header in (None, "invalid", '"999"'):
        headers = engineer if header is None else {**engineer, "If-Match": header}
        result = client.post(path, headers=headers, json={"text": " preliminary "})
        assert result.status_code == 201, result.text
        assert result.json()["text"] == "preliminary"
        assert result.json()["recorded_by_ref"] == "sample-engineer"
        assert result.json()["recorded_at"].endswith("Z")
    page = client.get(path, headers=engineer).json()
    assert len(page["items"]) == 3
    assert all(row["revision"] == 4 for row in page["items"])
    assert _counts(database, identifier) == ("Open", 4, 3, 0, 0, 0)


@pytest.mark.parametrize(
    "header,status",
    [
        (None, 428),
        ('W/"1"', 400),
        ("*", 400),
        ('"1","2"', 400),
        ("1", 400),
        ('"0"', 400),
        ('"2"', 412),
        ('"1"', 409),
    ],
)
# PUBLIC_INTERFACE
def test_defect_preconditions_no_mutation(client, record, database, header, status):
    """Authorized missing/malformed/stale/current-no-cause outcomes remain distinct."""
    identifier, engineer, _ = record
    result = _transition(client, identifier, engineer, "Under Investigation", header)
    assert result.status_code == status, result.text
    assert _counts(database, identifier) == ("Open", 1, 0, 0, 0, 0)


# PUBLIC_INTERFACE
def test_defect_lifecycle_zero_action_close_reopen(client, record, database):
    """Zero-action closure and supervisor reopen retain three causal events."""
    identifier, engineer, supervisor = record
    revision = _investigate(client, record)
    closed = _transition(client, identifier, supervisor, "Closed", revision)
    assert closed.status_code == 200, closed.text
    denied = _transition(
        client, identifier, engineer, "Under Investigation", closed.headers["etag"]
    )
    assert denied.status_code == 403
    reopened = _transition(
        client, identifier, supervisor, "Under Investigation", closed.headers["etag"]
    )
    assert reopened.status_code == 200, reopened.text
    assert (
        _transition(
            client,
            identifier,
            supervisor,
            "Under Investigation",
            reopened.headers["etag"],
        ).status_code
        == 409
    )
    rows = client.get(f"/api/v1/defects/{identifier}/history", headers=engineer).json()[
        "items"
    ]
    assert [row["aggregate_revision"] for row in rows] == [3, 4, 5]
    assert [row["actor_ref"] for row in rows] == [
        "sample-engineer",
        "sample-supervisor",
        "sample-supervisor",
    ]
    assert _counts(database, identifier) == ("Under Investigation", 5, 1, 0, 3, 0)


@pytest.mark.parametrize("status", ["Open", "In Progress", "Complete"])
# PUBLIC_INTERFACE
def test_closed_action_creation_precedes_business_gates(
    client, record, database, status
):
    """Every initial status on Closed returns defect_closed before owner gates."""
    identifier, engineer, supervisor = record
    revision = _investigate(client, record)
    assert (
        _transition(client, identifier, supervisor, "Closed", revision).status_code
        == 200
    )
    before = _counts(database, identifier)
    result = client.post(
        f"/api/v1/defects/{identifier}/actions",
        headers=engineer,
        json=_action(status, owner_ref="not-eligible"),
    )
    assert result.status_code == 409 and result.json()["code"] == "defect_closed"
    assert _counts(database, identifier) == before


# PUBLIC_INTERFACE
def test_action_cycles_closure_and_closed_reopen_policy(client, record, database):
    """Retain every completion cycle and deny existing-action reopening on Closed."""
    identifier, engineer, supervisor = record
    revision = _investigate(client, record)
    created = client.post(
        f"/api/v1/defects/{identifier}/actions",
        headers={**engineer, "If-Match": "ignored"},
        json=_action("Complete", completion_notes="First completion"),
    )
    assert created.status_code == 201, created.text
    action_id = created.json()["id"]
    path = f"/api/v1/actions/{action_id}/transitions"
    assert (
        _transition(client, identifier, supervisor, "Closed", revision).status_code
        == 412
    )
    reopened = client.post(
        path,
        headers={**supervisor, "If-Match": created.headers["etag"]},
        json={"target_status": "In Progress", "reopen_reason": "Investigate again"},
    )
    assert reopened.status_code == 200, reopened.text
    assert (
        _transition(
            client, identifier, supervisor, "Closed", reopened.headers["etag"]
        ).status_code
        == 409
    )
    completed = client.post(
        path,
        headers={**engineer, "If-Match": reopened.headers["etag"]},
        json={"target_status": "Complete", "completion_notes": "Second completion"},
    )
    assert completed.status_code == 200, completed.text
    closed = _transition(
        client, identifier, supervisor, "Closed", completed.headers["etag"]
    )
    assert closed.status_code == 200, closed.text
    before = _counts(database, identifier)
    denied = client.post(
        path,
        headers={**supervisor, "If-Match": closed.headers["etag"]},
        json={"target_status": "In Progress", "reopen_reason": "More work"},
    )
    assert denied.status_code == 503
    assert _counts(database, identifier) == before
    history = client.get(
        f"/api/v1/actions/{action_id}/history", headers=engineer
    ).json()["items"]
    assert [row["aggregate_revision"] for row in history] == [4, 5, 6]
    assert [row["completion_notes"] for row in history] == [
        "First completion",
        None,
        "Second completion",
    ]
    assert [row["reopen_reason"] for row in history] == [
        None,
        "Investigate again",
        None,
    ]
    assert all(row["defect_id"] == identifier for row in history)
    assert "effectiveness" not in json.dumps(history).lower()


# PUBLIC_INTERFACE
def test_assignable_and_action_validation(client, record, database):
    """Active fixture eligibility and required action fields reject atomically."""
    identifier, engineer, _ = record
    owners = client.get(
        "/api/v1/assignable-users",
        headers=engineer,
        params={"defect_id": identifier},
    )
    assert owners.status_code == 200
    assert {row["ref"] for row in owners.json()["items"]} == {
        "sample-engineer",
        "sample-supervisor",
    }
    path = f"/api/v1/defects/{identifier}/actions"
    for body in (
        _action(owner_ref="sample-auditor"),
        _action("Complete"),
        _action(description=" "),
        _action(description="x" * 2001),
        _action(owner_ref="missing"),
        _action(due_date="invalid"),
        _action("Open", completion_notes="unexpected"),
    ):
        assert client.post(path, headers=engineer, json=body).status_code == 422
        assert _counts(database, identifier) == ("Open", 1, 0, 0, 0, 0)
    with database[0].begin() as connection:
        connection.execute(
            update(User).where(User.ref == "sample-engineer").values(active=False)
        )
    supervisor = record[2]
    owners = client.get(
        "/api/v1/assignable-users",
        headers=supervisor,
        params={"defect_id": identifier},
    )
    assert [row["ref"] for row in owners.json()["items"]] == ["sample-supervisor"]
    assert client.post(path, headers=supervisor, json=_action()).status_code == 422


@pytest.mark.parametrize("operation", ["action.complete", "action.progress"])
# PUBLIC_INTERFACE
def test_owner_needs_explicit_grant(client, record, database, operation):
    """Being the assigned owner does not authorize a missing operation grant."""
    identifier, engineer, _ = record
    created = client.post(
        f"/api/v1/defects/{identifier}/actions", headers=engineer, json=_action()
    )
    assert created.status_code == 201
    with database[0].begin() as connection:
        connection.execute(
            delete(Permission).where(
                Permission.user_ref == "sample-engineer",
                Permission.operation == operation,
            )
        )
    target = "Complete" if operation == "action.complete" else "In Progress"
    body = {"target_status": target}
    if target == "Complete":
        body["completion_notes"] = "Done"
    result = client.post(
        f"/api/v1/actions/{created.json()['id']}/transitions",
        headers={**engineer, "If-Match": created.headers["etag"]},
        json=body,
    )
    assert result.status_code == 403
    assert _counts(database, identifier) == ("Open", 2, 0, 1, 0, 1)


# PUBLIC_INTERFACE
def test_denials_precede_existence_and_preconditions(client, record, database):
    """Revoked callers cannot probe child state, existence or transition tokens."""
    identifier, engineer, _ = record
    created = client.post(
        f"/api/v1/defects/{identifier}/actions", headers=engineer, json=_action()
    )
    action_id = created.json()["id"]
    with database[0].begin() as connection:
        connection.execute(
            delete(Permission).where(Permission.user_ref == "sample-engineer")
        )
    for parent in (identifier, str(uuid4())):
        for collection in ("causes", "actions", "history"):
            assert (
                client.get(
                    f"/api/v1/defects/{parent}/{collection}", headers=engineer
                ).status_code
                == 403
            )
        assert (
            client.post(
                f"/api/v1/defects/{parent}/causes",
                headers=engineer,
                json={"text": "valid"},
            ).status_code
            == 403
        )
        assert (
            _transition(
                client, parent, engineer, "Under Investigation", None
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/defects/{parent}/actions",
                headers=engineer,
                json=_action(),
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/api/v1/assignable-users",
                headers=engineer,
                params={"defect_id": parent},
            ).status_code
            == 403
        )
    for action in (action_id, str(uuid4())):
        assert (
            client.get(
                f"/api/v1/actions/{action}/history", headers=engineer
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/actions/{action}/transitions",
                headers=engineer,
                json={"target_status": "Complete", "completion_notes": "Done"},
            ).status_code
            == 403
        )


@pytest.mark.parametrize("kind", ["causes", "actions", "history", "action-history"])
# PUBLIC_INTERFACE
def test_live_child_keysets(client, record, database, kind):
    """Reconcile own rows; reject cursor resource/caller replay and revoked access."""
    identifier, engineer, supervisor = record
    if kind in {"history", "action-history"}:
        revision = _investigate(client, record)
    if kind == "causes":
        for _ in range(3):
            assert (
                client.post(
                    f"/api/v1/defects/{identifier}/causes",
                    headers=engineer,
                    json={"text": "Cause"},
                ).status_code
                == 201
            )
    elif kind in {"actions", "action-history"}:
        for _ in range(3 if kind == "actions" else 1):
            created = client.post(
                f"/api/v1/defects/{identifier}/actions",
                headers=engineer,
                json=_action(),
            )
            assert created.status_code == 201
        if kind == "action-history":
            action_id = created.json()["id"]
            changed = client.post(
                f"/api/v1/actions/{action_id}/transitions",
                headers={**engineer, "If-Match": created.headers["etag"]},
                json={"target_status": "Complete", "completion_notes": "Done"},
            )
            assert changed.status_code == 200
            assert (
                client.post(
                    f"/api/v1/actions/{action_id}/transitions",
                    headers={**supervisor, "If-Match": changed.headers["etag"]},
                    json={"target_status": "In Progress", "reopen_reason": "More"},
                ).status_code
                == 200
            )
    else:
        closed = _transition(client, identifier, supervisor, "Closed", revision)
        assert closed.status_code == 200
        assert (
            _transition(
                client,
                identifier,
                supervisor,
                "Under Investigation",
                closed.headers["etag"],
            ).status_code
            == 200
        )
    path = (
        f"/api/v1/actions/{action_id}/history"
        if kind == "action-history"
        else f"/api/v1/defects/{identifier}/{kind}"
    )
    page = client.get(path, headers=engineer, params={"limit": 1}).json()
    cursor = page["next_cursor"]
    assert cursor
    assert (
        client.get(path, headers=supervisor, params={"cursor": cursor}).status_code
        == 400
    )
    assert (
        client.get(
            path,
            headers=engineer,
            params={"cursor": cursor[:-8] + "tampered"},
        ).status_code
        == 400
    )
    alternate = f"/api/v1/defects/{identifier}/" + (
        "actions" if kind != "actions" else "causes"
    )
    assert (
        client.get(alternate, headers=engineer, params={"cursor": cursor}).status_code
        == 400
    )
    found = []
    while True:
        found.extend(row["id"] for row in page["items"])
        if not page["next_cursor"]:
            break
        page = client.get(
            path,
            headers=engineer,
            params={"limit": 1, "cursor": page["next_cursor"]},
        ).json()
    assert len(found) == len(set(found)) == 3
    with database[0].begin() as connection:
        connection.execute(
            delete(Permission).where(
                Permission.user_ref == "sample-engineer",
                Permission.operation == "defect.read",
            )
        )
    assert (
        client.get(path, headers=engineer, params={"cursor": cursor}).status_code == 403
    )


@pytest.mark.parametrize("command", ["cause", "defect", "action", "action-transition"])
# PUBLIC_INTERFACE
def test_workflow_flush_failure_rolls_back(database, capture_payload, command):
    """Post-flush faults roll back state, revision and all command evidence."""
    sessions = database[2]
    with sessions() as session, session.begin():
        caller = load_principal(session, "sample-engineer")
        parent = capture_defect(session, caller, Capture(**capture_payload))
        identifier = parent.id
        if command == "defect":
            w.add_cause(session, caller, identifier, CauseCreate(text="Saved"))
        elif command == "action-transition":
            action = w.add_action(
                session, caller, identifier, ActionCreate(**_action()), True
            )
    before = _counts(database, str(identifier))
    with sessions() as session:
        caller = load_principal(session, "sample-engineer")
        session.rollback()

        def fail(*_):
            raise RuntimeError("Injected after flush")

        event.listen(session, "after_flush_postexec", fail)
        with pytest.raises(RuntimeError), session.begin():
            if command == "cause":
                w.add_cause(session, caller, identifier, CauseCreate(text="Another"))
            elif command == "defect":
                w.transition_defect(
                    session,
                    caller,
                    identifier,
                    DefectTransition(target_status="Under Investigation"),
                    f'"{before[1]}"',
                    True,
                )
            elif command == "action":
                w.add_action(
                    session, caller, identifier, ActionCreate(**_action()), True
                )
            else:
                w.transition_action(
                    session,
                    caller,
                    action["id"],
                    ActionTransition(target_status="Complete", completion_notes="Done"),
                    f'"{before[1]}"',
                    True,
                )
    assert _counts(database, str(identifier)) == before


def _wait_for_lock(admin):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        with admin.connect() as observer:
            waiting = observer.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                    "WHERE datname = current_database() AND wait_event_type = 'Lock' "
                    "AND pid <> pg_backend_pid())"
                )
            )
        if waiting:
            return True
        time.sleep(0.02)
    return False


@pytest.mark.parametrize("winner", ["close", "action", "cause", "revoke"])
# PUBLIC_INTERFACE
def test_parent_lock_serializes_competing_commands(database, capture_payload, winner):
    """Real lock waits enforce closure-first, additive-first and revocation rules."""
    admin, _, sessions, _, _ = database
    with sessions() as session, session.begin():
        caller = load_principal(session, "sample-engineer")
        identifier = capture_defect(session, caller, Capture(**capture_payload)).id
        w.add_cause(session, caller, identifier, CauseCreate(text="Saved"))
        supervisor = load_principal(session, "sample-supervisor")
        w.transition_defect(
            session,
            supervisor,
            identifier,
            DefectTransition(target_status="Under Investigation"),
            '"2"',
            True,
        )
    with sessions() as holding:
        transaction = holding.begin()
        parent = holding.scalar(
            select(Defect).where(Defect.id == identifier).with_for_update()
        )
        reviewed = parent.revision
        principal = load_principal(holding, "sample-supervisor")
        if winner == "close":
            w.transition_defect(
                holding,
                principal,
                identifier,
                DefectTransition(target_status="Closed"),
                f'"{reviewed}"',
                True,
            )
        elif winner == "action":
            w.add_action(
                holding, principal, identifier, ActionCreate(**_action()), True
            )
        elif winner == "cause":
            w.add_cause(holding, principal, identifier, CauseCreate(text="Another"))
        with ThreadPoolExecutor(max_workers=1) as executor:

            def worker():
                try:
                    with sessions() as session, session.begin():
                        session.execute(text("SET LOCAL lock_timeout = '5s'"))
                        caller = load_principal(session, "sample-supervisor")
                        if winner in {"close", "revoke"}:
                            w.add_action(
                                session,
                                caller,
                                identifier,
                                ActionCreate(**_action()),
                                True,
                            )
                        else:
                            w.transition_defect(
                                session,
                                caller,
                                identifier,
                                DefectTransition(target_status="Closed"),
                                f'"{reviewed}"',
                                True,
                            )
                    return 201
                except Failure as exc:
                    return exc.problem.status

            future = executor.submit(worker)
            waiting = _wait_for_lock(admin)
            if winner == "revoke":
                with admin.begin() as connection:
                    connection.execute(
                        delete(Permission).where(
                            Permission.user_ref == "sample-supervisor",
                            Permission.operation == "action.assign",
                        )
                    )
            transaction.commit()
            assert waiting, "Expected a real PostgreSQL parent-row lock wait"
            assert (
                future.result(timeout=6)
                == {
                    "close": 409,
                    "action": 412,
                    "cause": 412,
                    "revoke": 403,
                }[winner]
            )
    counts = _counts(database, str(identifier))
    assert counts[1] == (3 if winner == "revoke" else 4)
    if winner == "action":
        with sessions() as session, session.begin(), pytest.raises(Failure) as caught:
            w.transition_defect(
                session,
                load_principal(session, "sample-supervisor"),
                identifier,
                DefectTransition(target_status="Closed"),
                '"4"',
                True,
            )
        assert caught.value.problem.status == 409


# PUBLIC_INTERFACE
def test_concurrent_cause_writes_keep_all_revisions(database, capture_payload):
    """Concurrent causes serialize without losing rows or revision increments."""
    sessions = database[2]
    with sessions() as session, session.begin():
        identifier = capture_defect(
            session,
            load_principal(session, "sample-engineer"),
            Capture(**capture_payload),
        ).id

    def worker(index):
        with sessions() as session, session.begin():
            return w.add_cause(
                session,
                load_principal(session, "sample-engineer"),
                identifier,
                CauseCreate(text=f"Cause {index}"),
            )["revision"]

    with ThreadPoolExecutor(max_workers=4) as executor:
        revisions = list(executor.map(worker, range(4)))
    assert sorted(revisions) == [2, 3, 4, 5]
    assert _counts(database, str(identifier)) == ("Open", 5, 4, 0, 0, 0)


# PUBLIC_INTERFACE
def test_action_preconditions_and_duplicate_headers(client, record, database):
    """Action transitions use parent tokens and reject duplicate revision headers."""
    identifier, engineer, _ = record
    created = client.post(
        f"/api/v1/defects/{identifier}/actions",
        headers=engineer,
        json=_action(),
    )
    assert created.status_code == 201
    path = f"/api/v1/actions/{created.json()['id']}/transitions"
    body = {"target_status": "Complete", "completion_notes": "Done"}
    before = _counts(database, identifier)
    for header, status in ((None, 428), ('W/"2"', 400), ('"1"', 412), ('"0"', 400)):
        headers = engineer if header is None else {**engineer, "If-Match": header}
        result = client.post(path, headers=headers, json=body)
        assert result.status_code == status
        assert _counts(database, identifier) == before
    headers = [*engineer.items(), ("If-Match", '"2"'), ("If-Match", '"2"')]
    assert client.post(path, headers=headers, json=body).status_code == 400
    assert (
        client.post(
            f"/api/v1/defects/{identifier}/transitions",
            headers=headers,
            json={"target_status": "Under Investigation"},
        ).status_code
        == 400
    )
    assert _counts(database, identifier) == before


@pytest.mark.parametrize("winner", ["close", "reopen"])
# PUBLIC_INTERFACE
def test_closure_races_existing_action_reopen(database, capture_payload, winner):
    """Shared parent locking prevents Closed with concurrently reopened work."""
    admin, _, sessions, _, _ = database
    with sessions() as session, session.begin():
        engineer = load_principal(session, "sample-engineer")
        identifier = capture_defect(session, engineer, Capture(**capture_payload)).id
        w.add_cause(session, engineer, identifier, CauseCreate(text="Saved"))
        w.transition_defect(
            session,
            engineer,
            identifier,
            DefectTransition(target_status="Under Investigation"),
            '"2"',
            True,
        )
        action_id = w.add_action(
            session,
            engineer,
            identifier,
            ActionCreate(**_action("Complete", completion_notes="Done")),
            True,
        )["id"]
    with sessions() as holding:
        transaction = holding.begin()
        supervisor = load_principal(holding, "sample-supervisor")
        if winner == "close":
            w.transition_defect(
                holding,
                supervisor,
                identifier,
                DefectTransition(target_status="Closed"),
                '"4"',
                True,
            )
        else:
            w.transition_action(
                holding,
                supervisor,
                action_id,
                ActionTransition(target_status="In Progress", reopen_reason="More"),
                '"4"',
                True,
            )
        with ThreadPoolExecutor(max_workers=1) as executor:

            def worker():
                try:
                    with sessions() as session, session.begin():
                        session.execute(text("SET LOCAL lock_timeout = '5s'"))
                        caller = load_principal(session, "sample-supervisor")
                        if winner == "close":
                            w.transition_action(
                                session,
                                caller,
                                action_id,
                                ActionTransition(
                                    target_status="In Progress", reopen_reason="More"
                                ),
                                '"5"',
                                True,
                            )
                        else:
                            w.transition_defect(
                                session,
                                caller,
                                identifier,
                                DefectTransition(target_status="Closed"),
                                '"4"',
                                True,
                            )
                    return 200
                except Failure as exc:
                    return exc.problem.status

            future = executor.submit(worker)
            waiting = _wait_for_lock(admin)
            transaction.commit()
            assert waiting
            assert future.result(timeout=6) == (503 if winner == "close" else 412)
    assert _counts(database, str(identifier)) == (
        "Closed" if winner == "close" else "Under Investigation",
        5,
        1,
        1,
        2 if winner == "close" else 1,
        1 if winner == "close" else 2,
    )
