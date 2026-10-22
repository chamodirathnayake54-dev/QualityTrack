"""FastAPI entry point for Batch A only."""

from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from qualitytrack.config import Settings
from qualitytrack.defects import capture_defect, defect_view, get_defect, list_defects
from qualitytrack.errors import Failure, Problem, problem_response
from qualitytrack.models import DefectType, ProductionLine, Shift
from qualitytrack.schemas import (
    Capture,
    DefectPage,
    DefectView,
    Filters,
    LoginRequest,
    LookupPage,
    MeView,
    TokenResponse,
    TypePage,
)
from qualitytrack.security import issue_token, load_principal, require, verify_token

ERRORS = {
    status: {"model": Problem, "description": description}
    for status, description in {
        400: "Malformed request or cursor",
        401: "Authentication required",
        403: "Explicit grant absent or inactive caller",
        404: "Record not found",
        409: "Configured lookup unavailable",
        422: "Invalid fields or unsupported photo part",
        503: "Persistence unavailable",
    }.items()
}


# PUBLIC_INTERFACE
def create_app(settings: Settings | None = None, session_factory=None):
    """Build the API; optional settings/session injection supports isolated tests."""

    @asynccontextmanager
    async def lifespan(application):
        resolved = settings or Settings.from_env()
        application.state.settings = resolved
        engine = None
        if session_factory is None:
            engine = create_engine(resolved.database_url, pool_pre_ping=True)
            application.state.sessions = sessionmaker(engine, expire_on_commit=False)
        else:
            application.state.sessions = session_factory
        try:
            yield
        finally:
            if engine:
                engine.dispose()

    application = FastAPI(
        title="QualityTrack",
        description="Single-plant demo API. Batch A only; photo upload disabled.",
        version="0.1.0",
        openapi_tags=[
            {"name": "identity", "description": "Local demo identity"},
            {"name": "lookups", "description": "Active capture choices"},
            {
                "name": "defects",
                "description": "Photo-free capture and permitted reads",
            },
        ],
        lifespan=lifespan,
        responses=ERRORS,
    )

    @application.exception_handler(Failure)
    async def failure_handler(request, exc):
        return problem_response(exc.problem)

    @application.exception_handler(RequestValidationError)
    async def validation_handler(request, exc):
        # Never return Pydantic's input/ctx values, especially login passwords.
        fields = {
            ".".join(
                str(part) for part in error["loc"] if part != "body"
            ): "Required or invalid value"
            for error in exc.errors()
        }
        return problem_response(
            Problem(
                status=422,
                code="validation_failed",
                title="Input is invalid",
                field_errors=fields,
            )
        )

    @application.exception_handler(SQLAlchemyError)
    async def database_handler(request, exc):
        return problem_response(
            Problem(
                status=503, code="persistence_unavailable", title="Service unavailable"
            )
        )

    @application.exception_handler(HTTPException)
    async def http_handler(request, exc):
        return problem_response(
            Problem(
                status=exc.status_code, code="request_failed", title="Request failed"
            )
        )

    @application.exception_handler(Exception)
    async def internal_handler(request, exc):
        return problem_response(
            Problem(
                status=500, code="internal_failure", title="Request could not complete"
            )
        )

    def session_dependency(request: Request):
        with request.app.state.sessions() as session:
            # Commit only after a successful handler; rollback on every rejection.
            with session.begin():
                yield session

    def principal_dependency(
        request: Request, session: Annotated[Session, Depends(session_dependency)]
    ):
        header = request.headers.get("Authorization", "")
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise Failure(401, "invalid_token", "Authentication is required")
        ref = verify_token(parts[1], request.app.state.settings)
        return load_principal(session, ref)

    DB = Annotated[Session, Depends(session_dependency)]
    Caller = Annotated[object, Depends(principal_dependency)]

    @application.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        return response

    # PUBLIC_INTERFACE
    @application.post(
        "/api/v1/auth/login",
        tags=["identity"],
        response_model=TokenResponse,
        summary="Authenticate a local demo user",
        description="Verify Argon2id credentials and issue a 3600-second HS256 token.",
    )
    def login(body: LoginRequest, request: Request, session: DB):
        """Accept username/password and return bearer token metadata, never a hash."""
        return TokenResponse(
            access_token=issue_token(
                session, request.app.state.settings, body.username, body.password
            )
        )

    # PUBLIC_INTERFACE
    @application.get(
        "/api/v1/me",
        tags=["identity"],
        response_model=MeView,
        summary="Read current caller",
        description="Return active caller identity and current persisted plant grants.",
    )
    def me(request: Request, caller: Caller):
        """Return caller-only identity, explicit permissions and plant timezone."""
        return MeView(
            ref=caller.ref,
            display_name=caller.display_name,
            permissions=sorted(caller.permissions),
            plant_zone=request.app.state.settings.plant_zone,
        )

    def choices(model, session, caller):
        require(caller, "defect.capture")
        rows = session.scalars(
            select(model).where(model.retired.is_(False)).order_by(model.code)
        )
        items = []
        for row in rows:
            item = {"id": row.id, "code": row.code, "label": row.label}
            if model is DefectType:
                item.update(retired=row.retired, revision=row.revision)
            items.append(item)
        return {"items": items, "next_cursor": None}

    # PUBLIC_INTERFACE
    @application.get(
        "/api/v1/production-lines",
        tags=["lookups"],
        response_model=LookupPage,
        summary="List active production lines",
        description="Requires an explicit capture grant; excludes retired choices.",
    )
    def production_lines(session: DB, caller: Caller):
        """Return active line IDs/codes/labels for permitted capture."""
        return choices(ProductionLine, session, caller)

    # PUBLIC_INTERFACE
    @application.get(
        "/api/v1/shifts",
        tags=["lookups"],
        response_model=LookupPage,
        summary="List active shifts",
        description="Requires an explicit capture grant; excludes retired choices.",
    )
    def shifts(session: DB, caller: Caller):
        """Return active shift IDs/codes/labels for permitted capture."""
        return choices(Shift, session, caller)

    # PUBLIC_INTERFACE
    @application.get(
        "/api/v1/defect-types",
        tags=["lookups"],
        response_model=TypePage,
        summary="List selectable active types",
        description="Capture access does not imply configuration authority.",
    )
    def types(session: DB, caller: Caller):
        """Return active types and their configuration revisions."""
        return choices(DefectType, session, caller)

    # PUBLIC_INTERFACE
    @application.post(
        "/api/v1/defects",
        tags=["defects"],
        response_model=DefectView,
        status_code=201,
        summary="Capture a photo-free defect",
        description="Multipart capture JSON part only. Any photo part is rejected.",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "multipart/form-data": {
                        "schema": {
                            "type": "object",
                            "required": ["capture"],
                            "properties": {
                                "capture": {
                                    "type": "string",
                                    "description": "JSON-encoded Capture object",
                                }
                            },
                            "additionalProperties": False,
                        }
                    }
                },
            }
        },
    )
    async def capture(
        request: Request, response: Response, session: DB, caller: Caller
    ):
        """Accept one capture JSON part; return committed context with an ETag."""
        require(caller, "defect.capture")
        if (
            request.headers.get("content-type", "").split(";")[0]
            != "multipart/form-data"
        ):
            raise Failure(400, "invalid_multipart", "Multipart capture is required")
        async with request.form(max_files=1, max_fields=2) as form:
            if "photo" in form:
                raise Failure(
                    422, "photo_not_supported", "Photo parts are not supported"
                )
            if set(form.keys()) != {"capture"} or len(form.getlist("capture")) != 1:
                raise Failure(422, "invalid_parts", "Supply one capture JSON part")
            raw = form["capture"]
            if not isinstance(raw, str):
                raw = await raw.read()
            try:
                body = Capture.model_validate_json(raw)
            except ValidationError as exc:
                fields = {
                    ".".join(
                        str(part) for part in error["loc"]
                    ): "Required or invalid value"
                    for error in exc.errors()
                }
                raise Failure(
                    422, "capture_validation_failed", "Capture input is invalid", fields
                ) from None
        row = await run_in_threadpool(capture_defect, session, caller, body)
        response.headers["ETag"] = f'"{row.revision}"'
        return defect_view(row)

    # PUBLIC_INTERFACE
    @application.get(
        "/api/v1/defects",
        tags=["defects"],
        response_model=DefectPage,
        summary="List permitted defects",
        description="AND filters and caller-bound signed descending keyset pagination.",
    )
    def collection(
        request: Request,
        session: DB,
        caller: Caller,
        status: str | None = None,
        severity: str | None = None,
        production_line_id: str | None = None,
        shift_id: str | None = None,
        defect_type_id: str | None = None,
        part_number: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        cursor: str | None = None,
        limit: int = Query(default=50, ge=1, le=100),
    ):
        """Accept filters/cursor/limit; authorize and return a live page."""
        require(caller, "defect.read")
        try:
            filters = Filters(
                status=status,
                severity=severity,
                production_line_id=production_line_id,
                shift_id=shift_id,
                defect_type_id=defect_type_id,
                part_number=part_number,
                start_date=start_date,
                end_date=end_date,
            )
        except ValidationError:
            raise Failure(422, "invalid_filters", "Filters are invalid") from None
        return list_defects(
            session, caller, request.app.state.settings, filters, cursor, limit
        )

    # PUBLIC_INTERFACE
    @application.get(
        "/api/v1/defects/{defect_id}",
        tags=["defects"],
        response_model=DefectView,
        summary="Read a permitted defect",
        description="Read grant is checked before record existence is disclosed.",
    )
    def record(defect_id: UUID, response: Response, session: DB, caller: Caller):
        """Accept a defect UUID and return its captured context with aggregate ETag."""
        row = get_defect(session, caller, defect_id)
        response.headers["ETag"] = f'"{row.revision}"'
        return defect_view(row)

    return application


app = create_app()
