"""Batch 3 loopback HTTP evidence; never prints credentials or cursor values."""

import hashlib
import hmac
import importlib.util
import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import jwt
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import create_engine, select, update

from qualitytrack.models import Permission, User
from qualitytrack.schemas import Filters
from qualitytrack.security import HASHER

BACKEND = Path(__file__).resolve().parents[1]


def _run():
    spec = importlib.util.spec_from_file_location(
        "demo_db", BACKEND / "scripts/demo_db.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    metadata = helper.load_private()
    password = secrets.token_urlsafe(40)
    engine = create_engine(metadata["admin_url"])
    try:
        with engine.begin() as connection:
            connection.execute(
                update(User)
                .where(User.ref == "sample-engineer")
                .values(password_hash=HASHER.hash(password))
            )
            # Explicit throwaway fixture grant, not a product policy change.
            grant = dict(
                user_ref="sample-engineer", operation="type.retire", scope="plant"
            )
            if not connection.scalar(select(Permission.user_ref).filter_by(**grant)):
                connection.execute(Permission.__table__.insert().values(**grant))
    finally:
        engine.dispose()
    process = subprocess.Popen(
        [sys.executable, "scripts/demo_db.py", "api"],
        cwd=BACKEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Demo API exited before readiness")
                try:
                    response = client.get("/openapi.json")
                    response.raise_for_status()
                    live = response.json()
                    break
                except httpx.HTTPError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Demo API readiness failed")
            _exercise(client, live, password, metadata["secret"])
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=15)


def _exercise(client, live, password, secret):
    rows = []

    def call(method, path, template=None, status=200, **kwargs):
        template = template or path
        response = client.request(method, "/api/v1" + path, **kwargs)
        media = response.headers.get("content-type", "").split(";")[0]
        declaration = live["paths"]["/api/v1" + template][method]["responses"][
            str(response.status_code)
        ]["content"][media]["schema"]
        body = (
            response.content.decode("latin1")
            if media == "application/pdf"
            else response.json()
        )
        validator = Draft202012Validator(
            {"components": live["components"], "allOf": [declaration]},
            format_checker=FormatChecker(),
        )
        valid = not list(validator.iter_errors(body))
        valid = valid and response.status_code == status
        assert response.headers["cache-control"] == "private, no-store"
        if media == "application/pdf":
            valid = (
                valid
                and response.content.startswith(b"%PDF-")
                and response.content.rstrip().endswith(b"%%EOF")
            )
        if status >= 400:
            valid = (
                valid
                and media == "application/problem+json"
                and body["status"] == status
            )
        rows.append(
            dict(
                method=method.upper(),
                path=template,
                status=response.status_code,
                media=media,
                valid=valid,
            )
        )
        if not valid:
            raise RuntimeError("Response validation failed at " + template)
        return response

    login = call(
        "post",
        "/auth/login",
        json={"username": "sample-engineer", "password": password},
    )
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    choices = {}
    for path in ("/me", "/production-lines", "/shifts", "/defect-types", "/defects"):
        choices[path] = call("get", path, headers=headers).json()
    type_id = choices["/defect-types"]["items"][0]["id"]
    capture = dict(
        part_number="BATCH3-LIVE",
        defect_type_id=type_id,
        production_line_id=choices["/production-lines"]["items"][0]["id"],
        shift_id=choices["/shifts"]["items"][0]["id"],
        quantity_affected=1,
        severity="Major",
    )
    multipart = {"capture": (None, json.dumps(capture), "application/json")}
    saved = call("post", "/defects", status=201, headers=headers, files=multipart)
    parent = saved.json()["id"]
    dp, dt = f"/defects/{parent}", "/defects/{defect_id}"
    call("get", dp, dt, headers=headers)
    cause = call(
        "post",
        dp + "/causes",
        dt + "/causes",
        201,
        headers=headers,
        json={"text": "Live QA cause"},
    )
    call("get", dp + "/causes", dt + "/causes", headers=headers)
    call(
        "post",
        dp + "/transitions",
        dt + "/transitions",
        headers={**headers, "If-Match": cause.headers["etag"]},
        json={"target_status": "Under Investigation"},
    )
    action_body = dict(
        description="Live QA work",
        owner_ref="sample-engineer",
        due_date="2000-01-01",
        status="Open",
    )
    action = call(
        "post",
        dp + "/actions",
        dt + "/actions",
        201,
        headers=headers,
        json=action_body,
    )
    action_id = action.json()["id"]
    ap, at = f"/actions/{action_id}", "/actions/{action_id}"
    call("get", dp + "/actions", dt + "/actions", headers=headers)
    call("get", "/assignable-users", headers=headers, params={"defect_id": parent})
    call(
        "post",
        ap + "/transitions",
        at + "/transitions",
        headers={**headers, "If-Match": action.headers["etag"]},
        json={"target_status": "Complete", "completion_notes": "Live completion"},
    )
    call("get", dp + "/history", dt + "/history", headers=headers)
    call("get", ap + "/history", at + "/history", headers=headers)
    call("get", "/overdue-actions", headers=headers)
    call("get", dp + "/audit.pdf", dt + "/audit.pdf", headers=headers)
    call(
        "post",
        f"/defect-types/{type_id}/retire",
        "/defect-types/{type_id}/retire",
        headers={**headers, "If-Match": '"1"'},
        json={},
    )
    operations = [
        (path, method)
        for path, methods in live["paths"].items()
        for method in methods
        if method in ("get", "post")
    ]
    assert len(operations) == 20
    for template, method in operations:
        path = (
            template.removeprefix("/api/v1")
            .replace("{defect_id}", parent)
            .replace("{action_id}", action_id)
            .replace("{type_id}", type_id)
        )
        kwargs = {}
        if method == "post":
            if path == "/auth/login":
                kwargs = {"json": {"username": "sample-engineer", "password": "bad"}}
            elif path == "/defects":
                kwargs = {"files": multipart}
            elif path.endswith("/causes"):
                kwargs = {"json": {"text": "Live QA"}}
            elif path.endswith("/actions"):
                kwargs = {"json": action_body}
            elif path.endswith("/retire"):
                kwargs = {"json": {}}
            else:
                target = (
                    "Complete"
                    if path.startswith("/actions/")
                    else "Under Investigation"
                )
                kwargs = {"json": {"target_status": target}}
        if path == "/assignable-users":
            kwargs = {"params": {"defect_id": parent}}
        call(method, path, template.removeprefix("/api/v1"), 401, **kwargs)
    cases = [
        (dp + "/actions", dt + "/actions", f"actions:{parent}", [1]),
        (
            dp + "/causes",
            dt + "/causes",
            f"causes:{parent}",
            ["2026-01-01T00:00:00+00:00", 1],
        ),
        (dp + "/history", dt + "/history", f"history:{parent}", [True]),
        (ap + "/history", at + "/history", f"action-history:{action_id}", [True]),
        (
            "/overdue-actions",
            "/overdue-actions",
            "overdue-v1:Etc/UTC:due_date,id",
            ["2026-01-02", "2026-01-01", 1],
        ),
        ("/defects", "/defects", None, None),
    ]
    bound = {"caller": "sample-engineer", "scope": "plant"}
    for path, template, context, key in cases:
        if context:
            payload = {**bound, "context": context, "key": key}
            domain = b"qualitytrack:children:v1"
        else:
            payload = {
                **bound,
                "kind": "defects-v1",
                "zone": "Etc/UTC",
                "filters": Filters().model_dump(mode="json"),
                "order": "created_at DESC,id DESC",
                "at": "2026-01-01T00:00:00+00:00",
                "id": 1,
            }
            domain = b"qualitytrack:defect-cursor:v1"
        token = jwt.encode(
            payload,
            hmac.new(secret.encode(), domain, hashlib.sha256).digest(),
            algorithm="HS256",
        )
        result = call(
            "get", path, template, 400, headers=headers, params={"cursor": token}
        )
        assert result.json() == {
            "type": "about:blank",
            "title": "Page continuation is invalid",
            "status": 400,
            "code": "invalid_cursor",
        }
        assert token not in result.text
    assert all(
        "application/problem+json"
        in live["paths"][path][method]["responses"]["500"]["content"]
        for path, method in operations
    )
    print(
        json.dumps(
            {
                "operations": len(operations),
                "responses": len(rows),
                "valid": sum(row["valid"] for row in rows),
                "accuracy_percent": 100 * sum(row["valid"] for row in rows) / len(rows),
                "rows": rows,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    _run()
