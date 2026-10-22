"""Database-free Batch B service, DTO and cursor regressions."""

import secrets
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from qualitytrack import workflow as w
from qualitytrack.config import Settings
from qualitytrack.errors import Failure
from qualitytrack.models import ActionEvent, DefectStatusEvent, RcaEntry
from qualitytrack.security import Principal
from qualitytrack.workflow_schemas import (
    ActionCreate,
    ActionTransition,
    CauseCreate,
    DefectTransition,
)


def _caller(*grants, ref="sample-engineer"):
    return Principal(ref, "Not a role", frozenset(grants))


def _parent(status="Open"):
    return SimpleNamespace(id=uuid4(), status=status, revision=7)


def _body(status="Open", **extra):
    return ActionCreate(
        description=" Inspect fixture ",
        owner_ref="sample-engineer",
        due_date="2026-01-01",
        status=status,
        **extra,
    )


def _bind(monkeypatch, parent, caller):
    mock = Mock(return_value=(parent, caller))
    monkeypatch.setattr(w, "_parent", mock)
    return mock


@pytest.mark.parametrize(
    "header,status",
    [
        (None, 428),
        ('W/"7"', 400),
        ("7", 400),
        ('"0"', 400),
        ('"07"', 400),
        ('"7","8"', 400),
        ("*", 400),
        ('"6"', 412),
        ('"8"', 412),
        ('"7"', 200),
        ('" 7"', 400),
        ('"-1"', 400),
    ],
)
# PUBLIC_INTERFACE
def test_revision_contract(header, status):
    """Distinguish missing, malformed, stale and current strong revision tokens."""
    if status == 200:
        w.check_revision(header, 7)
    else:
        with pytest.raises(Failure) as caught:
            w.check_revision(header, 7)
        assert caught.value.problem.status == status


@pytest.mark.parametrize("value", ["", " \n\t", "x" * 2001, None, 12])
# PUBLIC_INTERFACE
def test_cause_input_rejections(value):
    """Reject missing/blank/oversized or non-string saved causes."""
    with pytest.raises(ValidationError):
        CauseCreate(text=value)


@pytest.mark.parametrize("case", ["trim", "bound", "attribution", "revision", "lock"])
# PUBLIC_INTERFACE
def test_add_cause_contract(monkeypatch, case):
    """Saved causes are trimmed, attributed, revisioned and parent-locked."""
    session = Mock()
    parent, caller = _parent(), _caller("cause.create")
    gate = _bind(monkeypatch, parent, caller)
    body = CauseCreate(text="x" * 2000 if case == "bound" else " preliminary ")
    monkeypatch.setattr(w, "cause_view", lambda row, rev: (row, rev))
    row, revision = w.add_cause(session, caller, parent.id, body)
    assert isinstance(row, RcaEntry)
    assert row.cause_text == body.text
    assert row.recorded_by_ref == caller.ref
    assert revision == 8
    assert gate.call_args.args[-1] is True
    session.flush.assert_called_once()


@pytest.mark.parametrize(
    "old,target,causes,incomplete,expected",
    [
        ("Open", "Under Investigation", ["preliminary"], False, 200),
        ("Open", "Under Investigation", [], False, 409),
        ("Open", "Under Investigation", [" \t"], False, 409),
        ("Under Investigation", "Closed", [], True, 409),
        ("Under Investigation", "Closed", [], False, 200),
        ("Open", "Closed", ["cause"], False, 409),
        ("Closed", "Under Investigation", ["cause"], False, 200),
        ("Closed", "Closed", ["cause"], False, 409),
    ],
)
# PUBLIC_INTERFACE
def test_defect_transition_gates(
    monkeypatch, old, target, causes, incomplete, expected
):
    """Legal edges and persisted cause/all-complete gates govern event creation."""
    session = Mock()
    session.scalars.return_value = causes
    session.scalar.return_value = uuid4() if incomplete else None
    caller = _caller(
        "defect.investigate", "defect.close", "defect.reopen", ref="sample-supervisor"
    )
    parent = _parent(old)
    _bind(monkeypatch, parent, caller)
    body = DefectTransition(target_status=target)
    if expected == 200:
        assert (
            w.transition_defect(session, caller, parent.id, body, '"7"', True) is parent
        )
        event = session.add.call_args.args[0]
        assert isinstance(event, DefectStatusEvent)
        assert (event.old_status, event.new_status, event.aggregate_revision) == (
            old,
            target,
            8,
        )
        assert event.actor_ref == caller.ref
    else:
        with pytest.raises(Failure) as caught:
            w.transition_defect(session, caller, parent.id, body, '"7"', True)
        assert caught.value.problem.status == expected
        assert parent.revision == 7 and parent.status == old
        session.add.assert_not_called()


@pytest.mark.parametrize("case", ["denied", "empty", "active", "fixture", "projection"])
# PUBLIC_INTERFACE
def test_assignable_contract(monkeypatch, case):
    """Eligibility is explicit demo fixture plus active flag, never all active users."""
    caller = _caller("action.assign")
    session, parent = Mock(), _parent()
    gate = _bind(monkeypatch, parent, caller)
    if case == "denied":
        gate.side_effect = Failure(403, "forbidden", "Denied")
        with pytest.raises(Failure):
            w.assignable_users(session, caller, parent.id, True)
        session.scalars.assert_not_called()
        return
    session.scalars.return_value = (
        []
        if case == "empty"
        else [
            SimpleNamespace(
                ref="sample-engineer",
                display_name="Engineer",
                password_hash="excluded",
            )
        ]
    )
    result = w.assignable_users(session, caller, parent.id, True)
    query = session.scalars.call_args.args[0]
    assert "users.active IS true" in str(query)
    assert set(query.compile().params["ref_1"]) == {
        "sample-engineer",
        "sample-supervisor",
    }
    assert result == {
        "items": (
            []
            if case == "empty"
            else [{"ref": "sample-engineer", "display_name": "Engineer"}]
        ),
        "next_cursor": None,
    }


@pytest.mark.parametrize(
    "case",
    [
        "open",
        "progress",
        "complete",
        "closed",
        "owner",
        "inactive",
        "notes",
        "no_completion_grant",
        "not_demo",
    ],
)
# PUBLIC_INTERFACE
def test_action_entry_contract(monkeypatch, case):
    """Check Closed before eligibility and explicit entry authority."""
    session = Mock()
    session.get.return_value = SimpleNamespace(active=case != "inactive")
    caller = _caller(
        "action.assign",
        "action.progress",
        *([] if case == "no_completion_grant" else ["action.complete"]),
    )
    parent = _parent("Closed" if case == "closed" else "Open")
    _bind(monkeypatch, parent, caller)
    status = (
        "Complete"
        if case in {"complete", "notes", "no_completion_grant"}
        else "In Progress" if case == "progress" else "Open"
    )
    body = _body(
        status,
        **(
            {"completion_notes": "Saved evidence"}
            if status == "Complete" and case != "notes"
            else {}
        ),
    )
    if case == "owner":
        body.owner_ref = "sample-auditor"
    expected = {
        "closed": 409,
        "owner": 422,
        "inactive": 422,
        "notes": 422,
        "no_completion_grant": 403,
        "not_demo": 503,
    }.get(case)
    if expected:
        with pytest.raises(Failure) as caught:
            w.add_action(session, caller, parent.id, body, case != "not_demo")
        assert caught.value.problem.status == expected
        assert parent.revision == 7
        session.add.assert_not_called()
        if case == "closed":
            assert caught.value.problem.code == "defect_closed"
            session.get.assert_not_called()
    else:
        result = w.add_action(session, caller, parent.id, body, True)
        assert result["revision"] == 8 and result["status"] == status
        event = session.add.call_args.args[0]
        assert isinstance(event, ActionEvent)
        assert event.old_status is None and event.actor_ref == caller.ref
        assert event.completion_notes == body.completion_notes


@pytest.mark.parametrize(
    "old,target,extra,ref,expected",
    [
        ("Open", "In Progress", {}, "sample-engineer", 200),
        ("Open", "Complete", {"completion_notes": "done"}, "sample-engineer", 200),
        ("In Progress", "Complete", {}, "sample-engineer", 422),
        (
            "Complete",
            "In Progress",
            {"reopen_reason": "more"},
            "sample-supervisor",
            200,
        ),
        ("Complete", "In Progress", {}, "sample-supervisor", 422),
        (
            "Complete",
            "In Progress",
            {"reopen_reason": "more"},
            "sample-engineer",
            403,
        ),
        ("In Progress", "Open", {}, "sample-engineer", 409),
        ("Open", "Open", {}, "sample-engineer", 409),
        (
            "Open",
            "In Progress",
            {"completion_notes": "wrong"},
            "sample-engineer",
            422,
        ),
    ],
)
# PUBLIC_INTERFACE
def test_action_transition_contract(monkeypatch, old, target, extra, ref, expected):
    """Owner completion and supervisor reopening preserve conditional evidence."""
    session = Mock()
    parent = _parent()
    caller = _caller("action.progress", "action.complete", "action.reopen", ref=ref)
    row = SimpleNamespace(
        id=uuid4(),
        defect_id=parent.id,
        owner_ref="sample-engineer",
        status=old,
        description="Work",
        due_date=date(2026, 1, 1),
    )
    monkeypatch.setattr(w, "_action_parent", Mock(return_value=(parent, caller, row)))
    body = ActionTransition(target_status=target, **extra)
    if expected == 200:
        result = w.transition_action(session, caller, row.id, body, '"7"', True)
        assert result["revision"] == 8 and result["status"] == target
        event = session.add.call_args.args[0]
        assert (event.old_status, event.new_status) == (old, target)
        assert event.completion_notes == extra.get("completion_notes")
        assert event.reopen_reason == extra.get("reopen_reason")
    else:
        with pytest.raises(Failure) as caught:
            w.transition_action(session, caller, row.id, body, '"7"', True)
        assert caught.value.problem.status == expected
        assert row.status == old and parent.revision == 7
        session.add.assert_not_called()


@pytest.mark.parametrize("kind", ["causes", "actions", "history", "action-history"])
@pytest.mark.parametrize("case", ["denied", "empty", "ordered", "projection", "limit"])
# PUBLIC_INTERFACE
def test_child_reads_contract(monkeypatch, kind, case):
    """Every child feature authorizes, projects safely and uses stable ordering."""
    session = Mock()
    parent, caller = _parent(), _caller("defect.read")
    gate = _bind(monkeypatch, parent, caller)
    action = SimpleNamespace(id=uuid4())
    action_gate = Mock(return_value=(parent, caller, action))
    monkeypatch.setattr(w, "_action_parent", action_gate)
    if case == "denied":
        gate.side_effect = action_gate.side_effect = Failure(403, "forbidden", "Denied")
        with pytest.raises(Failure):
            w.list_children(session, caller, None, parent.id, kind, None, 5)
        session.scalars.assert_not_called()
        return
    row = SimpleNamespace(
        id=uuid4(),
        defect_id=parent.id,
        action_id=action.id,
        cause_text="Saved",
        recorded_by_ref=caller.ref,
        recorded_at=datetime.now(timezone.utc),
        description="Work",
        owner_ref=caller.ref,
        due_date=date(2026, 1, 1),
        status="Open",
        old_status="Open",
        new_status="In Progress",
        actor_ref=caller.ref,
        occurred_at=datetime.now(timezone.utc),
        aggregate_revision=6,
        completion_notes=None,
        reopen_reason=None,
        password_hash="excluded",
    )
    session.scalars.return_value = [] if case == "empty" else [row]
    result = w.list_children(session, caller, None, parent.id, kind, None, 5)
    query = session.scalars.call_args.args[0]
    assert "ORDER BY" in str(query)
    assert query.compile().params["param_1"] == 6
    if case == "empty":
        assert result == {"items": [], "next_cursor": None}
    else:
        assert len(result["items"]) == 1
        assert "password_hash" not in result["items"][0]
        assert result["next_cursor"] is None
        if kind in {"causes", "actions"}:
            assert result["items"][0]["revision"] == 7
        elif kind == "action-history":
            assert result["items"][0]["defect_id"] == parent.id


@pytest.mark.parametrize(
    "change", ["caller", "parent", "kind", "signature", "roundtrip"]
)
# PUBLIC_INTERFACE
def test_child_cursor_context(change):
    """Continuations bind exact caller/resource/order with a separated signing key."""
    settings = Settings("unused", secrets.token_urlsafe(48), "Etc/UTC", True)
    caller = _caller("defect.read")
    context = "history:" + str(uuid4())
    token = w._cursor(settings, caller, context, key=[7])
    if change == "roundtrip":
        assert w._cursor(settings, caller, context, token=token) == [7]
        return
    if change == "caller":
        caller = _caller("defect.read", ref="other")
    elif change == "parent":
        context = "history:" + str(uuid4())
    elif change == "kind":
        context = context.replace("history:", "actions:")
    else:
        token = token[:-8] + "tampered"
    with pytest.raises(Failure) as caught:
        w._cursor(settings, caller, context, token=token)
    assert caught.value.problem.status == 400


@pytest.mark.parametrize("header", [None, "malformed", '"6"', '"7"', '"8"'])
# PUBLIC_INTERFACE
def test_defect_reopen_authority_precedes_preconditions(monkeypatch, header):
    """A grant without supervisor authority cannot reveal any token/state outcome."""
    session = Mock()
    parent = _parent("Closed")
    caller = _caller("defect.reopen")
    _bind(monkeypatch, parent, caller)
    with pytest.raises(Failure) as caught:
        w.transition_defect(
            session,
            caller,
            parent.id,
            DefectTransition(target_status="Under Investigation"),
            header,
            True,
        )
    assert caught.value.problem.status == 403
    assert parent.status == "Closed" and parent.revision == 7
    session.add.assert_not_called()
