"""Batch A deterministic unit checks without a database."""

import secrets
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from qualitytrack.config import Settings
from qualitytrack.defects import capture_defect, defect_view, get_defect
from qualitytrack.errors import Failure
from qualitytrack.models import Base
from qualitytrack.schemas import Capture, Filters, LoginRequest
from qualitytrack.security import (
    HASHER,
    Principal,
    decode_cursor,
    encode_cursor,
    issue_token,
    load_principal,
    require,
    verify_token,
)
from qualitytrack.seed import GRANTS, SeedDiscrepancy, seed_demo


@pytest.fixture
def settings():
    return Settings(
        "postgresql+psycopg://unused", secrets.token_urlsafe(48), "Etc/UTC", True
    )


@pytest.fixture
def caller():
    return Principal("test-unit", "Unit", frozenset({"defect.capture", "defect.read"}))


@pytest.fixture
def payload():
    return {
        "part_number": " SAMPLE-P100 ",
        "defect_type_id": str(uuid4()),
        "production_line_id": str(uuid4()),
        "shift_id": str(uuid4()),
        "quantity_affected": 3,
        "severity": "Major",
    }


@pytest.mark.parametrize("quantity", [0, -1, 1000001, 1.5, "3", True, None])
def test_capture_quantity_is_strict(payload, quantity):
    payload["quantity_affected"] = quantity
    with pytest.raises(ValidationError):
        Capture(**payload)


@pytest.mark.parametrize("severity", ["Critical", "Major", "Minor"])
def test_manual_severity_preserved(payload, severity):
    payload["severity"] = severity
    assert Capture(**payload).severity.value == severity


@pytest.mark.parametrize(
    "field,value",
    [
        ("part_number", "   "),
        ("part_number", "x" * 51),
        ("severity", "major"),
        ("severity", None),
        ("defect_type_id", "unknown"),
        ("created_by_ref", "forged"),
    ],
)
def test_capture_rejects_invalid_or_trusted_input(payload, field, value):
    payload[field] = value
    with pytest.raises(ValidationError):
        Capture(**payload)


def test_capture_trims_and_accepts_boundaries(payload):
    payload["quantity_affected"] = 1000000
    assert Capture(**payload).part_number == "SAMPLE-P100"


@pytest.mark.parametrize(
    "env,valid",
    [
        ({"QT_DEMO_MODE": "true"}, True),
        ({"QT_DEMO_MODE": "true", "PLANT_TIMEZONE": "America/New_York"}, True),
        ({"QT_DEMO_MODE": "false", "PLANT_TIMEZONE": "Europe/London"}, True),
        ({"QT_DEMO_MODE": "false"}, False),
        ({"QT_DEMO_MODE": "true", "PLANT_TIMEZONE": ""}, False),
        ({"QT_DEMO_MODE": "true", "PLANT_TIMEZONE": "Not/AZone"}, False),
    ],
)
def test_timezone_configuration(monkeypatch, settings, env, valid):
    monkeypatch.delenv("PLANT_TIMEZONE", raising=False)
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("JWT_SECRET_KEY", settings.secret)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    if valid:
        assert Settings.from_env().plant_zone == env.get("PLANT_TIMEZONE", "Etc/UTC")
    else:
        with pytest.raises(RuntimeError):
            Settings.from_env()


@pytest.mark.parametrize("field", ["DATABASE_URL", "JWT_SECRET_KEY"])
def test_missing_secure_config_fails(monkeypatch, field):
    monkeypatch.setenv("QT_DEMO_MODE", "true")
    monkeypatch.delenv(field, raising=False)
    with pytest.raises(RuntimeError):
        Settings.from_env()


def _user(password, active=True):
    return SimpleNamespace(
        ref="unit-ref", password_hash=HASHER.hash(password), active=active
    )


def test_valid_login_token_contract(settings):
    password = secrets.token_urlsafe()
    session = Mock()
    session.scalar.return_value = _user(password)
    token = issue_token(session, settings, "unit", password)
    assert verify_token(token, settings) == "unit-ref"
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] == 3600
    assert "permissions" not in claims and "password" not in claims


@pytest.mark.parametrize("kind", ["unknown", "wrong", "inactive", "bad_hash"])
def test_login_generic_denial(settings, kind):
    password = secrets.token_urlsafe()
    session = Mock()
    user = _user(password, active=kind != "inactive")
    if kind == "bad_hash":
        user.password_hash = "invalid"
    session.scalar.return_value = None if kind == "unknown" else user
    with pytest.raises(Failure) as caught:
        issue_token(
            session, settings, "unit", password if kind != "wrong" else password + "x"
        )
    assert caught.value.problem.status == 401
    assert caught.value.problem.code == "invalid_credentials"


@pytest.mark.parametrize(
    "kind", ["expired", "issuer", "audience", "algorithm", "tampered"]
)
def test_token_validation(settings, kind):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "unit-ref",
        "iss": "qualitytrack-local",
        "aud": "qualitytrack-api",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    if kind == "expired":
        claims["exp"] = now - timedelta(seconds=1)
    if kind == "issuer":
        claims["iss"] = "other"
    if kind == "audience":
        claims["aud"] = "other"
    token = jwt.encode(
        claims,
        settings.secret if kind != "tampered" else secrets.token_urlsafe(48),
        algorithm="HS384" if kind == "algorithm" else "HS256",
    )
    with pytest.raises(Failure) as caught:
        verify_token(token, settings)
    assert caught.value.problem.code == "invalid_token"


def test_missing_claims_rejected(settings):
    token = jwt.encode({"sub": "unit"}, settings.secret, algorithm="HS256")
    with pytest.raises(Failure):
        verify_token(token, settings)


def test_principal_reloads_grants():
    session = Mock()
    session.get.return_value = SimpleNamespace(
        ref="ref", display_name="Name", active=True
    )
    session.scalars.return_value = ["defect.read"]
    principal = load_principal(session, "ref")
    assert principal.permissions == frozenset({"defect.read"})
    with pytest.raises(Failure):
        require(principal, "defect.capture")


@pytest.mark.parametrize("user", [None, SimpleNamespace(active=False)])
def test_inactive_or_unmapped_caller_denied(user):
    session = Mock()
    session.get.return_value = user
    with pytest.raises(Failure) as caught:
        load_principal(session, "unknown")
    assert caught.value.problem.status == 403


def test_ownership_or_name_is_not_grant():
    principal = Principal("sample-supervisor", "Supervisor", frozenset())
    with pytest.raises(Failure):
        require(principal, "defect.read")


@pytest.mark.parametrize(
    "filters",
    [
        {"start_date": "2026-01-01"},
        {"end_date": "2026-01-01"},
        {"start_date": "2026-02-01", "end_date": "2026-01-01"},
        {"status": "Complete"},
        {"severity": "critical"},
        {"production_line_id": "bad"},
    ],
)
def test_filter_validation(filters):
    with pytest.raises(ValidationError):
        Filters(**filters)


def test_cursor_roundtrip(settings, caller):
    instant, identifier = datetime.now(timezone.utc), uuid4()
    filters = Filters(part_number="A")
    token = encode_cursor(settings, caller, filters, instant, identifier)
    assert decode_cursor(settings, caller, filters, token) == (instant, identifier)


@pytest.mark.parametrize(
    "change", ["caller", "filters", "zone", "signature", "garbage"]
)
def test_cursor_bound_context(settings, caller, change):
    filters = Filters(part_number="A")
    token = encode_cursor(
        settings, caller, filters, datetime.now(timezone.utc), uuid4()
    )
    if change == "caller":
        caller = Principal("other", "Other", caller.permissions)
    if change == "filters":
        filters = Filters(part_number="B")
    if change == "zone":
        settings = Settings(
            settings.database_url, settings.secret, "Europe/London", True
        )
    if change == "signature":
        token = token[:-8] + "tampered"
    if change == "garbage":
        token = "not-a-cursor"
    with pytest.raises(Failure) as caught:
        decode_cursor(settings, caller, filters, token)
    assert caught.value.problem.status == 400


@pytest.mark.parametrize("index", [0, 1, 2])
def test_capture_missing_or_retired_lookup_has_no_write(payload, caller, index):
    session = Mock()
    lookups = [SimpleNamespace(retired=False) for _ in range(3)]
    lookups[index] = SimpleNamespace(retired=True)
    session.scalar.side_effect = lookups
    with pytest.raises(Failure) as caught:
        capture_defect(session, caller, Capture(**payload))
    assert caught.value.problem.status == 409
    session.add.assert_not_called()


def test_capture_denies_before_lookup(payload):
    session = Mock()
    with pytest.raises(Failure):
        capture_defect(
            session, Principal("ref", "Name", frozenset()), Capture(**payload)
        )
    session.scalar.assert_not_called()


def test_record_denies_before_existence_lookup():
    session = Mock()
    with pytest.raises(Failure):
        get_defect(session, Principal("ref", "Name", frozenset()), uuid4())
    session.get.assert_not_called()


def test_record_missing_is_safe(caller):
    session = Mock()
    session.get.return_value = None
    with pytest.raises(Failure) as caught:
        get_defect(session, caller, uuid4())
    assert caught.value.problem.status == 404


def test_projection_uses_captured_labels():
    row = SimpleNamespace(
        id=uuid4(),
        part_number="A",
        type_id=uuid4(),
        type_code_at_capture="T",
        type_label_at_capture="Original Type",
        quantity_affected=1,
        production_line_id=uuid4(),
        production_line_code_at_capture="L",
        production_line_label_at_capture="Original Line",
        shift_id=uuid4(),
        shift_code_at_capture="S",
        shift_label_at_capture="Original Shift",
        severity="Minor",
        status="Open",
        created_by_ref="ref",
        created_at=datetime.now(timezone.utc),
        revision=1,
    )
    result = defect_view(row)
    assert result.defect_type.label_at_capture == "Original Type"
    assert result.production_line.label_at_capture == "Original Line"
    assert result.shift.label_at_capture == "Original Shift"
    assert result.has_photo is False


def test_full_erd_contains_all_tables():
    assert set(Base.metadata.tables) == {
        "users",
        "permissions",
        "production_line",
        "shift",
        "defect_type",
        "defect",
        "defect_photo",
        "rca_entry",
        "corrective_action",
        "defect_status_event",
        "action_event",
    }


def test_foreign_keys_never_cascade_delete():
    assert all(
        key.ondelete == "RESTRICT"
        for table in Base.metadata.tables.values()
        for key in table.foreign_keys
    )


def test_action_status_has_no_default():
    column = Base.metadata.tables["corrective_action"].c.status
    assert column.default is None and column.server_default is None


def test_event_evidence_checks_exist():
    constraints = Base.metadata.tables["action_event"].constraints
    names = {constraint.name for constraint in constraints}
    assert {"ck_action_completion_notes", "ck_action_reopen_reason"} <= names


def test_permission_vocabulary_is_checked():
    names = {c.name for c in Base.metadata.tables["permissions"].constraints}
    assert {"ck_permission_operation", "ck_permission_scope"} <= names


def test_seed_refuses_non_demo_without_querying():
    session = Mock()
    with pytest.raises(SeedDiscrepancy):
        seed_demo(session, False, {})
    session.execute.assert_not_called()


def test_seed_missing_passwords_has_no_inserts():
    session = Mock()
    session.scalars.return_value = []
    session.scalar.return_value = None
    with pytest.raises(SeedDiscrepancy):
        seed_demo(session, True, {})
    session.add.assert_not_called()


def test_seed_partial_dataset_refused():
    session = Mock()
    session.scalars.return_value = []
    session.scalar.side_effect = [SimpleNamespace(), None, None, None, None, None]
    with pytest.raises(SeedDiscrepancy):
        seed_demo(session, True, {})
    session.add.assert_not_called()


def test_seed_grants_are_exact_no_custodian():
    assert len(GRANTS) == 3
    assert GRANTS["sample-auditor"] == {"defect.read", "defect.export"}
    assert not any("type.retire" in grants for grants in GRANTS.values())
    assert "defect.capture" not in GRANTS["sample-supervisor"]


@pytest.mark.parametrize("username", ["", " ", "\t\n"])
def test_login_username_nonblank(username):
    with pytest.raises(ValidationError):
        LoginRequest(username=username, password=secrets.token_urlsafe())
