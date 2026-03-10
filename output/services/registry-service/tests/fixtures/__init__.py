"""Test fixtures for registry service tests."""
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent
MANIFESTS_DIR = FIXTURES_DIR / "manifests"


def get_manifest_path(name: str) -> Path:
    """Get path to a manifest fixture file."""
    return MANIFESTS_DIR / f"{name}.yaml"
