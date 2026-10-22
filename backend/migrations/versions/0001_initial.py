"""Full LLD ERD initial schema, frozen in migrations/initial_schema.py."""

import importlib.util
from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _metadata():
    path = Path(__file__).resolve().parents[1] / "initial_schema.py"
    spec = importlib.util.spec_from_file_location("qt_initial_schema", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Base.metadata


# PUBLIC_INTERFACE
def upgrade():
    """Create the complete frozen initial ERD in dependency order."""
    _metadata().create_all(op.get_bind(), checkfirst=False)


# PUBLIC_INTERFACE
def downgrade():
    """Remove the initial schema only on an explicitly disposable database."""
    _metadata().drop_all(op.get_bind(), checkfirst=False)
