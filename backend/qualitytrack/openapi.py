"""Cross-cutting declarations for the actual runtime HTTP contract."""

from fastapi.openapi.utils import get_openapi

from qualitytrack.schemas import Capture, Filters

_PROBLEMS = {
    400: "Malformed request, revision or cursor",
    401: "Missing or invalid authentication",
    403: "Inactive caller or explicit operation grant absent",
    404: "Record not found",
    409: "State/gate conflict, defect_closed or lookup unavailable",
    412: "Well-formed stale revision",
    422: "Required, invalid or conditional field",
    428: "If-Match required for this transition",
    500: "Internal/render failure; no partial protected output",
    503: "Persistence, calendar or authority policy unavailable",
}


# PUBLIC_INTERFACE
def install_openapi(application):
    """Install generated declarations without changing runtime authorization rules."""

    def schema():
        if application.openapi_schema:
            return application.openapi_schema
        result = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
            tags=application.openapi_tags,
        )
        components = result["components"]
        components.setdefault("securitySchemes", {})["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Local HS256 token; persisted grants checked per request",
        }
        capture = Capture.model_json_schema(ref_template="#/components/schemas/{model}")
        capture.pop("$defs", None)
        components["schemas"]["Capture"] = capture
        filters = Filters.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )["properties"]
        for name, model in components["schemas"].items():
            # Output defaults are still always serialized by the runtime.
            if name.endswith(("View", "Page", "Response")):
                model["required"] = list(model.get("properties", {}))
        for path, methods in result["paths"].items():
            for method, operation in methods.items():
                if method not in {"get", "post"}:
                    continue
                transition = path.endswith(("/transitions", "/retire"))
                operation["security"] = (
                    [] if path.endswith("/auth/login") else [{"BearerAuth": []}]
                )
                for status, description in _PROBLEMS.items():
                    if status in {412, 428} and not transition:
                        continue
                    operation["responses"][str(status)] = {
                        "description": description,
                        "content": {
                            "application/problem+json": {
                                "schema": {"$ref": "#/components/schemas/Problem"}
                            }
                        },
                    }
                for parameter in operation.get("parameters", []):
                    if (
                        path == "/api/v1/defects"
                        and method == "get"
                        and parameter["name"] in filters
                    ):
                        parameter["schema"] = filters[parameter["name"]]
                        parameter["description"] = (
                            "Optional AND filter. Dates are inclusive plant-local "
                            "dates; start_date and end_date must be supplied together."
                        )
                    if parameter["in"] == "header" and parameter["name"] == "If-Match":
                        parameter.update(
                            required=True,
                            schema={"type": "string", "pattern": r'^"[1-9][0-9]*"$'},
                            description=(
                                "Required after authorization: one strong quoted "
                                'positive revision, e.g. "7". Missing 428, '
                                "malformed 400, stale 412. Actions use the "
                                "parent defect revision."
                            ),
                        )
                success = operation["responses"].get(
                    "201"
                    if method == "post"
                    and path.endswith(("/defects", "/causes", "/actions"))
                    else "200"
                )
                if success:
                    headers = success.setdefault("headers", {})
                    headers["Cache-Control"] = {
                        "description": "Protected responses are private and not stored",
                        "schema": {"type": "string", "const": "private, no-store"},
                    }
                    if (method == "post" and path != "/api/v1/auth/login") or (
                        method == "get" and path == "/api/v1/defects/{defect_id}"
                    ):
                        headers["ETag"] = {
                            "description": "Quoted type revision for retirement; "
                            "otherwise parent revision",
                            "schema": {"type": "string", "pattern": r'^"[1-9][0-9]*"$'},
                        }
        result["paths"]["/api/v1/defects"]["post"]["description"] += (
            " The capture part is JSON matching #/components/schemas/Capture. "
            "If-Match is not evaluated on capture, cause or action creation."
        )
        multipart = result["paths"]["/api/v1/defects"]["post"]["requestBody"][
            "content"
        ]["multipart/form-data"]
        multipart["schema"]["properties"]["capture"].update(
            contentMediaType="application/json",
            contentSchema={"$ref": "#/components/schemas/Capture"},
        )
        application.openapi_schema = result
        return result

    application.openapi = schema
