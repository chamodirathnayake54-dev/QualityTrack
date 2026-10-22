"""Environment-only configuration; never loads .env files."""

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


# PUBLIC_INTERFACE
@dataclass(frozen=True)
class Settings:
    """Validated deployment settings. Secrets must be supplied by the operator."""

    database_url: str
    secret: str
    plant_zone: str
    demo: bool

    # PUBLIC_INTERFACE
    @classmethod
    def from_env(cls):
        """Read injected environment values, rejecting unsafe configuration."""
        # Request these environment variables from the user; never read .env.
        demo = os.environ.get("QT_DEMO_MODE") == "true"
        zone = os.environ.get("PLANT_TIMEZONE", "Etc/UTC" if demo else "")
        try:
            ZoneInfo(zone)
        except (ValueError, ZoneInfoNotFoundError):
            raise RuntimeError("Plant timezone configuration unavailable") from None
        url = os.environ.get("DATABASE_URL", "")
        secret = os.environ.get("JWT_SECRET_KEY", "")
        if not url.startswith("postgresql+psycopg://") or len(secret.encode()) < 32:
            raise RuntimeError("Database or signing configuration unavailable")
        return cls(url, secret, zone, demo)
