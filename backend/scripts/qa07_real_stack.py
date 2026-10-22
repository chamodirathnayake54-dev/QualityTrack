"""Run opt-in QA-07 browser validation on a private disposable real stack."""

import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from qualitytrack.models import Permission, User
from qualitytrack.security import HASHER
from qualitytrack.seed import GRANTS, seed_demo

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"
PG = Path("/usr/lib/postgresql/16/bin")
EVIDENCE = BACKEND / "docs/qa/batch2-evidence"


def _wait(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("Validation service exited during startup")
        try:
            if httpx.get(url).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.1)
    raise RuntimeError("Validation service did not become ready")


def _pg(*args):
    subprocess.run(
        [str(PG / args[0]), *map(str, args[1:])],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _reconcile(snapshot):
    browser = json.loads((EVIDENCE / "browser.json").read_text())
    checks = []
    for entry in browser["evidence"]:
        if "journey" in entry and "final" in entry:
            parent = entry["final"]
            row = next(r for r in snapshot["defect"] if str(r["id"]) == parent["id"])
            for key in (
                "part_number",
                "quantity_affected",
                "severity",
                "status",
                "revision",
            ):
                assert row[key] == parent[key], key
            causes = [
                r for r in snapshot["rca_entry"] if str(r["defect_id"]) == parent["id"]
            ]
            assert len(causes) == 1
            assert causes[0]["cause_text"] == "Fixture clamp loose"
            assert causes[0]["recorded_by_ref"] == "sample-engineer"
            history = [
                r
                for r in snapshot["defect_status_event"]
                if str(r["defect_id"]) == parent["id"]
            ]
            assert len(history) == len(entry["history"]) == 1
            event = entry["history"][0]
            for key in ("old_status", "new_status", "actor_ref", "aggregate_revision"):
                assert history[0][key] == event[key], key
            assert history[0]["occurred_at"] == datetime.fromisoformat(
                event["occurred_at"].replace("Z", "+00:00")
            )
            for action in entry["actions"]:
                saved = next(
                    r
                    for r in snapshot["corrective_action"]
                    if str(r["id"]) == action["id"]
                )
                assert str(saved["defect_id"]) == parent["id"]
                for key in ("description", "owner_ref", "status"):
                    assert saved[key] == action[key], key
                assert saved["due_date"].isoformat() == action["due_date"]
            checks.append({"journey": entry["journey"], "defect_id": parent["id"]})
        if entry.get("case") == "20" and "actions" in entry:
            assert entry["writes"] == 1
            matches = [
                r
                for r in snapshot["corrective_action"]
                if str(r["defect_id"]) == entry["defect_id"]
            ]
            assert len(matches) == 1
            assert str(matches[0]["id"]) == entry["actions"][0]["id"]
            checks.append({"case": "20", "count": 1, "id": str(matches[0]["id"])})
    assert len(checks) == 3, "Both journeys and lost response require data evidence"
    return checks


# PUBLIC_INTERFACE
def main():
    """Create isolated fixtures, run Chromium, save safe evidence, and tear down."""
    if os.environ.get("QA07_DISPOSABLE") != "true":
        raise SystemExit("Set QA07_DISPOSABLE=true to authorize isolated test fixtures")
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node 22 must be available on PATH")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    passwords = {ref: secrets.token_urlsafe(32) for ref in GRANTS}
    denied = {
        "qa-no-capture": GRANTS["sample-engineer"] - {"defect.capture"},
        "qa-no-transition": GRANTS["sample-engineer"] - {"defect.investigate"},
        "qa-no-read": set(),
        "qa-no-export": {"defect.read"},
        "qa-supervisor-denied": {"defect.read"},
    }
    passwords.update({ref: secrets.token_urlsafe(32) for ref in denied})
    children = []
    started = False
    engine = None
    with tempfile.TemporaryDirectory(prefix="qt-qa07-") as directory:
        root = Path(directory)
        socket = root / "socket"
        socket.mkdir(mode=0o700)
        try:
            _pg(
                "initdb",
                "-D",
                root / "data",
                "-U",
                "qt_qa",
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
                f"-k {socket} -c listen_addresses='' "
                "-c unix_socket_permissions=0700",
                "-w",
                "start",
            )
            started = True
            url = URL.create(
                "postgresql+psycopg",
                username="qt_qa",
                database="postgres",
                query={"host": str(socket)},
            ).render_as_string(hide_password=False)
            engine = create_engine(url)
            with engine.begin() as connection:
                cfg = Config(str(BACKEND / "alembic.ini"))
                cfg.attributes["connection"] = connection
                command.upgrade(cfg, "head")
            with Session(engine) as session, session.begin():
                seed_demo(session, True, passwords)
                for ref, grants in denied.items():
                    session.add(
                        User(
                            ref=ref,
                            issuer="qualitytrack-local",
                            subject=ref,
                            username=ref,
                            display_name=ref,
                            active=True,
                            password_hash=HASHER.hash(passwords[ref]),
                        )
                    )
                    session.flush()
                    for operation in grants:
                        session.add(
                            Permission(user_ref=ref, operation=operation, scope="plant")
                        )
                # Test-only custodian grant; never alters the shipped seed policy.
                session.add(
                    Permission(
                        user_ref="sample-supervisor",
                        operation="type.retire",
                        scope="plant",
                    )
                )
            env = dict(os.environ)
            env.update(
                DATABASE_URL=url,
                JWT_SECRET_KEY=secrets.token_urlsafe(48),
                QT_DEMO_MODE="true",
                PLANT_TIMEZONE="Etc/UTC",
                VITE_API_BASE_URL="/api/v1",
                QA07_PASSWORDS=json.dumps(passwords),
                QA07_EVIDENCE=str(EVIDENCE),
            )
            api = subprocess.Popen(
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
                ],
                cwd=BACKEND,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            children.append(api)
            _wait("http://127.0.0.1:8000/openapi.json", api)
            vite_command = [
                node,
                "node_modules/vite/bin/vite.js",
                "--host",
                "127.0.0.1",
                "--port",
                "4173",
                "--strictPort",
            ]
            vite = subprocess.Popen(
                vite_command,
                cwd=FRONTEND,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            children.append(vite)
            _wait("http://127.0.0.1:4173", vite)
            # Separate unconfigured frontend for case 01, never touch .env.
            negative_env = dict(env)
            negative_env.pop("VITE_API_BASE_URL")
            negative_command = [*vite_command]
            negative_command[-2] = "4174"
            negative = subprocess.Popen(
                negative_command,
                cwd=FRONTEND,
                env=negative_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            children.append(negative)
            _wait("http://127.0.0.1:4174", negative)
            metadata = {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "head": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=BACKEND, text=True
                ).strip(),
                "candidate": "uncommitted Batch 2 worktree",
                "python": sys.version.split()[0],
                "node": subprocess.check_output([node, "--version"], text=True).strip(),
                "postgres": subprocess.check_output(
                    [str(PG / "postgres"), "--version"], text=True
                ).strip(),
                "plant_zone": "Etc/UTC",
                "database_role": "isolated test administrator; not deployment-role QA",
            }
            (EVIDENCE / "browser.json").write_text(
                json.dumps({"evidence": [], "http": []}) + "\n"
            )
            result = subprocess.run(
                [
                    node,
                    "node_modules/@playwright/test/cli.js",
                    "test",
                    "--config=playwright.real.config.ts",
                ],
                cwd=FRONTEND,
                env=env,
                capture_output=True,
                text=True,
            )
            print(result.stdout)
            print(result.stderr)
            (EVIDENCE / "browser-run.txt").write_text(result.stdout + result.stderr)
            with engine.connect() as connection:
                snapshot = {}
                for table in (
                    "defect",
                    "rca_entry",
                    "corrective_action",
                    "defect_status_event",
                    "action_event",
                ):
                    rows = connection.execute(text(f"SELECT * FROM {table}"))
                    snapshot[table] = [dict(row._mapping) for row in rows]
                snapshot["grants"] = [
                    dict(row._mapping)
                    for row in connection.execute(
                        select(Permission.user_ref, Permission.operation)
                    )
                ]
            (EVIDENCE / "database.json").write_text(
                json.dumps(snapshot, indent=2, default=str) + "\n"
            )
            metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
            metadata["browser_exit"] = result.returncode
            if result.returncode == 0:
                metadata["database_reconciliation"] = _reconcile(snapshot)
            (EVIDENCE / "runtime.json").write_text(
                json.dumps(metadata, indent=2) + "\n"
            )
            raise SystemExit(result.returncode)
        finally:
            for child in reversed(children):
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            if engine:
                engine.dispose()
            if started:
                _pg("pg_ctl", "-D", root / "data", "-m", "fast", "-w", "stop")


if __name__ == "__main__":
    main()
