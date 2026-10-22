"""Regression coverage for required public frontend setup documentation."""

from pathlib import Path


# PUBLIC_INTERFACE
def test_frontend_api_base_example_and_readme():
    """The example and setup guide must supply the required same-origin value."""
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    values = dict(
        line.split("=", 1)
        for line in (frontend / ".env.example").read_text().splitlines()
        if line and not line.startswith("#")
    )
    assert values["VITE_API_BASE_URL"] == "/api/v1"
    readme = (frontend / "README.md").read_text()
    assert "VITE_API_BASE_URL=/api/v1" in readme
    assert "no implicit fallback" in readme
