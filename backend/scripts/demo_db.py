"""Disposable PostgreSQL 16 helper. Never reads/writes .env or prints secrets."""

import argparse
import json
import os
import secrets
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

BACKEND = Path(__file__).resolve().parents[1]
PRIVATE = Path("/tmp") / f"qualitytrack-demo-{os.getuid()}"
PG_BIN = Path("/usr/lib/postgresql/16/bin")


def _postgres_bin():
    """Locate PostgreSQL 16 on macOS without altering the Linux default."""
    if sys.platform != "darwin":
        return PG_BIN
    for directory in (
        Path("/Library/PostgreSQL/16/bin"),
        Path("/opt/homebrew/opt/postgresql@16/bin"),
        Path("/usr/local/opt/postgresql@16/bin"),
    ):
        if all(os.access(directory / name, os.X_OK) for name in ("initdb", "pg_ctl")):
            return directory
    raise RuntimeError("Install PostgreSQL 16 before using the demo database helper")


def _private_directory():
    if PRIVATE.is_symlink():
        raise RuntimeError("Private directory must not be a symlink")
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    info = PRIVATE.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise RuntimeError(
            "Host-local directory does not preserve owner-only permissions"
        )
    # Refuse workspace-backed storage even when the helper is invoked elsewhere.
    if BACKEND.parent in PRIVATE.resolve().parents:
        raise RuntimeError("Database storage must be outside the workspace")
    return PRIVATE


def _pg(action, *args):
    result = subprocess.run(
        [str(_postgres_bin() / action), *map(str, args)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode:
        raise RuntimeError("PostgreSQL lifecycle command failed")


def _url(user, database, password=None):
    return URL.create(
        "postgresql+psycopg",
        username=user,
        password=password,
        database=database,
        query={"host": str(PRIVATE / "socket")},
    ).render_as_string(hide_password=False)


# PUBLIC_INTERFACE
def load_private():
    """Read owner-only helper metadata, never returning it to terminal output."""
    root = _private_directory()
    path = root / "credentials.json"
    info = path.lstat()
    if (
        path.is_symlink()
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise RuntimeError("Credential file is not private")
    return json.loads(path.read_text())


# PUBLIC_INTERFACE
def stop():
    """Stop this helper's local cluster; no other PostgreSQL service is touched."""
    root = _private_directory()
    if (root / "data" / "postmaster.pid").exists():
        _pg("pg_ctl", "-D", root / "data", "-m", "fast", "-w", "stop")


# PUBLIC_INTERFACE
def recreate(confirmed):
    """Rebuild only the known disposable private cluster after explicit confirmation."""
    if not confirmed or os.environ.get("QT_DEMO_MODE") != "true":
        raise RuntimeError("Explicit demo mode and --confirm-disposable are required")
    if any(
        not os.environ.get("SEED_PASSWORD_" + role)
        for role in ("ENGINEER", "SUPERVISOR", "AUDITOR")
    ):
        raise RuntimeError("Secure per-user seed passwords must be supplied")
    root = _private_directory()
    stop()
    for name in ("data", "socket"):
        path = root / name
        if path.is_symlink():
            raise RuntimeError("Refusing symlink in disposable storage")
        if path.exists():
            shutil.rmtree(path)
    (root / "socket").mkdir(mode=0o700)
    _pg(
        "initdb",
        "-D",
        root / "data",
        "-U",
        "qt_admin",
        "--auth-local=trust",
        "--auth-host=reject",
        "--encoding=UTF8",
        "--locale=C",
    )
    _pg(
        "pg_ctl",
        "-D",
        root / "data",
        "-l",
        root / "postgres.log",
        "-o",
        f"-k {root / 'socket'} -c listen_addresses='' -c unix_socket_permissions=0700",
        "-w",
        "start",
    )
    app_password = secrets.token_urlsafe(48)
    admin = create_engine(_url("qt_admin", "postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            # Password is generated URL-safe, never received as SQL from a caller.
            connection.exec_driver_sql(
                f"CREATE ROLE qt_app LOGIN PASSWORD '{app_password}' "
                "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
            )
            connection.exec_driver_sql("CREATE DATABASE qualitytrack OWNER qt_admin")
    finally:
        admin.dispose()
    metadata = {
        "admin_url": _url("qt_admin", "qualitytrack"),
        "app_url": _url("qt_app", "qualitytrack", app_password),
        "secret": secrets.token_urlsafe(48),
    }
    # The socket is private; SCRAM still protects application connections.
    hba = root / "data" / "pg_hba.conf"
    hba.write_text(
        "local all qt_admin trust\n"
        "local all qt_app scram-sha-256\n"
        "local all all reject\n"
    )
    _pg("pg_ctl", "-D", root / "data", "reload")
    descriptor = os.open(
        root / "credentials.json",
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w") as handle:
        json.dump(metadata, handle)
    engine = create_engine(metadata["admin_url"])
    try:
        with engine.begin() as connection:
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
                    "REVOKE UPDATE ON rca_entry, defect_status_event, action_event "
                    "FROM qt_app"
                )
            )
            connection.execute(text("REVOKE ALL ON alembic_version FROM qt_app"))
    finally:
        engine.dispose()
    env = _environment(metadata)
    result = subprocess.run(
        [sys.executable, "-m", "qualitytrack.seed"], cwd=BACKEND, env=env
    )
    if result.returncode:
        raise RuntimeError("Demo bootstrap failed")
    print("Disposable PostgreSQL 16 migrated and seeded; private storage verified.")


def _environment(metadata):
    env = dict(os.environ)
    env.update(
        DATABASE_URL=metadata["app_url"],
        JWT_SECRET_KEY=metadata["secret"],
        QT_DEMO_MODE="true",
    )
    return env


# PUBLIC_INTERFACE
def main():
    """Dispatch recreate, API, test or stop without printing credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["recreate", "api", "test", "stop"])
    parser.add_argument("--confirm-disposable", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "recreate":
            recreate(args.confirm_disposable)
        elif args.action == "stop":
            stop()
        else:
            env = _environment(load_private())
            command_line = (
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "qualitytrack.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                    "--no-access-log",
                ]
                if args.action == "api"
                else [sys.executable, "-m", "pytest", "-q"]
            )
            raise SystemExit(subprocess.call(command_line, cwd=BACKEND, env=env))
    except Exception:
        raise SystemExit(
            "Demo database operation failed; no credentials disclosed"
        ) from None


if __name__ == "__main__":
    main()
