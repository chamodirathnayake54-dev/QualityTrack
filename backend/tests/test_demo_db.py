"""Regression tests for platform-specific PostgreSQL 16 discovery."""

import os
from pathlib import Path

import pytest
from conftest import demo_db


# PUBLIC_INTERFACE
@pytest.mark.parametrize(
    "directory",
    [
        "/Library/PostgreSQL/16/bin",
        "/opt/homebrew/opt/postgresql@16/bin",
        "/usr/local/opt/postgresql@16/bin",
    ],
)
def test_macos_postgres_discovery(monkeypatch, directory):
    """Find each supported macOS installation only when its tools are executable."""
    monkeypatch.setattr(demo_db.sys, "platform", "darwin")
    monkeypatch.setattr(
        demo_db.os,
        "access",
        lambda path, mode: path.parent == Path(directory) and mode == os.X_OK,
    )
    assert demo_db._postgres_bin() == Path(directory)


# PUBLIC_INTERFACE
def test_linux_postgres_path_unchanged(monkeypatch):
    """Linux retains the original PostgreSQL 16 binary path."""
    monkeypatch.setattr(demo_db.sys, "platform", "linux")
    assert demo_db._postgres_bin() == Path("/usr/lib/postgresql/16/bin")


# PUBLIC_INTERFACE
def test_missing_macos_postgres_fails_on_use(monkeypatch):
    """Missing tools produce a useful error only when the helper needs them."""
    monkeypatch.setattr(demo_db.sys, "platform", "darwin")
    monkeypatch.setattr(demo_db.os, "access", lambda *_: False)
    with pytest.raises(RuntimeError, match="Install PostgreSQL 16"):
        demo_db._postgres_bin()
