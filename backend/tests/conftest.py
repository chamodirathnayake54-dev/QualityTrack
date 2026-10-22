"""Real PostgreSQL integration fixtures; no .env loading, no shared test rows."""

import importlib.util
import secrets
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from qualitytrack.config import Settings
from qualitytrack.main import create_app
from qualitytrack.seed import GRANTS, seed_demo

BACKEND = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("demo_db", BACKEND / "scripts/demo_db.py")
demo_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo_db)


@pytest.fixture(scope="session")
def private_metadata():
    # Intentionally fail rather than silently skip the required integration suite.
    return demo_db.load_private()


@pytest.fixture
def database(private_metadata):
    name = "qt_test_" + uuid4().hex
    url = make_url(private_metadata["admin_url"])
    control = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with control.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    admin = create_engine(url.set(database=name))
    app = create_engine(make_url(private_metadata["app_url"]).set(database=name))
    passwords = {ref: secrets.token_urlsafe(32) for ref in GRANTS}
    try:
        with admin.begin() as connection:
            cfg = Config(str(BACKEND / "alembic.ini"))
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
            connection.execute(text("REVOKE ALL ON SCHEMA public FROM PUBLIC"))
            connection.execute(text("GRANT USAGE ON SCHEMA public TO qt_app"))
            connection.execute(
                text(
                    "GRANT SELECT, INSERT, UPDATE "
                    "ON ALL TABLES IN SCHEMA public TO qt_app"
                )
            )
            connection.execute(
                text(
                    "REVOKE UPDATE ON rca_entry, defect_status_event, "
                    "action_event FROM qt_app"
                )
            )
            connection.execute(text("REVOKE ALL ON alembic_version FROM qt_app"))
        sessions = sessionmaker(app, expire_on_commit=False)
        with sessions() as session, session.begin():
            seed_demo(session, True, passwords)
        settings = Settings(
            app.url.render_as_string(hide_password=False),
            secrets.token_urlsafe(48),
            "Etc/UTC",
            True,
        )
        yield admin, app, sessions, passwords, settings
    finally:
        app.dispose()
        admin.dispose()
        with control.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE "{name}" WITH (FORCE)')
        control.dispose()


@pytest.fixture
def client(database):
    _, _, sessions, _, settings = database
    with TestClient(create_app(settings, sessions)) as client:
        yield client


@pytest.fixture
def auth(client, database):
    def headers(ref="sample-engineer"):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": ref, "password": database[3][ref]},
        )
        assert response.status_code == 200
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    return headers


@pytest.fixture
def capture_payload():
    from qualitytrack.seed import lookup_id

    return {
        "part_number": "TEST-" + uuid4().hex,
        "defect_type_id": str(lookup_id("SAMPLE-SCRATCH")),
        "production_line_id": str(lookup_id("SAMPLE-LINE-A")),
        "shift_id": str(lookup_id("SAMPLE-SHIFT-1")),
        "quantity_affected": 3,
        "severity": "Major",
    }
