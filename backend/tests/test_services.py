"""Database-free route and detail contracts for Batch A."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from qualitytrack.defects import get_defect
from qualitytrack.errors import Failure
from qualitytrack.main import create_app
from qualitytrack.models import DefectType, ProductionLine, Shift
from qualitytrack.security import Principal


def _endpoint(path):
    return next(route.endpoint for route in create_app().routes if route.path == path)


@pytest.mark.parametrize(
    "path,model",
    [
        ("/api/v1/production-lines", ProductionLine),
        ("/api/v1/shifts", Shift),
        ("/api/v1/defect-types", DefectType),
    ],
)
@pytest.mark.parametrize(
    "case", ["denied", "empty", "projection", "active_predicate", "code_order"]
)
# PUBLIC_INTERFACE
def test_lookup_route_contract(path, model, case):
    """Each lookup requires capture, filters active rows and projects safe fields."""
    session = Mock()
    principal = Principal(
        "unit", "Unit", frozenset() if case == "denied" else {"defect.capture"}
    )
    row = SimpleNamespace(
        id=uuid4(),
        code="UNIT",
        label="Unit label",
        retired=False,
        revision=7,
        password_hash="must-not-be-projected",
    )
    session.scalars.return_value = [] if case == "empty" else [row]
    endpoint = _endpoint(path)
    if case == "denied":
        with pytest.raises(Failure) as caught:
            endpoint(session, principal)
        assert caught.value.problem.status == 403
        session.scalars.assert_not_called()
        return
    result = endpoint(session, principal)
    assert result["next_cursor"] is None
    if case == "empty":
        assert result["items"] == []
    elif case == "projection":
        expected = {"id": row.id, "code": row.code, "label": row.label}
        if model is DefectType:
            expected.update(retired=False, revision=7)
        assert result["items"] == [expected]
    elif case == "active_predicate":
        query = str(session.scalars.call_args.args[0])
        assert f"{model.__tablename__}.retired IS false" in query
    elif case == "code_order":
        query = str(session.scalars.call_args.args[0])
        assert f"ORDER BY {model.__tablename__}.code" in query


@pytest.mark.parametrize(
    "case", ["caller_only", "sorted_grants", "zone", "empty_grants", "no_credentials"]
)
# PUBLIC_INTERFACE
def test_me_route_contract(case):
    """Caller projection never invents permissions or exposes credential material."""
    permissions = frozenset() if case == "empty_grants" else {"z.read", "a.read"}
    caller = Principal("unit-ref", "Unit Name", permissions)
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                settings=SimpleNamespace(plant_zone="America/New_York")
            )
        )
    )
    result = _endpoint("/api/v1/me")(request, caller).model_dump()
    if case == "caller_only":
        assert result["ref"] == caller.ref
        assert result["display_name"] == caller.display_name
        assert result["scope"] == "plant"
    elif case == "sorted_grants":
        assert result["permissions"] == ["a.read", "z.read"]
    elif case == "zone":
        assert result["plant_zone"] == "America/New_York"
    elif case == "empty_grants":
        assert result["permissions"] == []
    elif case == "no_credentials":
        assert set(result) == {
            "ref",
            "display_name",
            "scope",
            "permissions",
            "plant_zone",
        }


@pytest.mark.parametrize(
    "case", ["denied", "missing", "found", "id_bound", "no_capture_required"]
)
# PUBLIC_INTERFACE
def test_detail_service_contract(case):
    """Read grant precedes existence checks and resolves exactly the requested ID."""
    session = Mock()
    identifier = uuid4()
    permissions = frozenset() if case == "denied" else {"defect.read"}
    principal = Principal("unit-ref", "Unit", permissions)
    row = SimpleNamespace(id=identifier)
    session.get.return_value = None if case == "missing" else row
    if case in {"denied", "missing"}:
        with pytest.raises(Failure) as caught:
            get_defect(session, principal, identifier)
        assert caught.value.problem.status == (403 if case == "denied" else 404)
        if case == "denied":
            session.get.assert_not_called()
    else:
        assert get_defect(session, principal, identifier) is row
        assert session.get.call_args.args[1] == identifier
        session.get.assert_called_once()
