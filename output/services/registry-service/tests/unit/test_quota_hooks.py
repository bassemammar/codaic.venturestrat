"""
Test quota checking hooks functionality.

This tests Task 12.4: Implement quota checking hooks
Validates that quota hooks are properly integrated with BaseModel operations.
"""
import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add SDK paths for testing
current_dir = os.path.dirname(os.path.abspath(__file__))
# From services/registry-service/tests/unit, we need to go up to project root then to sdk
project_root = os.path.join(current_dir, "..", "..", "..", "..")
sdk_models_path = os.path.join(project_root, "sdk", "venturestrat-models", "src")
sdk_tenancy_path = os.path.join(project_root, "sdk", "venturestrat-tenancy", "src")
sys.path.insert(0, sdk_models_path)
sys.path.insert(0, sdk_tenancy_path)

from venturestrat.models.quota_hooks import (
    QuotaChecker,
    QuotaExceededException,
    check_record_quota_hook,
    check_user_quota_hook,
    get_quota_checker,
)


class TestQuotaChecker:
    """Test QuotaChecker class functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.quota_checker = QuotaChecker()

    def test_quota_checker_initialization(self):
        """Test that QuotaChecker initializes properly."""
        checker = QuotaChecker()
        assert hasattr(checker, "_tenant_quotas_cache")
        assert isinstance(checker._tenant_quotas_cache, dict)

    def test_get_quota_checker_singleton(self):
        """Test that get_quota_checker returns the same instance."""
        checker1 = get_quota_checker()
        checker2 = get_quota_checker()
        assert checker1 is checker2

    @patch("venturestrat.models.quota_hooks.logger")
    def test_check_user_quota_before_create_no_quotas(self, mock_logger):
        """Test user quota check when no quotas are configured."""
        with patch.object(self.quota_checker, "_get_tenant_quotas_sync", return_value=None):
            # Should not raise exception when no quotas configured
            self.quota_checker.check_user_quota_before_create("test-tenant")
            # Should complete without error

    @patch("venturestrat.models.quota_hooks.logger")
    def test_check_user_quota_before_create_within_limit(self, mock_logger):
        """Test user quota check when within limits."""
        # Mock quota object
        mock_quotas = Mock()
        mock_quotas.is_within_user_limit.return_value = True
        mock_quotas.max_users = 100

        with patch.object(self.quota_checker, "_get_tenant_quotas_sync", return_value=mock_quotas):
            with patch.object(self.quota_checker, "_count_users_for_tenant_sync", return_value=50):
                # Should not raise exception when within limits
                self.quota_checker.check_user_quota_before_create("test-tenant")
                mock_quotas.is_within_user_limit.assert_called_once_with(51)  # current + 1

    @patch("venturestrat.models.quota_hooks.logger")
    def test_check_user_quota_before_create_exceeds_limit(self, mock_logger):
        """Test user quota check when exceeding limits."""
        # Mock quota object
        mock_quotas = Mock()
        mock_quotas.is_within_user_limit.return_value = False
        mock_quotas.max_users = 100

        with patch.object(self.quota_checker, "_get_tenant_quotas_sync", return_value=mock_quotas):
            with patch.object(self.quota_checker, "_count_users_for_tenant_sync", return_value=100):
                with pytest.raises(QuotaExceededException) as exc_info:
                    self.quota_checker.check_user_quota_before_create("test-tenant")

                exception = exc_info.value
                assert exception.quota_type == "users"
                assert exception.current_usage == 100
                assert exception.limit == 100
                assert exception.tenant_id == "test-tenant"

    @patch("venturestrat.models.quota_hooks.logger")
    def test_check_user_quota_before_create_fail_open(self, mock_logger):
        """Test that user quota check fails open on unexpected errors."""
        with patch.object(
            self.quota_checker, "_get_tenant_quotas_sync", side_effect=Exception("DB Error")
        ):
            # Should not raise exception on internal error (fail-open behavior)
            self.quota_checker.check_user_quota_before_create("test-tenant")
            mock_logger.warning.assert_called()

    @patch("venturestrat.models.quota_hooks.logger")
    def test_check_record_quota_before_create_sync_not_new_record(self, mock_logger):
        """Test record quota check skips non-new records."""
        mock_model = Mock()
        mock_model._is_new = False

        # Should return early without checking quotas
        self.quota_checker.check_record_quota_before_create_sync(mock_model)
        # No quota checks should be performed

    @patch("venturestrat.models.quota_hooks.logger")
    def test_check_record_quota_before_create_sync_no_tenant_field(self, mock_logger):
        """Test record quota check skips models without tenant field."""
        mock_model = Mock()
        mock_model._is_new = True
        # Remove _tenant_field attribute
        if hasattr(mock_model, "_tenant_field"):
            delattr(mock_model, "_tenant_field")

        # Should return early without checking quotas
        self.quota_checker.check_record_quota_before_create_sync(mock_model)
        # No quota checks should be performed

    @patch("venturestrat.models.quota_hooks.logger")
    def test_check_record_quota_before_create_sync_within_limit(self, mock_logger):
        """Test record quota check when within limits."""
        mock_model = Mock()
        mock_model._is_new = True
        mock_model._tenant_field = "tenant_id"
        mock_model.__class__.__name__ = "TestModel"
        # Set tenant_id
        setattr(mock_model, "tenant_id", "test-tenant")

        # Mock quota object
        mock_quotas = Mock()
        mock_quotas.is_within_record_limit.return_value = True
        mock_quotas.max_records_per_model = 1000

        with patch.object(self.quota_checker, "_get_tenant_quotas_sync", return_value=mock_quotas):
            with patch.object(
                self.quota_checker, "_count_records_for_model_sync", return_value=500
            ):
                # Should not raise exception when within limits
                self.quota_checker.check_record_quota_before_create_sync(mock_model)
                mock_quotas.is_within_record_limit.assert_called_once_with(501)  # current + 1

    @patch("venturestrat.models.quota_hooks.logger")
    def test_check_record_quota_before_create_sync_exceeds_limit(self, mock_logger):
        """Test record quota check when exceeding limits."""
        mock_model = Mock()
        mock_model._is_new = True
        mock_model._tenant_field = "tenant_id"
        mock_model.__class__.__name__ = "TestModel"
        # Set tenant_id
        setattr(mock_model, "tenant_id", "test-tenant")

        # Mock quota object
        mock_quotas = Mock()
        mock_quotas.is_within_record_limit.return_value = False
        mock_quotas.max_records_per_model = 1000

        with patch.object(self.quota_checker, "_get_tenant_quotas_sync", return_value=mock_quotas):
            with patch.object(
                self.quota_checker, "_count_records_for_model_sync", return_value=1000
            ):
                with pytest.raises(QuotaExceededException) as exc_info:
                    self.quota_checker.check_record_quota_before_create_sync(mock_model)

                exception = exc_info.value
                assert exception.quota_type == "records_per_model"
                assert exception.current_usage == 1000
                assert exception.limit == 1000
                assert exception.tenant_id == "test-tenant"
                assert exception.model_name == "TestModel"

    @patch("venturestrat.models.quota_hooks.logger")
    def test_check_record_quota_before_create_sync_fail_open(self, mock_logger):
        """Test that record quota check fails open on unexpected errors."""
        mock_model = Mock()
        mock_model._is_new = True
        mock_model._tenant_field = "tenant_id"
        setattr(mock_model, "tenant_id", "test-tenant")

        with patch.object(
            self.quota_checker, "_get_tenant_quotas_sync", side_effect=Exception("DB Error")
        ):
            # Should not raise exception on internal error (fail-open behavior)
            self.quota_checker.check_record_quota_before_create_sync(mock_model)
            mock_logger.warning.assert_called()

    def test_count_users_for_tenant_sync_redis_available(self):
        """Test user counting with Redis available."""
        with patch("redis.Redis") as mock_redis_class:
            mock_redis = Mock()
            mock_redis.get.return_value = "42"
            mock_redis_class.return_value = mock_redis

            count = self.quota_checker._count_users_for_tenant_sync("test-tenant")
            assert count == 42
            mock_redis.get.assert_called_once_with("quota:users:test-tenant")

    def test_count_users_for_tenant_sync_redis_not_available(self):
        """Test user counting with Redis not available."""
        with patch("redis.Redis", side_effect=ImportError("Redis not available")):
            count = self.quota_checker._count_users_for_tenant_sync("test-tenant")
            assert count == 0  # Fallback value

    @patch("venturestrat.models.quota_hooks.logger")
    def test_count_users_for_tenant_sync_error_handling(self, mock_logger):
        """Test user counting error handling."""
        with patch("redis.Redis", side_effect=Exception("Connection error")):
            count = self.quota_checker._count_users_for_tenant_sync("test-tenant")
            assert count == 0  # Fail-open behavior
            mock_logger.warning.assert_called()


class TestQuotaHookFunctions:
    """Test the global quota hook functions."""

    def test_check_record_quota_hook(self):
        """Test the global check_record_quota_hook function."""
        mock_model = Mock()
        mock_model._is_new = True

        with patch("venturestrat.models.quota_hooks.get_quota_checker") as mock_get_checker:
            mock_checker = Mock()
            mock_get_checker.return_value = mock_checker

            check_record_quota_hook(mock_model)

            mock_get_checker.assert_called_once()
            mock_checker.check_record_quota_before_create_sync.assert_called_once_with(mock_model)

    def test_check_user_quota_hook(self):
        """Test the global check_user_quota_hook function."""
        tenant_id = "test-tenant"

        with patch("venturestrat.models.quota_hooks.get_quota_checker") as mock_get_checker:
            mock_checker = Mock()
            mock_get_checker.return_value = mock_checker

            check_user_quota_hook(tenant_id)

            mock_get_checker.assert_called_once()
            mock_checker.check_user_quota_before_create.assert_called_once_with(tenant_id)


class TestQuotaExceededException:
    """Test the QuotaExceededException class."""

    def test_quota_exceeded_exception_with_model_name(self):
        """Test QuotaExceededException with model name."""
        exception = QuotaExceededException(
            quota_type="records_per_model",
            current_usage=1000,
            limit=1000,
            tenant_id="test-tenant",
            model_name="Quote",
        )

        assert exception.quota_type == "records_per_model"
        assert exception.current_usage == 1000
        assert exception.limit == 1000
        assert exception.tenant_id == "test-tenant"
        assert exception.model_name == "Quote"
        assert "Quote" in str(exception)
        assert "test-tenant" in str(exception)
        assert "records_per_model" in str(exception)

    def test_quota_exceeded_exception_without_model_name(self):
        """Test QuotaExceededException without model name."""
        exception = QuotaExceededException(
            quota_type="users", current_usage=100, limit=100, tenant_id="test-tenant"
        )

        assert exception.quota_type == "users"
        assert exception.current_usage == 100
        assert exception.limit == 100
        assert exception.tenant_id == "test-tenant"
        assert exception.model_name is None
        assert "test-tenant" in str(exception)
        assert "users" in str(exception)
        assert "model:" not in str(exception)  # Should not include model info


class TestQuotaHooksIntegration:
    """Test integration of quota hooks with BaseModel operations."""

    @patch("venturestrat.models.quota_hooks.logger")
    def test_basemodel_save_calls_quota_hook(self, mock_logger):
        """Test that BaseModel.save() calls quota hooks."""
        # This would be an integration test with actual BaseModel
        # For now, we test the hook function directly

        mock_model = Mock()
        mock_model._is_new = True
        mock_model._tenant_field = "tenant_id"
        mock_model.__class__.__name__ = "TestModel"
        setattr(mock_model, "tenant_id", "test-tenant")

        # Test that hook function can be called successfully
        with patch("venturestrat.models.quota_hooks.QuotaChecker") as mock_checker_class:
            mock_checker = Mock()
            mock_checker_class.return_value = mock_checker

            check_record_quota_hook(mock_model)

            # Verify the hook was called with the model
            mock_checker.check_record_quota_before_create_sync.assert_called_once_with(mock_model)

    def test_quota_enforcement_prevents_resource_abuse(self):
        """Test that quota enforcement prevents resource abuse."""
        # Simulate multiple record creation attempts
        checker = QuotaChecker()

        mock_model = Mock()
        mock_model._is_new = True
        mock_model._tenant_field = "tenant_id"
        mock_model.__class__.__name__ = "TestModel"
        setattr(mock_model, "tenant_id", "test-tenant")

        # Mock quota at limit
        mock_quotas = Mock()
        mock_quotas.is_within_record_limit.return_value = False
        mock_quotas.max_records_per_model = 1000

        with patch.object(checker, "_get_tenant_quotas_sync", return_value=mock_quotas):
            with patch.object(checker, "_count_records_for_model_sync", return_value=1000):
                with pytest.raises(QuotaExceededException):
                    checker.check_record_quota_before_create_sync(mock_model)

        # Ensure the check was properly performed
        mock_quotas.is_within_record_limit.assert_called_once_with(1001)


if __name__ == "__main__":
    # Run the tests directly
    pytest.main([__file__, "-v"])
