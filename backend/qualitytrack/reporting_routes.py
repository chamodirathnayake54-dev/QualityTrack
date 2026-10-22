"""Batch C HTTP routes; evidence rendering uses separate short transactions."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.orm import Session

from qualitytrack.evidence import export_record
from qualitytrack.reporting import (
    EmptyCommand,
    OverduePage,
    overdue_actions,
    retire_type,
)
from qualitytrack.schemas import TypeView


# PUBLIC_INTERFACE
def reporting_router(session_dependency, principal_dependency):
    """Build overdue, photo-free export and type-retirement routes."""
    router = APIRouter(tags=["reporting"])
    DB = Annotated[Session, Depends(session_dependency)]
    Caller = Annotated[object, Depends(principal_dependency)]

    # PUBLIC_INTERFACE
    @router.get(
        "/api/v1/overdue-actions",
        response_model=OverduePage,
        summary="Read plant-local overdue work",
        description="Read grant required; signed cursors pin local date and zone, "
        "while statuses and current grants remain live. Due today is excluded.",
    )
    def overdue(
        request: Request,
        session: DB,
        caller: Caller,
        cursor: str | None = None,
        limit: int = Query(50, ge=1, le=100),
    ):
        """Accept cursor/limit and return overdue work with evaluation date/zone."""
        return overdue_actions(
            session, caller, request.app.state.settings, cursor, limit
        )

    # PUBLIC_INTERFACE
    @router.post(
        "/api/v1/defect-types/{type_id}/retire",
        response_model=TypeView,
        tags=["lookups"],
        summary="Retire an active defect type",
        description="Explicit type.retire grant and one strong quoted type revision "
        "required. Uses capture's type lock; preserves historical captured labels.",
    )
    def retire(
        type_id: UUID,
        body: EmptyCommand,
        request: Request,
        response: Response,
        session: DB,
        caller: Caller,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ):
        """Accept type UUID, empty JSON and If-Match; return retired type and ETag."""
        header = (
            if_match if len(request.headers.getlist("if-match")) <= 1 else "multiple"
        )
        result = retire_type(session, caller, type_id, header)
        response.headers["ETag"] = f'"{result["revision"]}"'
        return result

    # PUBLIC_INTERFACE
    @router.get(
        "/api/v1/defects/{defect_id}/audit.pdf",
        response_class=Response,
        summary="Export complete photo-free evidence",
        description="Both current read and export grants required. Read-only "
        "repeatable-read snapshot includes every child; render fully before a final "
        "active/grant check. No photo handling, remote assets or public archive.",
        responses={
            200: {
                "description": "Complete A4 Latin-text audit PDF",
                "content": {
                    "application/pdf": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                },
                "headers": {"Content-Disposition": {"schema": {"type": "string"}}},
            },
        },
    )
    def audit(defect_id: UUID, request: Request, session: DB, caller: Caller):
        """Accept defect UUID; return complete protected PDF or a safe Problem."""
        # Authentication performed only reads. Release that transaction too;
        # export owns its snapshot and fresh final authorization transactions.
        session.rollback()
        content = export_record(
            request.app.state.sessions,
            caller.ref,
            defect_id,
            request.app.state.settings,
        )
        return Response(
            content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="defect-{defect_id}.pdf"'
            },
        )

    return router
