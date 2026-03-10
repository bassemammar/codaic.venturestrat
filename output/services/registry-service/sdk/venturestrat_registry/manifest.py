"""Manifest loading utilities.

Load and parse service manifest files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ManifestLoader:
    """Load service manifests from YAML files.

    Provides static methods for loading and validating manifest files.

    Usage:
        manifest = ManifestLoader.load("manifest.yaml")
        print(manifest["name"])
        print(manifest["version"])
    """

    @staticmethod
    def load(path: Path | str) -> dict[str, Any]:
        """Load manifest from YAML file.

        Args:
            path: Path to manifest.yaml file.

        Returns:
            Parsed manifest as dictionary.

        Raises:
            FileNotFoundError: If manifest file doesn't exist.
            ValueError: If manifest is not valid YAML.
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")

        try:
            with open(path) as f:
                manifest = yaml.safe_load(f)

            if not isinstance(manifest, dict):
                raise ValueError(f"Manifest must be a YAML object: {path}")

            # Validate required fields
            if not manifest.get("name"):
                raise ValueError("Manifest must have 'name' field")

            if not manifest.get("version"):
                raise ValueError("Manifest must have 'version' field")

            return manifest

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in manifest: {e}") from e

    @staticmethod
    def validate(manifest: dict[str, Any]) -> list[str]:
        """Validate manifest structure.

        Args:
            manifest: Parsed manifest dictionary.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Required fields
        if not manifest.get("name"):
            errors.append("Missing required field: name")

        if not manifest.get("version"):
            errors.append("Missing required field: version")

        # Validate version format (basic semver check)
        version = manifest.get("version", "")
        if version and not ManifestLoader._is_valid_version(version):
            errors.append(f"Invalid version format: {version}")

        # Validate depends format
        for dep in manifest.get("depends", []):
            if "@" not in dep:
                errors.append(f"Invalid dependency format (missing @): {dep}")

        return errors

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """Check if version is valid semver format."""
        parts = version.split(".")
        if len(parts) < 2:
            return False

        try:
            for part in parts[:3]:
                # Remove prerelease suffix for validation
                clean_part = part.split("-")[0].split("+")[0]
                int(clean_part)
            return True
        except ValueError:
            return False
