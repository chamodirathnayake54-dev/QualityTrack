"""Explicit demo-only bootstrap; no startup seeding or credential output."""

import os
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from qualitytrack.config import Settings
from qualitytrack.models import DefectType, Permission, ProductionLine, Shift, User
from qualitytrack.security import HASHER

GRANTS = {
    "sample-engineer": {
        "defect.capture",
        "defect.read",
        "cause.create",
        "defect.investigate",
        "action.assign",
        "action.progress",
        "action.complete",
        "defect.export",
    },
    "sample-supervisor": {
        "defect.read",
        "cause.create",
        "defect.investigate",
        "defect.close",
        "defect.reopen",
        "action.assign",
        "action.progress",
        "action.complete",
        "action.reopen",
        "defect.export",
        "analytics.read",
    },
    "sample-auditor": {"defect.read", "defect.export"},
}
# Explicit future policy fixture, never derived from persona/display names.
DEMO_ELIGIBLE_OWNERS = frozenset({"sample-engineer", "sample-supervisor"})
DEMO_SUPERVISOR_AUTHORITY = frozenset({"sample-supervisor"})
LOOKUPS = (
    (ProductionLine, "SAMPLE-LINE-A", "Sample Line A"),
    (ProductionLine, "SAMPLE-LINE-B", "Sample Line B"),
    (Shift, "SAMPLE-SHIFT-1", "Sample Shift 1"),
    (Shift, "SAMPLE-SHIFT-2", "Sample Shift 2"),
    (DefectType, "SAMPLE-SCRATCH", "Scratch"),
    (DefectType, "SAMPLE-DENT", "Dent"),
)


# PUBLIC_INTERFACE
class SeedDiscrepancy(RuntimeError):
    """Safe bootstrap refusal; no existing evidence or authority is overwritten."""


# PUBLIC_INTERFACE
def lookup_id(code):
    """Return a stable seed-owned identifier, not an approved production ID."""
    return uuid5(NAMESPACE_URL, "qualitytrack-demo/" + code)


# PUBLIC_INTERFACE
def seed_demo(session: Session, demo: bool, passwords: dict[str, str]):
    """Verify or atomically insert the entire LLD 16.3 fixture; caller transacts."""
    if not demo:
        raise SeedDiscrepancy("Explicit demo mode is required")
    # Serialize concurrent first-run bootstraps without adding a product table.
    from sqlalchemy import text

    session.execute(text("SELECT pg_advisory_xact_lock(6100601)"))
    seed_refs = set(GRANTS)
    present_users = list(
        session.scalars(
            select(User).where(
                (User.ref.in_(seed_refs)) | (User.username.in_(seed_refs))
            )
        )
    )
    present_lookups = [
        session.scalar(
            select(model).where((model.id == lookup_id(code)) | (model.code == code))
        )
        for model, code, _ in LOOKUPS
    ]
    existing = bool(present_users or any(present_lookups))
    if existing:
        if len(present_users) != 3 or not all(present_lookups):
            raise SeedDiscrepancy("Demo fixture is incomplete or collides")
        for user in present_users:
            if (
                user.ref not in GRANTS
                or user.username != user.ref
                or user.issuer != "qualitytrack-local"
                or user.subject != user.ref
                or user.display_name != _display_name(user.ref)
                or not user.active
                or not user.password_hash.startswith("$argon2id$")
            ):
                raise SeedDiscrepancy("Demo identity differs from fixture")
            actual = set(
                session.execute(
                    select(Permission.operation, Permission.scope).where(
                        Permission.user_ref == user.ref
                    )
                ).all()
            )
            if actual != {(operation, "plant") for operation in GRANTS[user.ref]}:
                raise SeedDiscrepancy("Demo grant set differs from fixture")
        for row, (_, code, label) in zip(present_lookups, LOOKUPS):
            if (
                row.id != lookup_id(code)
                or row.code != code
                or row.label != label
                or row.retired
                or (isinstance(row, DefectType) and row.revision != 1)
            ):
                raise SeedDiscrepancy("Demo lookup differs from fixture")
        return
    if any(not passwords.get(ref) for ref in GRANTS):
        raise SeedDiscrepancy("Secure per-user password input is required")
    for ref in GRANTS:
        session.add(
            User(
                ref=ref,
                issuer="qualitytrack-local",
                subject=ref,
                username=ref,
                display_name=_display_name(ref),
                password_hash=HASHER.hash(passwords[ref]),
                active=True,
            )
        )
    session.flush()
    for ref, grants in GRANTS.items():
        for operation in grants:
            session.add(Permission(user_ref=ref, operation=operation, scope="plant"))
    for model, code, label in LOOKUPS:
        session.add(model(id=lookup_id(code), code=code, label=label, retired=False))
    session.flush()


def _display_name(ref):
    return {
        "sample-engineer": "Sample Engineer",
        "sample-supervisor": "Sample Supervisor",
        "sample-auditor": "Sample Auditor",
    }[ref]


# PUBLIC_INTERFACE
def main():
    """Seed a disposable demo using securely injected per-user passwords."""
    settings = Settings.from_env()
    passwords = {
        ref: os.environ.get("SEED_PASSWORD_" + ref.split("-")[1].upper(), "")
        for ref in GRANTS
    }
    engine = create_engine(settings.database_url)
    try:
        with Session(engine) as session, session.begin():
            seed_demo(session, settings.demo, passwords)
        print("Demo fixtures verified: 3 users, 6 lookups; explicit grants intact.")
    except Exception:
        raise SystemExit(
            "Demo seed refused; configuration or fixture discrepancy"
        ) from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
