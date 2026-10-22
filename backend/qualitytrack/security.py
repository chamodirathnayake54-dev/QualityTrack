"""Local demo authentication and integrity-protected page continuation."""

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from qualitytrack.config import Settings
from qualitytrack.errors import Failure
from qualitytrack.models import Permission, User

HASHER = PasswordHasher()
# Equivalent verification work for unknown usernames; no usable seeded credential.
DUMMY_HASH = HASHER.hash(__import__("secrets").token_urlsafe(48))


# PUBLIC_INTERFACE
@dataclass(frozen=True)
class Principal:
    """Verified active user and freshly loaded explicit plant grants."""

    ref: str
    display_name: str
    permissions: frozenset[str]


# PUBLIC_INTERFACE
def require(principal: Principal, operation: str):
    """Reject an operation unless an explicit current grant exists."""
    if operation not in principal.permissions:
        raise Failure(403, "forbidden", "Operation is not permitted")


# PUBLIC_INTERFACE
def load_principal(session: Session, ref: str):
    """Resolve stable identity and current grants; never infer persona rights."""
    # A capture may have waited on a lookup lock since its first identity check.
    user = session.get(User, ref, populate_existing=True)
    if not user or not user.active:
        raise Failure(403, "inactive_user", "Caller is not permitted")
    grants = session.scalars(
        select(Permission.operation).where(
            Permission.user_ref == ref, Permission.scope == "plant"
        )
    )
    return Principal(user.ref, user.display_name, frozenset(grants))


# PUBLIC_INTERFACE
def issue_token(session: Session, settings: Settings, username: str, password: str):
    """Verify active local credentials and issue a fixed 3600-second HS256 JWT."""
    user = session.scalar(select(User).where(User.username == username))
    try:
        verified = HASHER.verify(user.password_hash if user else DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        verified = False
    if not verified or not user or not user.active:
        raise Failure(401, "invalid_credentials", "Credentials are invalid")
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user.ref,
            "iss": "qualitytrack-local",
            "aud": "qualitytrack-api",
            "iat": now,
            "exp": now + timedelta(seconds=3600),
        },
        settings.secret,
        algorithm="HS256",
    )


# PUBLIC_INTERFACE
def verify_token(token: str, settings: Settings):
    """Validate signature, expiry, issuer, audience and mandatory JWT claims."""
    try:
        claims = jwt.decode(
            token,
            settings.secret,
            algorithms=["HS256"],
            issuer="qualitytrack-local",
            audience="qualitytrack-api",
            options={"require": ["sub", "iss", "aud", "iat", "exp"]},
        )
        if not isinstance(claims["sub"], str) or not claims["sub"]:
            raise ValueError
        return claims["sub"]
    except (jwt.InvalidTokenError, ValueError):
        raise Failure(401, "invalid_token", "Authentication is required") from None


def _cursor_key(settings):
    return hmac.new(
        settings.secret.encode(), b"qualitytrack:defect-cursor:v1", hashlib.sha256
    ).digest()


# PUBLIC_INTERFACE
def encode_cursor(settings, principal, filters, created_at, identifier):
    """Bind continuation to caller, plant, filters, calendar and ordering."""
    payload = {
        "kind": "defects-v1",
        "caller": principal.ref,
        "scope": "plant",
        "zone": settings.plant_zone,
        "filters": filters.model_dump(mode="json"),
        "order": "created_at DESC,id DESC",
        "at": created_at.isoformat(),
        "id": str(identifier),
    }
    return jwt.encode(payload, _cursor_key(settings), algorithm="HS256")


# PUBLIC_INTERFACE
def decode_cursor(settings, principal, filters, token):
    """Reject tampering, wrong caller or altered filters before querying a page."""
    try:
        payload = jwt.decode(token, _cursor_key(settings), algorithms=["HS256"])
        expected = {
            "kind": "defects-v1",
            "caller": principal.ref,
            "scope": "plant",
            "zone": settings.plant_zone,
            "filters": filters.model_dump(mode="json"),
            "order": "created_at DESC,id DESC",
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise ValueError
        instant = datetime.fromisoformat(payload["at"])
        if instant.tzinfo is None or not isinstance(payload["id"], str):
            raise ValueError
        identifier = UUID(payload["id"])
        return instant, identifier
    except (
        jwt.InvalidTokenError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ):
        raise Failure(400, "invalid_cursor", "Page continuation is invalid") from None
