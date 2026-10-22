"""Batch B HTTP registration; dependency ownership remains in the application."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.orm import Session

from qualitytrack import workflow as service
from qualitytrack.defects import defect_view
from qualitytrack.errors import Problem
from qualitytrack.schemas import DefectView
from qualitytrack.workflow_schemas import (
    ActionCreate,
    ActionEventPage,
    ActionPage,
    ActionTransition,
    ActionView,
    CauseCreate,
    CausePage,
    CauseView,
    DefectEventPage,
    DefectTransition,
    OwnerPage,
)


# PUBLIC_INTERFACE
def workflow_router(session_dependency, principal_dependency):
    """Build workflow routes with injected transaction and caller dependencies."""
    router = APIRouter(
        tags=["workflow"],
        responses={
            code: {"model": Problem, "description": description}
            for code, description in {
                400: "Malformed revision or cursor",
                403: "Operation forbidden",
                404: "Record not found",
                409: "State or gate conflict",
                412: "Stale parent revision",
                422: "Invalid fields or conditional evidence",
                428: "Parent revision required",
                503: "Persistence or policy unavailable",
            }.items()
        },
    )
    DB = Annotated[Session, Depends(session_dependency)]
    Caller = Annotated[object, Depends(principal_dependency)]
    Match = Annotated[str | None, Header(alias="If-Match")]
    Limit = Annotated[int, Query(ge=1, le=100)]

    def settings(request):
        return request.app.state.settings

    def etag(response, revision):
        response.headers["ETag"] = f'"{revision}"'

    def revision_header(request, value):
        # Pass an invalid token through normal authorization-before-token checks.
        return value if len(request.headers.getlist("if-match")) <= 1 else "multiple"

    # PUBLIC_INTERFACE
    @router.post(
        "/api/v1/defects/{defect_id}/causes",
        response_model=CauseView,
        status_code=201,
        summary="Record a preliminary cause",
        description="Parent-locked append; If-Match is neither required nor evaluated.",
    )
    def cause(
        defect_id: UUID,
        body: CauseCreate,
        response: Response,
        session: DB,
        caller: Caller,
    ):
        """Accept parent UUID/text; return saved cause and parent ETag."""
        result = service.add_cause(session, caller, defect_id, body)
        etag(response, result["revision"])
        return result

    # PUBLIC_INTERFACE
    @router.post(
        "/api/v1/defects/{defect_id}/transitions",
        response_model=DefectView,
        summary="Transition a defect",
        description="Require parent If-Match and recheck saved cause/closure gates.",
    )
    def defect_transition(
        defect_id: UUID,
        body: DefectTransition,
        request: Request,
        response: Response,
        session: DB,
        caller: Caller,
        if_match: Match = None,
    ):
        """Accept target/revision; return atomically updated defect and parent ETag."""
        row = service.transition_defect(
            session,
            caller,
            defect_id,
            body,
            revision_header(request, if_match),
            settings(request).demo,
        )
        etag(response, row.revision)
        return defect_view(row)

    # PUBLIC_INTERFACE
    @router.post(
        "/api/v1/defects/{defect_id}/actions",
        response_model=ActionView,
        status_code=201,
        summary="Assign corrective work",
        description="Explicit entry status; Closed rejects before business gates.",
    )
    def action(
        defect_id: UUID,
        body: ActionCreate,
        request: Request,
        response: Response,
        session: DB,
        caller: Caller,
    ):
        """Accept work/owner/date/status; return action and incremented parent ETag."""
        result = service.add_action(
            session, caller, defect_id, body, settings(request).demo
        )
        etag(response, result["revision"])
        return result

    # PUBLIC_INTERFACE
    @router.post(
        "/api/v1/actions/{action_id}/transitions",
        response_model=ActionView,
        summary="Transition corrective work",
        description="Parent If-Match, explicit grants and authority gates apply.",
    )
    def action_transition(
        action_id: UUID,
        body: ActionTransition,
        request: Request,
        response: Response,
        session: DB,
        caller: Caller,
        if_match: Match = None,
    ):
        """Accept target/evidence; retain history and return action with parent ETag."""
        result = service.transition_action(
            session,
            caller,
            action_id,
            body,
            revision_header(request, if_match),
            settings(request).demo,
        )
        etag(response, result["revision"])
        return result

    # PUBLIC_INTERFACE
    @router.get(
        "/api/v1/assignable-users",
        response_model=OwnerPage,
        summary="List eligible demo owners",
        description="Requires assignment grant, parent context and eligibility.",
    )
    def owners(defect_id: UUID, request: Request, session: DB, caller: Caller):
        """Accept defect_id query; return explicitly eligible active owners only."""
        return service.assignable_users(
            session, caller, defect_id, settings(request).demo
        )

    # PUBLIC_INTERFACE
    @router.get(
        "/api/v1/defects/{defect_id}/causes",
        response_model=CausePage,
        summary="Read recorded causes",
        description="Read grant required on every caller/parent-bound keyset page.",
    )
    def causes(
        defect_id: UUID,
        request: Request,
        session: DB,
        caller: Caller,
        cursor: str | None = None,
        limit: Limit = 50,
    ):
        """Accept parent/cursor/limit; return saved causes in instant/ID order."""
        return service.list_children(
            session, caller, settings(request), defect_id, "causes", cursor, limit
        )

    # PUBLIC_INTERFACE
    @router.get(
        "/api/v1/defects/{defect_id}/actions",
        response_model=ActionPage,
        summary="Read corrective work",
        description="Read grant required; pagination never grants mutation authority.",
    )
    def actions(
        defect_id: UUID,
        request: Request,
        session: DB,
        caller: Caller,
        cursor: str | None = None,
        limit: Limit = 50,
    ):
        """Accept parent/cursor/limit; return live actions ordered by stable ID."""
        return service.list_children(
            session, caller, settings(request), defect_id, "actions", cursor, limit
        )

    # PUBLIC_INTERFACE
    @router.get(
        "/api/v1/defects/{defect_id}/history",
        response_model=DefectEventPage,
        summary="Read defect transition evidence",
        description="Successful immutable events ordered by aggregate revision.",
    )
    def history(
        defect_id: UUID,
        request: Request,
        session: DB,
        caller: Caller,
        cursor: str | None = None,
        limit: Limit = 50,
    ):
        """Accept parent/cursor/limit; return retained defect transition history."""
        return service.list_children(
            session, caller, settings(request), defect_id, "history", cursor, limit
        )

    # PUBLIC_INTERFACE
    @router.get(
        "/api/v1/actions/{action_id}/history",
        response_model=ActionEventPage,
        summary="Read action evidence",
        description="Parent read grant required; all action cycles retained.",
    )
    def action_history(
        action_id: UUID,
        request: Request,
        session: DB,
        caller: Caller,
        cursor: str | None = None,
        limit: Limit = 50,
    ):
        """Accept action/cursor/limit; return events with parent resolved through FK."""
        return service.list_children(
            session,
            caller,
            settings(request),
            action_id,
            "action-history",
            cursor,
            limit,
        )

    return router
