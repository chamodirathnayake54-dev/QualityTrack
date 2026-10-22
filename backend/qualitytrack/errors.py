"""Safe HTTP error representation."""

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# PUBLIC_INTERFACE
class Problem(BaseModel):
    """Public error envelope; never contains submitted content."""

    type: str = Field(default="about:blank", description="Problem type URI")
    title: str = Field(description="Safe human-readable error")
    status: int = Field(description="HTTP status")
    code: str = Field(description="Stable error code")
    field_errors: dict[str, str] | None = Field(
        default=None, description="Safe field-specific feedback"
    )


# PUBLIC_INTERFACE
class Failure(Exception):
    """Expected rejection without protected details."""

    # PUBLIC_INTERFACE
    def __init__(self, status: int, code: str, title: str, fields=None):
        """Initialize a safe status, code, title, and optional field errors."""
        self.problem = Problem(
            status=status, code=code, title=title, field_errors=fields
        )


# PUBLIC_INTERFACE
def problem_response(problem: Problem):
    """Return an RFC-style private, non-cacheable Problem response."""
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
        headers={"Cache-Control": "private, no-store"},
    )
