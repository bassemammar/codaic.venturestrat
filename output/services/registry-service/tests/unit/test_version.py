"""Tests for VersionMatcher - TDD approach.

These tests define the expected behavior of semver version matching
for service discovery.
"""
import pytest
from registry.models import HealthStatus, Protocol, ServiceInstance
from registry.version import VersionConstraintError, VersionMatcher


class TestVersionMatcherExactMatch:
    """Tests for exact version matching."""

    def test_exact_match_same_version(self):
        """Exact version matches same version."""
        matcher = VersionMatcher()

        assert matcher.matches("1.0.0", "1.0.0") is True
        assert matcher.matches("2.3.4", "2.3.4") is True

    def test_exact_match_different_version(self):
        """Exact version does not match different version."""
        matcher = VersionMatcher()

        assert matcher.matches("1.0.0", "1.0.1") is False
        assert matcher.matches("1.0.0", "2.0.0") is False

    def test_exact_match_with_prerelease(self):
        """Exact match with prerelease versions."""
        matcher = VersionMatcher()

        assert matcher.matches("1.0.0-alpha", "1.0.0-alpha") is True
        assert matcher.matches("1.0.0-alpha", "1.0.0-beta") is False
        assert matcher.matches("1.0.0-alpha.1", "1.0.0-alpha.1") is True


class TestVersionMatcherCaretConstraint:
    """Tests for caret (^) version constraints.

    Caret allows changes that do not modify the left-most non-zero digit.
    ^1.2.3 := >=1.2.3 <2.0.0
    ^0.2.3 := >=0.2.3 <0.3.0
    ^0.0.3 := >=0.0.3 <0.0.4
    """

    def test_caret_major_version(self):
        """^1.0.0 allows any 1.x.x version."""
        matcher = VersionMatcher()

        # ^1.2.3 should match >=1.2.3 <2.0.0
        assert matcher.matches("1.2.3", "^1.2.3") is True
        assert matcher.matches("1.2.4", "^1.2.3") is True
        assert matcher.matches("1.3.0", "^1.2.3") is True
        assert matcher.matches("1.9.9", "^1.2.3") is True

        # Should not match
        assert matcher.matches("1.2.2", "^1.2.3") is False  # Below constraint
        assert matcher.matches("2.0.0", "^1.2.3") is False  # Major bump
        assert matcher.matches("0.9.9", "^1.2.3") is False  # Below major

    def test_caret_zero_major(self):
        """^0.2.0 only allows 0.2.x versions."""
        matcher = VersionMatcher()

        # ^0.2.3 should match >=0.2.3 <0.3.0
        assert matcher.matches("0.2.3", "^0.2.3") is True
        assert matcher.matches("0.2.9", "^0.2.3") is True

        # Should not match
        assert matcher.matches("0.2.2", "^0.2.3") is False
        assert matcher.matches("0.3.0", "^0.2.3") is False
        assert matcher.matches("1.0.0", "^0.2.3") is False

    def test_caret_zero_minor(self):
        """^0.0.3 only allows exact 0.0.3."""
        matcher = VersionMatcher()

        # ^0.0.3 should match >=0.0.3 <0.0.4
        assert matcher.matches("0.0.3", "^0.0.3") is True

        # Should not match
        assert matcher.matches("0.0.4", "^0.0.3") is False
        assert matcher.matches("0.1.0", "^0.0.3") is False


class TestVersionMatcherTildeConstraint:
    """Tests for tilde (~) version constraints.

    Tilde allows patch-level changes.
    ~1.2.3 := >=1.2.3 <1.3.0
    """

    def test_tilde_allows_patch_updates(self):
        """~1.2.3 allows 1.2.x where x >= 3."""
        matcher = VersionMatcher()

        # ~1.2.3 should match >=1.2.3 <1.3.0
        assert matcher.matches("1.2.3", "~1.2.3") is True
        assert matcher.matches("1.2.4", "~1.2.3") is True
        assert matcher.matches("1.2.99", "~1.2.3") is True

        # Should not match
        assert matcher.matches("1.2.2", "~1.2.3") is False
        assert matcher.matches("1.3.0", "~1.2.3") is False
        assert matcher.matches("2.0.0", "~1.2.3") is False

    def test_tilde_zero_version(self):
        """~0.2.3 allows only patch updates."""
        matcher = VersionMatcher()

        assert matcher.matches("0.2.3", "~0.2.3") is True
        assert matcher.matches("0.2.5", "~0.2.3") is True
        assert matcher.matches("0.3.0", "~0.2.3") is False


class TestVersionMatcherRangeConstraints:
    """Tests for range (>=, <=, >, <) constraints."""

    def test_greater_than_or_equal(self):
        """>=1.0.0 matches versions 1.0.0 and above."""
        matcher = VersionMatcher()

        assert matcher.matches("1.0.0", ">=1.0.0") is True
        assert matcher.matches("1.0.1", ">=1.0.0") is True
        assert matcher.matches("2.0.0", ">=1.0.0") is True
        assert matcher.matches("10.0.0", ">=1.0.0") is True

        assert matcher.matches("0.9.9", ">=1.0.0") is False

    def test_less_than(self):
        """<2.0.0 matches versions below 2.0.0."""
        matcher = VersionMatcher()

        assert matcher.matches("1.9.9", "<2.0.0") is True
        assert matcher.matches("1.0.0", "<2.0.0") is True
        assert matcher.matches("0.0.1", "<2.0.0") is True

        assert matcher.matches("2.0.0", "<2.0.0") is False
        assert matcher.matches("2.0.1", "<2.0.0") is False

    def test_combined_range(self):
        """>=1.0.0 <2.0.0 matches versions in range."""
        matcher = VersionMatcher()

        assert matcher.matches("1.0.0", ">=1.0.0 <2.0.0") is True
        assert matcher.matches("1.5.0", ">=1.0.0 <2.0.0") is True
        assert matcher.matches("1.9.9", ">=1.0.0 <2.0.0") is True

        assert matcher.matches("0.9.9", ">=1.0.0 <2.0.0") is False
        assert matcher.matches("2.0.0", ">=1.0.0 <2.0.0") is False


class TestVersionMatcherWildcard:
    """Tests for wildcard (*) constraints."""

    def test_wildcard_matches_all(self):
        """* matches any version."""
        matcher = VersionMatcher()

        assert matcher.matches("0.0.1", "*") is True
        assert matcher.matches("1.0.0", "*") is True
        assert matcher.matches("999.999.999", "*") is True

    def test_wildcard_minor(self):
        """1.* matches any 1.x.x version."""
        matcher = VersionMatcher()

        assert matcher.matches("1.0.0", "1.*") is True
        assert matcher.matches("1.5.3", "1.*") is True
        assert matcher.matches("1.99.99", "1.*") is True

        assert matcher.matches("0.9.9", "1.*") is False
        assert matcher.matches("2.0.0", "1.*") is False

    def test_wildcard_patch(self):
        """1.2.* matches any 1.2.x version."""
        matcher = VersionMatcher()

        assert matcher.matches("1.2.0", "1.2.*") is True
        assert matcher.matches("1.2.99", "1.2.*") is True

        assert matcher.matches("1.3.0", "1.2.*") is False
        assert matcher.matches("1.1.9", "1.2.*") is False


class TestVersionMatcherInvalidConstraints:
    """Tests for handling invalid version constraints."""

    def test_invalid_constraint_format(self):
        """Invalid constraint raises error."""
        matcher = VersionMatcher()

        with pytest.raises(VersionConstraintError):
            matcher.matches("1.0.0", "invalid")

    def test_invalid_version_format(self):
        """Invalid version raises error."""
        matcher = VersionMatcher()

        with pytest.raises(VersionConstraintError):
            matcher.matches("not-a-version", "^1.0.0")


class TestVersionMatcherFilterInstances:
    """Tests for filtering service instances by version."""

    def _create_instance(self, version: str, name: str = "test-service") -> ServiceInstance:
        """Helper to create test instances."""
        return ServiceInstance(
            name=name,
            version=version,
            instance_id=f"{name}-{version.replace('.', '-')}",
            address="10.0.0.1",
            port=8080,
            protocol=Protocol.HTTP,
            health_status=HealthStatus.HEALTHY,
            tags=[],
            metadata={},
        )

    def test_filter_by_caret_constraint(self):
        """Filter instances by caret version constraint."""
        matcher = VersionMatcher()
        instances = [
            self._create_instance("1.0.0"),
            self._create_instance("1.2.0"),
            self._create_instance("1.5.0"),
            self._create_instance("2.0.0"),
            self._create_instance("2.1.0"),
        ]

        filtered = matcher.filter_by_version(instances, "^1.0.0")

        versions = [i.version for i in filtered]
        assert "1.0.0" in versions
        assert "1.2.0" in versions
        assert "1.5.0" in versions
        assert "2.0.0" not in versions
        assert "2.1.0" not in versions

    def test_filter_by_tilde_constraint(self):
        """Filter instances by tilde version constraint."""
        matcher = VersionMatcher()
        instances = [
            self._create_instance("1.2.0"),
            self._create_instance("1.2.5"),
            self._create_instance("1.3.0"),
            self._create_instance("1.4.0"),
        ]

        filtered = matcher.filter_by_version(instances, "~1.2.0")

        versions = [i.version for i in filtered]
        assert "1.2.0" in versions
        assert "1.2.5" in versions
        assert "1.3.0" not in versions

    def test_filter_no_constraint(self):
        """No constraint returns all instances."""
        matcher = VersionMatcher()
        instances = [
            self._create_instance("1.0.0"),
            self._create_instance("2.0.0"),
        ]

        filtered = matcher.filter_by_version(instances, None)

        assert len(filtered) == 2

    def test_filter_empty_list(self):
        """Empty instance list returns empty list."""
        matcher = VersionMatcher()

        filtered = matcher.filter_by_version([], "^1.0.0")

        assert filtered == []


class TestVersionMatcherPrerelease:
    """Tests for prerelease version handling."""

    def test_prerelease_ordering(self):
        """Prerelease versions sort correctly."""
        matcher = VersionMatcher()

        # alpha < beta < rc < release
        assert matcher.matches("1.0.0-alpha", ">=1.0.0-alpha") is True
        assert matcher.matches("1.0.0-beta", ">=1.0.0-alpha") is True
        assert matcher.matches("1.0.0-rc.1", ">=1.0.0-alpha") is True
        assert matcher.matches("1.0.0", ">=1.0.0-alpha") is True

    def test_caret_excludes_prerelease(self):
        """Caret constraint excludes prerelease by default."""
        matcher = VersionMatcher()

        # Standard behavior: ^1.0.0 should not match prereleases of 1.0.0
        # but should match prereleases of higher versions
        assert matcher.matches("1.0.0", "^1.0.0") is True
        assert matcher.matches("1.0.1-beta", "^1.0.0") is True

    def test_include_prerelease_flag(self):
        """Prerelease versions follow semver comparison rules.

        In semver, 2.0.0-alpha < 2.0.0, so it falls within ^1.0.0 (>=1.0.0 <2.0.0).
        This matches standard semver library behavior.
        """
        matcher = VersionMatcher(include_prerelease=True)

        # 2.0.0-alpha < 2.0.0, so it IS within ^1.0.0 (>=1.0.0 <2.0.0)
        assert matcher.matches("2.0.0-alpha", "^1.0.0") is True
        # But 2.0.0 is NOT within ^1.0.0
        assert matcher.matches("2.0.0", "^1.0.0") is False
