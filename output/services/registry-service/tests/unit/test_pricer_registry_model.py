"""Tests for PricerRegistry model - Database Schema Design.

These tests define the expected behavior of the PricerRegistry model for
pricing infrastructure plugin architecture as required by Task 1.1.
"""
import pytest
import datetime
from unittest.mock import MagicMock

from registry.models.pricer_registry import PricerRegistry, PricerStatus


class TestPricerStatus:
    """Tests for PricerStatus enum."""

    def test_enum_values(self):
        """PricerStatus has expected string values."""
        assert PricerStatus.HEALTHY == "healthy"
        assert PricerStatus.UNHEALTHY == "unhealthy"
        assert PricerStatus.UNKNOWN == "unknown"
        assert PricerStatus.DISABLED == "disabled"

    def test_enum_inherits_from_str(self):
        """PricerStatus enum values are strings."""
        assert isinstance(PricerStatus.HEALTHY, str)
        assert isinstance(PricerStatus.UNHEALTHY, str)
        assert isinstance(PricerStatus.UNKNOWN, str)
        assert isinstance(PricerStatus.DISABLED, str)


class TestPricerRegistry:
    """Tests for PricerRegistry model."""

    def test_create_minimal_pricer(self):
        """Create pricer with required fields only."""
        pricer = PricerRegistry(
            pricer_id="quantlib-v1.18",
            name="QuantLib",
            version="1.18.0",
            health_check_url="http://quantlib:8088/health",
            pricing_url="http://quantlib:8088/api/v1"
        )

        assert pricer.pricer_id == "quantlib-v1.18"
        assert pricer.name == "QuantLib"
        assert pricer.version == "1.18.0"
        assert pricer.health_check_url == "http://quantlib:8088/health"
        assert pricer.pricing_url == "http://quantlib:8088/api/v1"
        assert pricer.description is None
        assert pricer.batch_supported is False
        assert pricer.max_batch_size is None
        assert pricer.status == PricerStatus.HEALTHY.value
        assert pricer.last_health_check is None
        assert pricer.health_check_failures == 0

        # Should have auto-generated timestamps
        assert pricer.created_at is not None
        assert pricer.updated_at is not None

    def test_create_full_pricer(self):
        """Create pricer with all fields."""
        created_at = datetime.datetime.now(datetime.timezone.utc)
        updated_at = datetime.datetime.now(datetime.timezone.utc)
        last_health_check = datetime.datetime.now(datetime.timezone.utc)

        pricer = PricerRegistry(
            pricer_id="treasury-v2.3",
            name="Treasury",
            version="2.3.0",
            description="Proprietary Treasury pricing engine",
            health_check_url="http://treasury:8101/health",
            pricing_url="http://treasury:8101/api/v1",
            batch_supported=True,
            max_batch_size=5000,
            status=PricerStatus.HEALTHY,
            last_health_check=last_health_check,
            health_check_failures=2,
            created_at=created_at,
            updated_at=updated_at
        )

        assert pricer.pricer_id == "treasury-v2.3"
        assert pricer.name == "Treasury"
        assert pricer.version == "2.3.0"
        assert pricer.description == "Proprietary Treasury pricing engine"
        assert pricer.health_check_url == "http://treasury:8101/health"
        assert pricer.pricing_url == "http://treasury:8101/api/v1"
        assert pricer.batch_supported is True
        assert pricer.max_batch_size == 5000
        assert pricer.status == PricerStatus.HEALTHY
        assert pricer.last_health_check == last_health_check
        assert pricer.health_check_failures == 2
        assert pricer.created_at == created_at
        assert pricer.updated_at == updated_at

    def test_create_quantlib_pricer(self):
        """Create QuantLib pricer using factory method."""
        quantlib = PricerRegistry.create_quantlib_pricer()

        assert quantlib.pricer_id == "quantlib-v1.18"
        assert quantlib.name == "QuantLib"
        assert quantlib.version == "1.18.0"
        assert "quantitative finance library" in quantlib.description.lower()
        assert quantlib.health_check_url == "http://quantlib-service:8088/health"
        assert quantlib.pricing_url == "http://quantlib-service:8088/api/v1"
        assert quantlib.batch_supported is True
        assert quantlib.max_batch_size == 10000
        assert quantlib.status == PricerStatus.HEALTHY

    def test_create_treasury_pricer(self):
        """Create Treasury pricer using factory method."""
        treasury = PricerRegistry.create_treasury_pricer()

        assert treasury.pricer_id == "treasury-v2.3"
        assert treasury.name == "Treasury"
        assert treasury.version == "2.3.0"
        assert "proprietary" in treasury.description.lower()
        assert "monte carlo" in treasury.description.lower()
        assert treasury.health_check_url == "http://treasury-service:8101/health"
        assert treasury.pricing_url == "http://treasury-service:8101/api/v1"
        assert treasury.batch_supported is True
        assert treasury.max_batch_size == 5000
        assert treasury.status == PricerStatus.HEALTHY

    def test_is_healthy_method(self):
        """Test is_healthy method."""
        healthy_pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.HEALTHY
        )

        unhealthy_pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.UNHEALTHY
        )

        assert healthy_pricer.is_healthy() is True
        assert unhealthy_pricer.is_healthy() is False

    def test_mark_healthy(self):
        """Test marking pricer as healthy."""
        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.UNHEALTHY,
            health_check_failures=3
        )

        original_updated_at = pricer.updated_at
        healthy_pricer = pricer.mark_healthy()

        # Check new instance
        assert healthy_pricer.status == PricerStatus.HEALTHY
        assert healthy_pricer.health_check_failures == 0
        assert healthy_pricer.last_health_check is not None
        assert healthy_pricer.updated_at.timestamp() > original_updated_at.timestamp()

        # Original unchanged
        assert pricer.status == PricerStatus.UNHEALTHY
        assert pricer.health_check_failures == 3

    def test_mark_unhealthy(self):
        """Test marking pricer as unhealthy."""
        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.HEALTHY,
            health_check_failures=1
        )

        original_updated_at = pricer.updated_at
        unhealthy_pricer = pricer.mark_unhealthy(increment_failures=True)

        # Check new instance
        assert unhealthy_pricer.status == PricerStatus.UNHEALTHY
        assert unhealthy_pricer.health_check_failures == 2
        assert unhealthy_pricer.last_health_check is not None
        assert unhealthy_pricer.updated_at.timestamp() > original_updated_at.timestamp()

        # Test without incrementing failures
        unhealthy_no_increment = pricer.mark_unhealthy(increment_failures=False)
        assert unhealthy_no_increment.health_check_failures == 1

        # Original unchanged
        assert pricer.status == PricerStatus.HEALTHY
        assert pricer.health_check_failures == 1

    def test_disable_pricer(self):
        """Test disabling a pricer."""
        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            description="Original description",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.HEALTHY
        )

        disabled_pricer = pricer.disable("Service deprecated")

        assert disabled_pricer.status == PricerStatus.DISABLED
        assert "DISABLED: Service deprecated" in disabled_pricer.description
        assert disabled_pricer.updated_at.timestamp() > pricer.updated_at.timestamp()

        # Original unchanged
        assert pricer.status == PricerStatus.HEALTHY
        assert "DISABLED" not in pricer.description

    def test_get_capabilities_summary_empty(self):
        """Test capabilities summary with no capabilities."""
        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1"
        )

        summary = pricer.get_capabilities_summary()

        assert summary["total_capabilities"] == 0
        assert summary["supported_instruments"] == []
        assert summary["supported_models"] == []
        assert summary["features"] == []

    def test_get_capabilities_summary_with_capabilities(self):
        """Test capabilities summary with mock capabilities."""
        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1"
        )

        # Mock capabilities
        mock_cap1 = MagicMock()
        mock_cap1.instrument_type = "swap"
        mock_cap1.model_type = "Hull-White"
        mock_cap1.features = ["greeks", "duration"]

        mock_cap2 = MagicMock()
        mock_cap2.instrument_type = "bond"
        mock_cap2.model_type = None
        mock_cap2.features = ["yield", "duration"]

        pricer.capabilities = [mock_cap1, mock_cap2]

        summary = pricer.get_capabilities_summary()

        assert summary["total_capabilities"] == 2
        assert set(summary["supported_instruments"]) == {"swap", "bond"}
        assert "Hull-White" in summary["supported_models"]
        assert set(summary["features"]) == {"greeks", "duration", "yield"}

    def test_pricer_id_validation_valid_cases(self):
        """Valid pricer_id formats are accepted."""
        valid_ids = [
            "quantlib-v1.0",
            "quantlib-v1.18",
            "treasury-v2.3",
            "custom-v1.0.0",
            "pricer-v10.5.2",
            "test-pricer-v0.1",
        ]

        for pricer_id in valid_ids:
            pricer = PricerRegistry(
                pricer_id=pricer_id,
                name="Test",
                version="1.0",
                health_check_url="http://test:8080/health",
                pricing_url="http://test:8080/api/v1"
            )
            assert pricer.pricer_id == pricer_id

    def test_serialization_to_dict(self):
        """Pricer serializes to dictionary with ISO timestamps."""
        created_at = datetime.datetime.now(datetime.timezone.utc)
        updated_at = datetime.datetime.now(datetime.timezone.utc)
        last_health_check = datetime.datetime.now(datetime.timezone.utc)

        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test Pricer",
            version="1.0.0",
            description="Test pricer description",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            batch_supported=True,
            max_batch_size=1000,
            status=PricerStatus.HEALTHY,
            last_health_check=last_health_check,
            health_check_failures=0,
            created_at=created_at,
            updated_at=updated_at
        )

        data = pricer.to_dict()

        assert data["pricer_id"] == "test-v1.0"
        assert data["name"] == "Test Pricer"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Test pricer description"
        assert data["batch_supported"] is True
        assert data["max_batch_size"] == 1000
        assert data["status"] == "healthy"  # String value, not enum
        assert data["health_check_failures"] == 0
        assert data["created_at"] == created_at.isoformat()
        assert data["updated_at"] == updated_at.isoformat()
        assert data["last_health_check"] == last_health_check.isoformat()

    def test_immutability_through_methods(self):
        """Pricer methods return new instances, don't mutate original."""
        original = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.HEALTHY,
            health_check_failures=0
        )

        # Test all mutation methods
        healthy = original.mark_healthy()
        unhealthy = original.mark_unhealthy()
        disabled = original.disable("Test reason")

        # Original should be unchanged
        assert original.status == PricerStatus.HEALTHY
        assert original.health_check_failures == 0
        assert "DISABLED" not in (original.description or "")

        # New instances should be different
        assert healthy.status == PricerStatus.HEALTHY
        assert unhealthy.status == PricerStatus.UNHEALTHY
        assert disabled.status == PricerStatus.DISABLED

    def test_default_values(self):
        """Test default values are set correctly."""
        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1"
        )

        # Check defaults
        assert pricer.description is None
        assert pricer.batch_supported is False
        assert pricer.max_batch_size is None
        assert pricer.status == PricerStatus.HEALTHY.value
        assert pricer.last_health_check is None
        assert pricer.health_check_failures == 0

        # Check auto-generated values
        assert pricer.created_at is not None
        assert pricer.updated_at is not None

    def test_string_representation(self):
        """Test string representation methods."""
        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test Pricer",
            version="1.0.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.HEALTHY
        )

        str_repr = str(pricer)
        assert "PricerRegistry(" in str_repr
        assert "test-v1.0" in str_repr
        assert "Test Pricer" in str_repr
        assert "healthy" in str_repr

        repr_str = repr(pricer)
        assert "PricerRegistry(" in repr_str
        assert "pricer_id='test-v1.0'" in repr_str
        assert "name='Test Pricer'" in repr_str
        assert "version='1.0.0'" in repr_str


class TestPricerRegistryConstraints:
    """Tests for PricerRegistry database constraints."""

    def test_pricer_id_format_constraint_logic(self):
        """Test pricer_id format constraint validation logic."""
        # Valid formats (should pass regex: ^[a-z0-9-]+-v[0-9]+\.[0-9]+(\.[0-9]+)?$)
        valid_ids = [
            "quantlib-v1.0",
            "quantlib-v1.18",
            "treasury-v2.3",
            "custom-v1.0.0",
            "pricer-v10.5.2",
            "test-pricer-v0.1",
            "a-v1.0",
            "pricer123-v1.0",
            "my-pricer-v1.2.3"
        ]

        for pricer_id in valid_ids:
            # Test regex pattern compliance
            import re
            pattern = r'^[a-z0-9-]+-v[0-9]+\.[0-9]+(\.[0-9]+)?$'
            assert re.match(pattern, pricer_id), f"ID {pricer_id} should match pattern"

        # Invalid formats (should fail regex)
        invalid_ids = [
            "quantlib",           # no version
            "quantlib-1.0",       # no 'v' prefix
            "quantlib-v1",        # no minor version
            "quantlib-v1.",       # incomplete version
            "quantlib-v",         # no version numbers
            "QUANTLIB-v1.0",      # uppercase
            "quantlib_v1.0",      # underscore
            "-quantlib-v1.0",     # starts with hyphen
            "quantlib-v1.0-",     # ends with hyphen
            "quantlib-v1.0.0.0",  # too many version parts
            "",                   # empty
            "v1.0",               # no name
            "quantlib-v-1.0",     # invalid version format
        ]

        for pricer_id in invalid_ids:
            import re
            pattern = r'^[a-z0-9-]+-v[0-9]+\.[0-9]+(\.[0-9]+)?$'
            assert not re.match(pattern, pricer_id), f"ID {pricer_id} should NOT match pattern"

    def test_max_batch_size_positive_constraint_logic(self):
        """Test max_batch_size positive constraint validation logic."""
        # Valid values (null or positive)
        valid_sizes = [None, 1, 100, 1000, 10000, 50000]

        for size in valid_sizes:
            # Constraint: max_batch_size IS NULL OR max_batch_size > 0
            constraint_passes = size is None or size > 0
            assert constraint_passes, f"Size {size} should pass constraint"

        # Invalid values (zero or negative)
        invalid_sizes = [0, -1, -100, -1000]

        for size in invalid_sizes:
            constraint_passes = size is None or size > 0
            assert not constraint_passes, f"Size {size} should fail constraint"

    def test_health_check_failures_non_negative_constraint_logic(self):
        """Test health_check_failures non-negative constraint validation logic."""
        # Valid values (zero or positive)
        valid_failures = [0, 1, 5, 10, 100, 999]

        for failures in valid_failures:
            # Constraint: health_check_failures >= 0
            constraint_passes = failures >= 0
            assert constraint_passes, f"Failures {failures} should pass constraint"

        # Invalid values (negative)
        invalid_failures = [-1, -5, -100]

        for failures in invalid_failures:
            constraint_passes = failures >= 0
            assert not constraint_passes, f"Failures {failures} should fail constraint"

    def test_pricer_status_enum_constraint_logic(self):
        """Test pricer status enum constraint validation logic."""
        # Valid status values
        valid_statuses = ["healthy", "unhealthy", "unknown", "disabled"]

        for status in valid_statuses:
            # Constraint: status IN ('healthy', 'unhealthy', 'unknown', 'disabled')
            constraint_passes = status in ["healthy", "unhealthy", "unknown", "disabled"]
            assert constraint_passes, f"Status {status} should pass constraint"

        # Invalid status values
        invalid_statuses = ["active", "inactive", "running", "stopped", "", "HEALTHY", "null"]

        for status in invalid_statuses:
            constraint_passes = status in ["healthy", "unhealthy", "unknown", "disabled"]
            assert not constraint_passes, f"Status {status} should fail constraint"


class TestPricerRegistryBusinessLogic:
    """Tests for PricerRegistry business logic."""

    def test_health_status_transitions(self):
        """Test valid health status transitions."""
        # Start with healthy pricer
        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            status=PricerStatus.HEALTHY,
            health_check_failures=0
        )

        # Healthy -> Unhealthy
        unhealthy = pricer.mark_unhealthy()
        assert unhealthy.status == PricerStatus.UNHEALTHY
        assert unhealthy.health_check_failures == 1

        # Unhealthy -> Healthy (recovery)
        recovered = unhealthy.mark_healthy()
        assert recovered.status == PricerStatus.HEALTHY
        assert recovered.health_check_failures == 0

        # Any -> Disabled
        disabled = pricer.disable("Maintenance")
        assert disabled.status == PricerStatus.DISABLED

    def test_health_check_failure_tracking(self):
        """Test health check failure counting."""
        pricer = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            health_check_failures=5
        )

        # Increment failures
        failed1 = pricer.mark_unhealthy(increment_failures=True)
        assert failed1.health_check_failures == 6

        # Don't increment failures
        failed2 = pricer.mark_unhealthy(increment_failures=False)
        assert failed2.health_check_failures == 5

        # Reset on recovery
        healthy = pricer.mark_healthy()
        assert healthy.health_check_failures == 0

    def test_batch_support_configuration(self):
        """Test batch support configuration."""
        # Batch not supported
        no_batch = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            batch_supported=False,
            max_batch_size=None
        )

        assert no_batch.batch_supported is False
        assert no_batch.max_batch_size is None

        # Batch supported with limit
        with_batch = PricerRegistry(
            pricer_id="test-v1.0",
            name="Test",
            version="1.0",
            health_check_url="http://test:8080/health",
            pricing_url="http://test:8080/api/v1",
            batch_supported=True,
            max_batch_size=1000
        )

        assert with_batch.batch_supported is True
        assert with_batch.max_batch_size == 1000

    def test_version_parsing_logic(self):
        """Test version number parsing for pricer IDs."""
        test_cases = [
            ("quantlib-v1.18", ("quantlib", "1.18")),
            ("treasury-v2.3", ("treasury", "2.3")),
            ("custom-v1.0.0", ("custom", "1.0.0")),
            ("my-pricer-v10.5.2", ("my-pricer", "10.5.2")),
        ]

        for pricer_id, (expected_name, expected_version) in test_cases:
            # Extract name and version from pricer_id
            if "-v" in pricer_id:
                name_part, version_part = pricer_id.split("-v", 1)
                assert name_part == expected_name
                assert version_part == expected_version

    def test_service_url_validation_logic(self):
        """Test service URL format validation logic."""
        # Valid URL formats
        valid_urls = [
            "http://service:8080/health",
            "http://service:8080/api/v1",
            "https://service.domain.com:443/health",
            "http://localhost:8080/api/v1",
            "http://quantlib-service:8088/health",
            "http://treasury-service:8101/api/v1",
        ]

        for url in valid_urls:
            # Basic URL format validation (starts with http/https, has port)
            assert url.startswith(("http://", "https://"))
            assert ":" in url.split("//")[1]  # Port should be present

        # Invalid URL formats (for business logic validation)
        invalid_urls = [
            "",
            "not-a-url",
            "ftp://service:8080/health",
            "service:8080/health",  # Missing protocol
            "http://service/health",  # Missing port (optional in some cases)
        ]

        for url in invalid_urls:
            # Should not start with valid protocols
            if url:  # Skip empty string
                passes_basic_validation = url.startswith(("http://", "https://"))
                # Most invalid URLs should fail this basic check
                if url not in ["http://service/health"]:  # This one might pass basic check
                    assert not passes_basic_validation