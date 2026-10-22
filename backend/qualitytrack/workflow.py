"""Batch B services. Callers own commit/rollback; every write locks the parent."""

import hashlib
import hmac
import re
from datetime import datetime
from uuid import UUID

import jwt
from sqlalchemy import select, tuple_

from qualitytrack.errors import Failure
from qualitytrack.models import (
    ActionEvent,
    CorrectiveAction,
    Defect,
    DefectStatusEvent,
    RcaEntry,
    User,
)
from qualitytrack.security import load_principal, require

# Explicit LA-06 fixture bindings, not role/name-derived privileges.
_DEMO_OWNERS = ("sample-engineer", "sample-supervisor")
_DEMO_SUPERVISOR = "sample-supervisor"


def _parent(session, caller, identifier, operation, lock=False):
    require(caller, operation)
    query = select(Defect).where(Defect.id == identifier)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = session.scalar(query)
    if not row:
        raise Failure(404, "not_found", "Record was not found")
    fresh = load_principal(session, caller.ref)
    require(fresh, operation)
    return row, fresh


# PUBLIC_INTERFACE
def check_revision(header, revision):
    """Require exactly one strong quoted positive integer, then compare under lock."""
    if header is None:
        raise Failure(428, "precondition_required", "A revision is required")
    if not re.fullmatch(r'"[1-9][0-9]*"', header):
        raise Failure(400, "invalid_precondition", "Revision is malformed")
    # String comparison avoids unbounded integer parsing of hostile headers.
    if header[1:-1] != str(revision):
        raise Failure(412, "precondition_failed", "Record has changed")


# PUBLIC_INTERFACE
def cause_view(row, revision):
    """Project a cause with the current parent revision."""
    return dict(
        id=row.id,
        defect_id=row.defect_id,
        text=row.cause_text,
        recorded_by_ref=row.recorded_by_ref,
        recorded_at=row.recorded_at,
        revision=revision,
    )


# PUBLIC_INTERFACE
def action_view(row, revision):
    """Project current action data without replacing historical completion evidence."""
    return dict(
        id=row.id,
        defect_id=row.defect_id,
        description=row.description,
        owner_ref=row.owner_ref,
        due_date=row.due_date,
        status=row.status,
        revision=revision,
    )


# PUBLIC_INTERFACE
def add_cause(session, caller, defect_id, body):
    """Save a cause and advance parent revision without evaluating If-Match."""
    parent, caller = _parent(session, caller, defect_id, "cause.create", True)
    row = RcaEntry(
        defect_id=parent.id, cause_text=body.text, recorded_by_ref=caller.ref
    )
    session.add(row)
    parent.revision += 1
    session.flush()
    return cause_view(row, parent.revision)


# PUBLIC_INTERFACE
def transition_defect(session, caller, defect_id, body, header, demo_mode):
    """Check authority, token and saved gates; append successful history atomically."""
    target = body.target_status.value
    # Resolve without revealing state until some applicable explicit grant exists.
    if target == "Under Investigation":
        if not {"defect.investigate", "defect.reopen"} & caller.permissions:
            raise Failure(403, "forbidden", "Operation is not permitted")
        operation = (
            "defect.investigate"
            if "defect.investigate" in caller.permissions
            else "defect.reopen"
        )
    else:
        operation = "defect.close" if target == "Closed" else "defect.reopen"
    parent, caller = _parent(session, caller, defect_id, operation, True)
    operation = (
        "defect.reopen"
        if parent.status == "Closed"
        else "defect.close" if target == "Closed" else "defect.investigate"
    )
    require(caller, operation)
    if parent.status == "Closed":
        _supervisor(caller, demo_mode)
    check_revision(header, parent.revision)
    old = parent.status
    if (old, target) not in {
        ("Open", "Under Investigation"),
        ("Under Investigation", "Closed"),
        ("Closed", "Under Investigation"),
    }:
        raise Failure(409, "invalid_transition", "Transition is not permitted")
    if target == "Under Investigation":
        causes = session.scalars(
            select(RcaEntry.cause_text).where(RcaEntry.defect_id == parent.id)
        )
        if not any(text.strip() for text in causes):
            raise Failure(409, "cause_required", "A recorded cause is required")
    elif session.scalar(
        select(CorrectiveAction.id)
        .where(
            CorrectiveAction.defect_id == parent.id,
            CorrectiveAction.status != "Complete",
        )
        .limit(1)
    ):
        raise Failure(409, "actions_incomplete", "Associated work is incomplete")
    # Zero-action closure is deliberately permitted by the settled demo policy.
    parent.status = target
    parent.revision += 1
    session.add(
        DefectStatusEvent(
            defect_id=parent.id,
            old_status=old,
            new_status=target,
            actor_ref=caller.ref,
            aggregate_revision=parent.revision,
        )
    )
    session.flush()
    return parent


def _supervisor(caller, demo_mode):
    if not demo_mode:
        raise Failure(503, "policy_unavailable", "Authority policy is unavailable")
    if caller.ref != _DEMO_SUPERVISOR:
        raise Failure(403, "forbidden", "Operation is not permitted")


def _owner_authority(caller, owner_ref, operation, demo_mode):
    require(caller, operation)
    if caller.ref != owner_ref:
        _supervisor(caller, demo_mode)


def _evidence(target, notes, reason=None, reopening=False):
    if (target == "Complete") != (notes is not None):
        raise Failure(
            422, "completion_notes_required", "Completion evidence is invalid"
        )
    if reopening != (reason is not None):
        raise Failure(422, "reopening_reason_required", "Reopening evidence is invalid")


# PUBLIC_INTERFACE
def assignable_users(session, caller, defect_id, demo_mode):
    """Authorize parent context and return active explicit LA-06 eligible owners."""
    _parent(session, caller, defect_id, "action.assign")
    if not demo_mode:
        raise Failure(503, "policy_unavailable", "Eligibility policy is unavailable")
    return {
        "items": [
            {"ref": row.ref, "display_name": row.display_name}
            for row in session.scalars(
                select(User)
                .where(User.ref.in_(_DEMO_OWNERS), User.active.is_(True))
                .order_by(User.ref)
            )
        ],
        "next_cursor": None,
    }


# PUBLIC_INTERFACE
def add_action(session, caller, defect_id, body, demo_mode):
    """Reject Closed first, check eligibility/authority and append a creation event."""
    parent, caller = _parent(session, caller, defect_id, "action.assign", True)
    if parent.status == "Closed":
        raise Failure(409, "defect_closed", "Defect is closed")
    if not demo_mode:
        raise Failure(503, "policy_unavailable", "Eligibility policy is unavailable")
    owner = session.get(User, body.owner_ref, populate_existing=True)
    if body.owner_ref not in _DEMO_OWNERS or not owner or not owner.active:
        raise Failure(422, "invalid_owner", "Select an assignable owner")
    target = body.status.value
    _evidence(target, body.completion_notes)
    if target in {"Complete", "In Progress"}:
        _owner_authority(
            caller,
            body.owner_ref,
            "action.complete" if target == "Complete" else "action.progress",
            demo_mode,
        )
    row = CorrectiveAction(
        defect_id=parent.id,
        description=body.description,
        owner_ref=body.owner_ref,
        due_date=body.due_date,
        status=target,
    )
    session.add(row)
    session.flush()
    parent.revision += 1
    session.add(
        ActionEvent(
            action_id=row.id,
            old_status=None,
            new_status=target,
            actor_ref=caller.ref,
            aggregate_revision=parent.revision,
            completion_notes=body.completion_notes,
        )
    )
    session.flush()
    return action_view(row, parent.revision)


def _action_parent(session, caller, action_id, operation, lock=False):
    require(caller, operation)
    parent_id = session.scalar(
        select(CorrectiveAction.defect_id).where(CorrectiveAction.id == action_id)
    )
    if parent_id is None:
        raise Failure(404, "not_found", "Record was not found")
    parent, caller = _parent(session, caller, parent_id, operation, lock)
    row = session.get(CorrectiveAction, action_id, populate_existing=True)
    return parent, caller, row


# PUBLIC_INTERFACE
def transition_action(session, caller, action_id, body, header, demo_mode):
    """Lock parent, enforce owner/supervisor authority and preserve every cycle."""
    target = body.target_status.value
    candidates = (
        {"action.progress", "action.reopen"}
        if target == "In Progress"
        else {"action.complete"} if target == "Complete" else {"action.progress"}
    )
    permitted = sorted(candidates & caller.permissions)
    if not permitted:
        raise Failure(403, "forbidden", "Operation is not permitted")
    parent, caller, row = _action_parent(session, caller, action_id, permitted[0], True)
    old = row.status
    reopening = old == "Complete" and target == "In Progress"
    operation = (
        "action.reopen"
        if reopening
        else "action.complete" if target == "Complete" else "action.progress"
    )
    require(caller, operation)
    if reopening:
        _supervisor(caller, demo_mode)
    else:
        _owner_authority(caller, row.owner_ref, operation, demo_mode)
    check_revision(header, parent.revision)
    if (old, target) not in {
        ("Open", "In Progress"),
        ("Open", "Complete"),
        ("In Progress", "Complete"),
        ("Complete", "In Progress"),
    }:
        raise Failure(409, "invalid_transition", "Transition is not permitted")
    if reopening and parent.status == "Closed":
        raise Failure(503, "policy_unavailable", "Closed-parent policy is unavailable")
    _evidence(target, body.completion_notes, body.reopen_reason, reopening)
    row.status = target
    parent.revision += 1
    session.add(
        ActionEvent(
            action_id=row.id,
            old_status=old,
            new_status=target,
            actor_ref=caller.ref,
            aggregate_revision=parent.revision,
            completion_notes=body.completion_notes,
            reopen_reason=body.reopen_reason,
        )
    )
    session.flush()
    return action_view(row, parent.revision)


def _cursor(settings, caller, context, token=None, key=None):
    signing_key = hmac.new(
        settings.secret.encode(), b"qualitytrack:children:v1", hashlib.sha256
    ).digest()
    bound = {"caller": caller.ref, "scope": "plant", "context": context}
    if token is None:
        return jwt.encode({**bound, "key": key}, signing_key, algorithm="HS256")
    try:
        payload = jwt.decode(token, signing_key, algorithms=["HS256"])
        if any(payload.get(k) != v for k, v in bound.items()):
            raise ValueError
        return payload["key"]
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise Failure(400, "invalid_cursor", "Page continuation is invalid") from None


# PUBLIC_INTERFACE
def list_children(session, caller, settings, identifier, kind, cursor, limit):
    """Authorize every live child page; bind cursor to caller, resource and order."""
    if kind == "action-history":
        parent, caller, action = _action_parent(
            session, caller, identifier, "defect.read"
        )
        model, column, value = ActionEvent, ActionEvent.action_id, action.id
    else:
        parent, caller = _parent(session, caller, identifier, "defect.read")
        model = {
            "causes": RcaEntry,
            "actions": CorrectiveAction,
            "history": DefectStatusEvent,
        }[kind]
        column, value = model.defect_id, parent.id
    context = f"{kind}:{identifier}"
    query = select(model).where(column == value)
    if kind == "causes":
        order = (model.recorded_at, model.id)
    elif kind == "actions":
        order = (model.id,)
    else:
        order = (model.aggregate_revision,)
    if cursor:
        key = _cursor(settings, caller, context, token=cursor)
        try:
            if not isinstance(key, list):
                raise ValueError
            if kind == "causes":
                instant = datetime.fromisoformat(key[0])
                if instant.tzinfo is None or not isinstance(key[1], str):
                    raise ValueError
                values = (instant, UUID(key[1]))
            elif kind == "actions":
                if not isinstance(key[0], str):
                    raise ValueError
                values = (UUID(key[0]),)
            else:
                if len(key) != 1 or type(key[0]) is not int or key[0] < 1:
                    raise ValueError
                values = (key[0],)
            if len(key) != len(order):
                raise ValueError
        except (ValueError, TypeError, IndexError):
            raise Failure(
                400, "invalid_cursor", "Page continuation is invalid"
            ) from None
        query = query.where(tuple_(*order) > tuple_(*values))
    rows = list(session.scalars(query.order_by(*order).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit]
    items = []
    for row in rows:
        if kind == "causes":
            item = cause_view(row, parent.revision)
        elif kind == "actions":
            item = action_view(row, parent.revision)
        else:
            item = {
                name: getattr(row, name)
                for name in (
                    "id",
                    "old_status",
                    "new_status",
                    "actor_ref",
                    "occurred_at",
                    "aggregate_revision",
                )
            }
            if kind == "action-history":
                item.update(
                    action_id=row.action_id,
                    defect_id=parent.id,
                    completion_notes=row.completion_notes,
                    reopen_reason=row.reopen_reason,
                )
        items.append(item)
    next_cursor = None
    if more:
        last = rows[-1]
        key = (
            [last.recorded_at.isoformat(), str(last.id)]
            if kind == "causes"
            else [str(last.id)] if kind == "actions" else [last.aggregate_revision]
        )
        next_cursor = _cursor(settings, caller, context, key=key)
    return {"items": items, "next_cursor": next_cursor}
