"""Version matching for semver constraints.

This module provides version constraint matching for service discovery,
supporting npm-style semver constraints (^, ~, ranges, wildcards).
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import semver

if TYPE_CHECKING:
    from registry.models import ServiceInstance


class VersionConstraintError(Exception):
    """Raised when a version or constraint is invalid."""

    pass


class VersionMatcher:
    """Matches versions against semver constraints.

    Supports:
    - Exact versions: 1.2.3
    - Caret ranges: ^1.2.3 (>=1.2.3 <2.0.0)
    - Tilde ranges: ~1.2.3 (>=1.2.3 <1.3.0)
    - Comparisons: >=1.0.0, <2.0.0, >=1.0.0 <2.0.0
    - Wildcards: *, 1.*, 1.2.*

    Usage:
        matcher = VersionMatcher()

        # Check if version matches constraint
        if matcher.matches("1.5.0", "^1.0.0"):
            print("Version matches!")

        # Filter instances by version
        matching = matcher.filter_by_version(instances, "^1.0.0")
    """

    # Patterns for parsing constraints
    CARET_PATTERN = re.compile(r"^\^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.-]+)?$")
    TILDE_PATTERN = re.compile(r"^~(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.-]+)?$")
    RANGE_PATTERN = re.compile(r"^(>=?|<=?|=)(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?)$")
    WILDCARD_MAJOR = re.compile(r"^\*$")
    WILDCARD_MINOR = re.compile(r"^(\d+)\.\*$")
    WILDCARD_PATCH = re.compile(r"^(\d+)\.(\d+)\.\*$")
    EXACT_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$")

    def __init__(self, include_prerelease: bool = False):
        """Initialize version matcher.

        Args:
            include_prerelease: Whether to include prerelease versions in matching.
        """
        self.include_prerelease = include_prerelease

    def matches(self, version: str, constraint: str) -> bool:
        """Check if a version matches a constraint.

        Args:
            version: Semver version string (e.g., "1.2.3").
            constraint: Version constraint (e.g., "^1.0.0", "~1.2.0", ">=1.0.0 <2.0.0").

        Returns:
            True if version matches constraint, False otherwise.

        Raises:
            VersionConstraintError: If version or constraint is invalid.
        """
        # Validate and parse version
        try:
            parsed_version = semver.Version.parse(version)
        except ValueError as e:
            raise VersionConstraintError(f"Invalid version '{version}': {e}") from e

        # Handle wildcard constraints
        if self.WILDCARD_MAJOR.match(constraint):
            return True

        if match := self.WILDCARD_MINOR.match(constraint):
            major = int(match.group(1))
            return parsed_version.major == major

        if match := self.WILDCARD_PATCH.match(constraint):
            major = int(match.group(1))
            minor = int(match.group(2))
            return parsed_version.major == major and parsed_version.minor == minor

        # Handle caret constraint (^)
        if match := self.CARET_PATTERN.match(constraint):
            return self._match_caret(parsed_version, match)

        # Handle tilde constraint (~)
        if match := self.TILDE_PATTERN.match(constraint):
            return self._match_tilde(parsed_version, match)

        # Handle range constraints (>=, <=, >, <)
        if " " in constraint:
            # Combined range like ">=1.0.0 <2.0.0"
            return self._match_combined_range(parsed_version, constraint)

        if match := self.RANGE_PATTERN.match(constraint):
            return self._match_single_range(parsed_version, match.group(1), match.group(2))

        # Handle exact version match
        if self.EXACT_VERSION.match(constraint):
            try:
                constraint_version = semver.Version.parse(constraint)
                return parsed_version == constraint_version
            except ValueError as e:
                raise VersionConstraintError(f"Invalid constraint '{constraint}': {e}") from e

        raise VersionConstraintError(
            f"Invalid constraint format: '{constraint}'. "
            "Expected: ^x.y.z, ~x.y.z, >=x.y.z, x.y.z, *, x.*, or x.y.*"
        )

    def _match_caret(self, version: semver.Version, match: re.Match) -> bool:
        """Match caret constraint (^x.y.z).

        ^x.y.z allows changes that do not modify the left-most non-zero digit:
        - ^1.2.3 := >=1.2.3 <2.0.0
        - ^0.2.3 := >=0.2.3 <0.3.0
        - ^0.0.3 := >=0.0.3 <0.0.4
        """
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        prerelease = match.group(4)[1:] if match.group(4) else None

        min_version = semver.Version(major, minor, patch, prerelease)

        if major > 0:
            # ^1.2.3 := >=1.2.3 <2.0.0
            max_version = semver.Version(major + 1, 0, 0)
        elif minor > 0:
            # ^0.2.3 := >=0.2.3 <0.3.0
            max_version = semver.Version(0, minor + 1, 0)
        else:
            # ^0.0.3 := >=0.0.3 <0.0.4
            max_version = semver.Version(0, 0, patch + 1)

        return version >= min_version and version < max_version

    def _match_tilde(self, version: semver.Version, match: re.Match) -> bool:
        """Match tilde constraint (~x.y.z).

        ~x.y.z allows patch-level changes:
        - ~1.2.3 := >=1.2.3 <1.3.0
        """
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        prerelease = match.group(4)[1:] if match.group(4) else None

        min_version = semver.Version(major, minor, patch, prerelease)
        max_version = semver.Version(major, minor + 1, 0)

        return version >= min_version and version < max_version

    def _match_single_range(
        self, version: semver.Version, operator: str, constraint_version: str
    ) -> bool:
        """Match single range constraint (>=x.y.z, <x.y.z, etc.)."""
        try:
            target = semver.Version.parse(constraint_version)
        except ValueError as e:
            raise VersionConstraintError(f"Invalid version in constraint: {e}") from e

        if operator == ">=":
            return version >= target
        elif operator == ">":
            return version > target
        elif operator == "<=":
            return version <= target
        elif operator == "<":
            return version < target
        elif operator == "=":
            return version == target
        else:
            raise VersionConstraintError(f"Unknown operator: {operator}")

    def _match_combined_range(self, version: semver.Version, constraint: str) -> bool:
        """Match combined range constraint (>=x.y.z <a.b.c)."""
        parts = constraint.split()
        for part in parts:
            if match := self.RANGE_PATTERN.match(part):
                if not self._match_single_range(version, match.group(1), match.group(2)):
                    return False
            else:
                raise VersionConstraintError(f"Invalid part in combined constraint: '{part}'")
        return True

    def filter_by_version(
        self,
        instances: list[ServiceInstance],
        constraint: str | None,
    ) -> list[ServiceInstance]:
        """Filter service instances by version constraint.

        Args:
            instances: List of service instances to filter.
            constraint: Version constraint string, or None for no filtering.

        Returns:
            List of instances matching the constraint.

        Raises:
            VersionConstraintError: If constraint is invalid.
        """
        if constraint is None:
            return list(instances)

        result = []
        for instance in instances:
            try:
                if self.matches(instance.version, constraint):
                    result.append(instance)
            except VersionConstraintError:
                # Skip instances with invalid versions
                continue

        return result

    def compare(self, v1: str, v2: str) -> int:
        """Compare two versions.

        Args:
            v1: First version string.
            v2: Second version string.

        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2

        Raises:
            VersionConstraintError: If either version is invalid.
        """
        try:
            version1 = semver.Version.parse(v1)
            version2 = semver.Version.parse(v2)
        except ValueError as e:
            raise VersionConstraintError(f"Invalid version: {e}") from e

        return version1.compare(version2)

    def is_valid_version(self, version: str) -> bool:
        """Check if a string is a valid semver version.

        Args:
            version: Version string to validate.

        Returns:
            True if valid, False otherwise.
        """
        try:
            semver.Version.parse(version)
            return True
        except ValueError:
            return False

    def get_highest_version(self, versions: list[str]) -> str | None:
        """Get the highest version from a list.

        Args:
            versions: List of version strings.

        Returns:
            Highest version string, or None if list is empty.

        Raises:
            VersionConstraintError: If any version is invalid.
        """
        if not versions:
            return None

        parsed = []
        for v in versions:
            try:
                parsed.append((semver.Version.parse(v), v))
            except ValueError as e:
                raise VersionConstraintError(f"Invalid version '{v}': {e}") from e

        parsed.sort(key=lambda x: x[0], reverse=True)
        return parsed[0][1]
