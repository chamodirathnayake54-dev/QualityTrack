"""Batch A PostgreSQL contract and concurrency verification."""

import json
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import delete, func, inspect, select, text, update
from sqlalchemy.exc import DBAPIError

from qualitytrack.defects import capture_defect
from qualitytrack.errors import Failure
from qualitytrack.models import (
    Base,
    Defect,
    DefectType,
    Permission,
    ProductionLine,
    Shift,
    User,
)
from qualitytrack.schemas import Capture
from qualitytrack.security import load_principal
from qualitytrack.seed import GRANTS, SeedDiscrepancy, lookup_id, seed_demo


def _post(client, headers, payload, extra=None):
    files = [("capture", (None, json.dumps(payload), "application/json"))]
    files.extend(extra or [])
    return client.post("/api/v1/defects", headers=headers, files=files)


def test_migration_matches_full_erd(database):
    admin = database[0]
    with admin.connect() as connection:
        assert (
            compare_metadata(MigrationContext.configure(connection), Base.metadata)
            == []
        )
        assert set(inspect(connection).get_table_names()) == set(
            Base.metadata.tables
        ) | {"alembic_version"}


def test_application_role_is_least_privileged(database):
    with database[1].connect() as connection:
        assert (
            connection.scalar(
                text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
            )
            is False
        )
        for table in ("action_event", "defect_status_event", "rca_entry"):
            assert (
                connection.scalar(
                    text("SELECT has_table_privilege(current_user, :t, 'DELETE')"),
                    {"t": table},
                )
                is False
            )
            assert (
                connection.scalar(
                    text("SELECT has_table_privilege(current_user, :t, 'UPDATE')"),
                    {"t": table},
                )
                is False
            )


def test_seed_rerun_preserves_hashes(database):
    _, _, sessions, _, _ = database
    with sessions() as session, session.begin():
        before = dict(session.execute(select(User.ref, User.password_hash)).all())
        seed_demo(session, True, {ref: secrets.token_urlsafe() for ref in GRANTS})
        assert (
            dict(session.execute(select(User.ref, User.password_hash)).all()) == before
        )
        assert session.scalar(select(func.count()).select_from(User)) == 3
        assert session.scalar(select(func.count()).select_from(Permission)) == sum(
            len(grants) for grants in GRANTS.values()
        )


@pytest.mark.parametrize(
    "change", ["grant", "active", "lookup", "collision", "partial"]
)
def test_seed_drift_aborts_without_repair(database, change):
    admin, _, sessions, _, _ = database
    with admin.begin() as connection:
        if change == "grant":
            connection.execute(
                delete(Permission).where(
                    Permission.user_ref == "sample-engineer",
                    Permission.operation == "defect.capture",
                )
            )
        elif change == "active":
            connection.execute(
                update(User).where(User.ref == "sample-engineer").values(active=False)
            )
        elif change == "lookup":
            connection.execute(
                update(Shift)
                .where(Shift.id == lookup_id("SAMPLE-SHIFT-1"))
                .values(label="Changed")
            )
        elif change == "collision":
            connection.execute(
                update(User)
                .where(User.ref == "sample-engineer")
                .values(username="other")
            )
        else:
            connection.execute(
                delete(DefectType).where(DefectType.id == lookup_id("SAMPLE-DENT"))
            )
    with sessions() as session:
        with pytest.raises(SeedDiscrepancy), session.begin():
            seed_demo(session, True, {})
    with admin.connect() as connection:
        if change == "grant":
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(Permission)
                    .where(
                        Permission.user_ref == "sample-engineer",
                        Permission.operation == "defect.capture",
                    )
                )
                == 0
            )
        if change == "active":
            assert (
                connection.scalar(
                    select(User.active).where(User.ref == "sample-engineer")
                )
                is False
            )


def test_login_me_and_revocation(client, auth, database):
    headers = auth()
    result = client.get("/api/v1/me", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["permissions"] == sorted(GRANTS["sample-engineer"])
    assert body["plant_zone"] == "Etc/UTC"
    assert not {"password_hash", "access_token", "username"} & body.keys()
    with database[0].begin() as connection:
        connection.execute(
            delete(Permission).where(
                Permission.user_ref == "sample-engineer",
                Permission.operation == "defect.read",
            )
        )
    assert (
        "defect.read"
        not in client.get("/api/v1/me", headers=headers).json()["permissions"]
    )
    assert client.get("/api/v1/defects", headers=headers).status_code == 403


# PUBLIC_INTERFACE
def test_cached_identity_is_refreshed_before_capture(database, capture_payload):
    """A deactivation committed after initial resolution must prevent capture."""
    with database[2]() as session, session.begin():
        cached = session.get(User, "sample-engineer")
        principal = load_principal(session, cached.ref)
        with database[0].begin() as connection:
            connection.execute(
                update(User).where(User.ref == cached.ref).values(active=False)
            )
        with pytest.raises(Failure) as caught:
            capture_defect(session, principal, Capture(**capture_payload))
        assert caught.value.problem.status == 403
        assert session.scalar(select(func.count()).select_from(Defect)) == 0


def test_inactive_login_and_existing_token_denied(client, auth, database):
    headers = auth()
    with database[0].begin() as connection:
        connection.execute(
            update(User).where(User.ref == "sample-engineer").values(active=False)
        )
    assert client.get("/api/v1/me", headers=headers).status_code == 403
    result = client.post(
        "/api/v1/auth/login",
        json={
            "username": "sample-engineer",
            "password": database[3]["sample-engineer"],
        },
    )
    assert result.status_code == 401 and result.json()["code"] == "invalid_credentials"


def test_unknown_wrong_password_and_validation_never_echo(client):
    password = secrets.token_urlsafe()
    for body in (
        {"username": "missing", "password": password},
        {"username": "sample-engineer", "password": password},
        {"username": " ", "password": password},
        {"username": "sample-engineer", "password": [password]},
    ):
        result = client.post("/api/v1/auth/login", json=body)
        assert result.status_code in (401, 422)
        assert password not in result.text
        assert result.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize(
    "route",
    [
        "/api/v1/me",
        "/api/v1/production-lines",
        "/api/v1/shifts",
        "/api/v1/defect-types",
        "/api/v1/defects",
    ],
)
def test_missing_authentication_denied(client, route):
    assert client.get(route).status_code == 401


@pytest.mark.parametrize(
    "route,model",
    [
        ("/api/v1/production-lines", ProductionLine),
        ("/api/v1/shifts", Shift),
        ("/api/v1/defect-types", DefectType),
    ],
)
def test_active_lookup_choices_require_capture(client, auth, database, route, model):
    engineer = auth()
    items = client.get(route, headers=engineer).json()["items"]
    assert len(items) == 2
    retired_id = UUID(items[0]["id"])
    with database[0].begin() as connection:
        connection.execute(
            update(model).where(model.id == retired_id).values(retired=True)
        )
    remaining = client.get(route, headers=engineer).json()["items"]
    assert len(remaining) == 1 and remaining[0]["id"] != str(retired_id)
    assert client.get(route, headers=auth("sample-supervisor")).status_code == 403


@pytest.mark.parametrize("severity", ["Critical", "Major", "Minor"])
def test_capture_and_read_preserve_snapshots(
    client, auth, capture_payload, database, severity
):
    headers = auth()
    capture_payload["severity"] = severity
    result = _post(client, {**headers, "If-Match": "ignored"}, capture_payload)
    assert result.status_code == 201, result.text
    body = result.json()
    assert body["status"] == "Open" and body["revision"] == 1
    assert body["severity"] == severity and body["has_photo"] is False
    assert body["created_by_ref"] == "sample-engineer"
    assert result.headers["etag"] == '"1"'
    with database[0].begin() as connection:
        for model in (DefectType, ProductionLine, Shift):
            connection.execute(update(model).values(label="Changed", retired=True))
    read = client.get("/api/v1/defects/" + body["id"], headers=headers)
    assert read.status_code == 200 and read.json() == body
    assert body["defect_type"]["label_at_capture"] == "Scratch"
    assert body["production_line"]["label_at_capture"] == "Sample Line A"
    assert body["shift"]["label_at_capture"] == "Sample Shift 1"


@pytest.mark.parametrize(
    "field,value",
    [
        ("quantity_affected", 0),
        ("quantity_affected", 1.5),
        ("quantity_affected", "1"),
        ("quantity_affected", True),
        ("quantity_affected", 1000001),
        ("part_number", " "),
        ("part_number", "x" * 51),
        ("severity", None),
        ("severity", "Automatic"),
        ("created_by_ref", "forged"),
    ],
)
def test_invalid_capture_no_write(
    client, auth, capture_payload, database, field, value
):
    capture_payload[field] = value
    response = _post(client, auth(), capture_payload)
    assert response.status_code == 422
    with database[1].connect() as connection:
        assert connection.scalar(select(func.count()).select_from(Defect)) == 0


def test_capture_photo_duplicate_and_malformed_parts_rollback(
    client, auth, capture_payload, database
):
    headers = auth()
    assert (
        _post(
            client,
            headers,
            capture_payload,
            [("photo", ("test.png", b"not-supported", "image/png"))],
        ).status_code
        == 422
    )
    assert (
        _post(
            client,
            headers,
            capture_payload,
            [("capture", (None, json.dumps(capture_payload)))],
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/defects", headers=headers, files={"capture": (None, "{not-json")}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/defects", headers=headers, json=capture_payload
        ).status_code
        == 400
    )
    with database[1].connect() as connection:
        assert connection.scalar(select(func.count()).select_from(Defect)) == 0


def test_denied_capture_precedes_state_and_input(
    client, auth, capture_payload, database
):
    result = _post(client, auth("sample-supervisor"), {"bad": "input"})
    assert result.status_code == 403
    with database[1].connect() as connection:
        assert connection.scalar(select(func.count()).select_from(Defect)) == 0


def test_denied_read_precedes_record_existence(client, auth, database):
    headers = auth()
    with database[0].begin() as connection:
        connection.execute(
            delete(Permission).where(
                Permission.user_ref == "sample-engineer",
                Permission.operation == "defect.read",
            )
        )
    result = client.get("/api/v1/defects/" + str(uuid4()), headers=headers)
    assert result.status_code == 403
    assert "part_number" not in result.text


def test_missing_record_safe_404(client, auth):
    assert (
        client.get("/api/v1/defects/" + str(uuid4()), headers=auth()).status_code == 404
    )


def test_keyset_equal_times_filters_and_caller_binding(
    client, auth, capture_payload, database
):
    headers = auth()
    ids = []
    for _ in range(5):
        response = _post(client, headers, capture_payload)
        assert response.status_code == 201
        ids.append(UUID(response.json()["id"]))
    with database[0].begin() as connection:
        connection.execute(
            update(Defect)
            .where(Defect.id.in_(ids))
            .values(created_at=datetime(2026, 3, 8, 6, 0, tzinfo=timezone.utc))
        )
    params = {"part_number": capture_payload["part_number"], "limit": 2}
    first = client.get("/api/v1/defects", headers=headers, params=params).json()
    assert first["next_cursor"]
    assert (
        client.get(
            "/api/v1/defects",
            headers=auth("sample-supervisor"),
            params={**params, "cursor": first["next_cursor"]},
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/v1/defects",
            headers=headers,
            params={**params, "part_number": "other", "cursor": first["next_cursor"]},
        ).status_code
        == 400
    )
    found = []
    page = first
    while True:
        found.extend(UUID(row["id"]) for row in page["items"])
        if not page["next_cursor"]:
            break
        page = client.get(
            "/api/v1/defects",
            headers=headers,
            params={**params, "cursor": page["next_cursor"]},
        ).json()
    assert found == sorted(ids, reverse=True)


@pytest.mark.parametrize(
    "query",
    [
        {"status": "Complete"},
        {"severity": "major"},
        {"limit": 0},
        {"limit": 101},
        {"start_date": "2026-01-01"},
        {"production_line_id": "bad"},
        {"start_date": "2026-02-01", "end_date": "2026-01-01"},
        {"cursor": "tampered"},
    ],
)
def test_invalid_collection_queries(client, auth, query):
    assert client.get("/api/v1/defects", headers=auth(), params=query).status_code in (
        400,
        422,
    )


def test_all_collection_filters_and_dst_boundaries(
    client, auth, capture_payload, database
):
    headers = auth()
    identifier = UUID(_post(client, headers, capture_payload).json()["id"])
    with database[0].begin() as connection:
        connection.execute(
            update(Defect)
            .where(Defect.id == identifier)
            .values(created_at=datetime(2026, 3, 9, 3, 59, tzinfo=timezone.utc))
        )
    client.app.state.settings = type(database[4])(
        database[4].database_url, database[4].secret, "America/New_York", True
    )
    params = {
        **{
            key: value
            for key, value in capture_payload.items()
            if key not in ("quantity_affected",)
        },
        "status": "Open",
        "start_date": "2026-03-08",
        "end_date": "2026-03-08",
    }
    page = client.get("/api/v1/defects", headers=headers, params=params).json()
    assert [row["id"] for row in page["items"]] == [str(identifier)]
    params["severity"] = "Minor"
    assert (
        client.get("/api/v1/defects", headers=headers, params=params).json()["items"]
        == []
    )
    params["severity"] = "Major"
    with database[0].begin() as connection:
        connection.execute(
            update(Defect)
            .where(Defect.id == identifier)
            .values(created_at=datetime(2026, 3, 9, 4, 0, tzinfo=timezone.utc))
        )
    assert (
        client.get("/api/v1/defects", headers=headers, params=params).json()["items"]
        == []
    )


def test_capture_failure_after_flush_rolls_back(database, capture_payload):
    _, _, sessions, _, _ = database
    identifier = None
    with sessions() as session:
        with pytest.raises(RuntimeError), session.begin():
            caller = load_principal(session, "sample-engineer")
            identifier = capture_defect(session, caller, Capture(**capture_payload)).id
            raise RuntimeError("injected failure")
    with sessions() as session:
        assert session.get(Defect, identifier) is None


@pytest.mark.parametrize(
    "model,code",
    [
        (DefectType, "SAMPLE-SCRATCH"),
        (ProductionLine, "SAMPLE-LINE-A"),
        (Shift, "SAMPLE-SHIFT-1"),
    ],
)
def test_retirement_wins_lock_capture_rechecks(database, capture_payload, model, code):
    admin, _, sessions, _, _ = database
    with admin.connect() as connection:
        transaction = connection.begin()
        connection.execute(
            select(model).where(model.id == lookup_id(code)).with_for_update()
        )
        connection.execute(
            update(model).where(model.id == lookup_id(code)).values(retired=True)
        )
        with ThreadPoolExecutor(max_workers=1) as executor:

            def worker():
                with sessions() as session, session.begin():
                    session.execute(text("SET LOCAL lock_timeout = '5s'"))
                    principal = load_principal(session, "sample-engineer")
                    try:
                        capture_defect(session, principal, Capture(**capture_payload))
                    except Failure as exc:
                        return exc.problem.status
                    return 201

            future = executor.submit(worker)
            # Observe a real PostgreSQL lock wait, not just a scheduling delay.
            waiting = False
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                with admin.connect() as observer:
                    waiting = observer.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                            "WHERE datname = current_database() "
                            "AND wait_event_type = 'Lock' "
                            "AND pid <> pg_backend_pid())"
                        )
                    )
                if waiting:
                    break
                time.sleep(0.02)
            transaction.commit()
            assert waiting
            assert future.result(timeout=6) == 409
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Defect)) == 0


def test_capture_wins_lock_retirement_waits_and_snapshot_survives(
    database, capture_payload
):
    admin, _, sessions, _, _ = database
    with sessions() as session:
        transaction = session.begin()
        row = capture_defect(
            session,
            load_principal(session, "sample-engineer"),
            Capture(**capture_payload),
        )
        identifier = row.id
        with ThreadPoolExecutor(max_workers=1) as executor:

            def retire():
                with admin.begin() as connection:
                    connection.execute(text("SET LOCAL lock_timeout = '5s'"))
                    connection.execute(
                        update(DefectType)
                        .where(DefectType.id == lookup_id("SAMPLE-SCRATCH"))
                        .values(retired=True, label="Changed")
                    )

            future = executor.submit(retire)
            waiting = False
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                with admin.connect() as observer:
                    waiting = observer.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                            "WHERE datname = current_database() "
                            "AND wait_event_type = 'Lock')"
                        )
                    )
                if waiting:
                    break
                time.sleep(0.02)
            transaction.commit()
            assert waiting
            future.result(timeout=6)
    with sessions() as session:
        assert session.get(Defect, identifier).type_label_at_capture == "Scratch"


def test_database_quantity_constraint_rolls_back(database, capture_payload):
    _, _, sessions, _, _ = database
    with sessions() as session:
        with pytest.raises(DBAPIError), session.begin():
            row = capture_defect(
                session,
                load_principal(session, "sample-engineer"),
                Capture(**capture_payload),
            )
            row.quantity_affected = 0
            session.flush()
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Defect)) == 0


def test_openapi_batch_boundary(client):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert len(paths) == 7
    assert sum(len(operations) for operations in paths.values()) == 8
    assert "/api/v1/defects/{defect_id}" in paths
    assert not any(
        word in path
        for path in paths
        for word in (
            "transitions",
            "causes",
            "actions",
            "analytics",
            "audit.pdf",
            "retire",
        )
    )
    assert (
        "multipart/form-data"
        in paths["/api/v1/defects"]["post"]["requestBody"]["content"]
    )
