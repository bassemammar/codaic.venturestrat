"""Unit tests for PricingRepository.

These tests verify the data access layer for pricing service registration
and capability management functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from registry.repositories.pricing_repository import PricingRepository
from registry.models.pricer_registry import PricerRegistry, PricerStatus
from registry.models.pricer_capability import PricerCapability
from registry.models.tenant_pricing_config import TenantPricingConfig


class TestPricingRepositoryInitialization:
    """Test PricingRepository initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful repository initialization."""
        with patch('registry.repositories.pricing_repository.create_async_engine') as mock_engine, \
             patch('registry.repositories.pricing_repository.sessionmaker') as mock_session_factory:

            mock_engine_instance = AsyncMock()
            mock_engine.return_value = mock_engine_instance

            mock_factory = MagicMock()
            mock_session_factory.return_value = mock_factory

            repo = PricingRepository()
            await repo.initialize()

            assert repo.engine == mock_engine_instance
            assert repo.session_factory == mock_factory
            mock_engine.assert_called_once()
            mock_session_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test repository initialization failure."""
        with patch('registry.repositories.pricing_repository.create_async_engine') as mock_engine:
            mock_engine.side_effect = Exception("Database connection failed")

            repo = PricingRepository()

            with pytest.raises(Exception, match="Database connection failed"):
                await repo.initialize()

    @pytest.mark.asyncio
    async def test_close(self):
        """Test repository close."""
        mock_engine = AsyncMock()

        repo = PricingRepository()
        repo.engine = mock_engine

        await repo.close()

        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_without_initialization(self):
        """Test getting session without initialization."""
        repo = PricingRepository()

        with pytest.raises(RuntimeError, match="Repository not initialized"):
            async with repo._get_session():
                pass


class TestPricingRepositoryPricerOperations:
    """Test pricer registry CRUD operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repo = PricingRepository()
        self.mock_session = AsyncMock()
        self.repo.session_factory = MagicMock(return_value=self.mock_session)

    @pytest.mark.asyncio
    async def test_save_new_pricer(self):
        """Test saving a new pricer."""
        # Setup
        pricer = PricerRegistry.create_quantlib_pricer()

        # Mock session behavior
        self.mock_session.get.return_value = None  # No existing pricer
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.save_pricer(pricer)

        # Verify
        self.mock_session.add.assert_called_once_with(pricer)
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once()
        assert result == pricer

    @pytest.mark.asyncio
    async def test_save_existing_pricer(self):
        """Test updating an existing pricer."""
        # Setup
        new_pricer = PricerRegistry.create_quantlib_pricer()
        existing_pricer = MagicMock()

        # Mock session behavior
        self.mock_session.get.return_value = existing_pricer
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.save_pricer(new_pricer)

        # Verify
        self.mock_session.add.assert_not_called()  # Should not add, just update existing
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(existing_pricer)
        assert result == existing_pricer

        # Check that existing pricer was updated
        assert existing_pricer.name == new_pricer.name
        assert existing_pricer.version == new_pricer.version

    @pytest.mark.asyncio
    async def test_save_pricer_failure(self):
        """Test handling save pricer failure."""
        # Setup
        pricer = PricerRegistry.create_quantlib_pricer()

        # Mock session behavior
        self.mock_session.get.return_value = None
        self.mock_session.commit.side_effect = Exception("Database error")
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute and verify
        with pytest.raises(Exception, match="Database error"):
            await self.repo.save_pricer(pricer)

        self.mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pricer_found(self):
        """Test getting an existing pricer."""
        # Setup
        pricer_id = "quantlib-v1.18"
        expected_pricer = PricerRegistry.create_quantlib_pricer()

        # Mock session behavior
        self.mock_session.get.return_value = expected_pricer
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.get_pricer(pricer_id)

        # Verify
        assert result == expected_pricer
        self.mock_session.get.assert_called_once_with(PricerRegistry, pricer_id)

    @pytest.mark.asyncio
    async def test_get_pricer_not_found(self):
        """Test getting a non-existent pricer."""
        # Setup
        pricer_id = "non-existent-v1.0"

        # Mock session behavior
        self.mock_session.get.return_value = None
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.get_pricer(pricer_id)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_list_pricers_all(self):
        """Test listing all pricers."""
        # Setup
        expected_pricers = [
            PricerRegistry.create_quantlib_pricer(),
            PricerRegistry.create_treasury_pricer()
        ]

        # Mock session behavior
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_pricers
        self.mock_session.execute.return_value = mock_result
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.list_pricers()

        # Verify
        assert result == expected_pricers
        self.mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_pricers_with_status_filter(self):
        """Test listing pricers with status filter."""
        # Setup
        status = PricerStatus.HEALTHY.value
        expected_pricers = [PricerRegistry.create_quantlib_pricer()]

        # Mock session behavior
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_pricers
        self.mock_session.execute.return_value = mock_result
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.list_pricers(status=status)

        # Verify
        assert result == expected_pricers
        self.mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_pricer_success(self):
        """Test deleting an existing pricer."""
        # Setup
        pricer_id = "quantlib-v1.18"
        pricer = PricerRegistry.create_quantlib_pricer()

        # Mock session behavior
        self.mock_session.get.return_value = pricer
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.delete_pricer(pricer_id)

        # Verify
        assert result is True
        self.mock_session.delete.assert_called_once_with(pricer)
        self.mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_pricer_not_found(self):
        """Test deleting a non-existent pricer."""
        # Setup
        pricer_id = "non-existent-v1.0"

        # Mock session behavior
        self.mock_session.get.return_value = None
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.delete_pricer(pricer_id)

        # Verify
        assert result is False
        self.mock_session.delete.assert_not_called()
        self.mock_session.commit.assert_not_called()


class TestPricingRepositoryCapabilityOperations:
    """Test capability CRUD operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repo = PricingRepository()
        self.mock_session = AsyncMock()
        self.repo.session_factory = MagicMock(return_value=self.mock_session)

    @pytest.mark.asyncio
    async def test_save_capability(self):
        """Test saving a capability."""
        # Setup
        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            model_type="Hull-White",
            features=["greeks", "duration"],
            priority=10
        )

        # Mock session behavior
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.save_capability(capability)

        # Verify
        self.mock_session.add.assert_called_once_with(capability)
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(capability)
        assert result == capability

    @pytest.mark.asyncio
    async def test_get_pricer_capabilities(self):
        """Test getting capabilities for a pricer."""
        # Setup
        pricer_id = "quantlib-v1.18"
        expected_capabilities = PricerCapability.create_quantlib_capabilities()

        # Mock session behavior
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_capabilities
        self.mock_session.execute.return_value = mock_result
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.get_pricer_capabilities(pricer_id)

        # Verify
        assert result == expected_capabilities
        self.mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_capabilities_instrument_only(self):
        """Test querying capabilities by instrument type only."""
        # Setup
        instrument_type = "swap"
        expected_capabilities = [
            cap for cap in PricerCapability.create_quantlib_capabilities()
            if cap.instrument_type == instrument_type
        ]

        # Mock session behavior
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_capabilities
        self.mock_session.execute.return_value = mock_result
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.query_capabilities(instrument_type=instrument_type)

        # Verify
        assert result == expected_capabilities
        self.mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_capabilities_with_model_and_feature(self):
        """Test querying capabilities with model type and feature requirements."""
        # Setup
        instrument_type = "swap"
        model_type = "Hull-White"
        feature = "greeks"
        expected_capabilities = []  # Mock result

        # Mock session behavior
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = expected_capabilities
        self.mock_session.execute.return_value = mock_result
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.query_capabilities(
            instrument_type=instrument_type,
            model_type=model_type,
            feature=feature
        )

        # Verify
        assert result == expected_capabilities
        self.mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_pricer_capabilities(self):
        """Test deleting all capabilities for a pricer."""
        # Setup
        pricer_id = "quantlib-v1.18"
        capabilities = PricerCapability.create_quantlib_capabilities()[:3]  # Just a few for test

        # Mock session behavior
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = capabilities
        self.mock_session.execute.return_value = mock_result
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.delete_pricer_capabilities(pricer_id)

        # Verify
        assert result == len(capabilities)
        assert self.mock_session.delete.call_count == len(capabilities)
        self.mock_session.commit.assert_called_once()


class TestPricingRepositoryTenantConfigOperations:
    """Test tenant pricing configuration operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repo = PricingRepository()
        self.mock_session = AsyncMock()
        self.repo.session_factory = MagicMock(return_value=self.mock_session)

    @pytest.mark.asyncio
    async def test_get_tenant_pricing_config_found(self):
        """Test getting existing tenant pricing configuration."""
        # Setup
        tenant_id = str(uuid4())
        expected_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        # Mock session behavior
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_config
        self.mock_session.execute.return_value = mock_result
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.get_tenant_pricing_config(tenant_id)

        # Verify
        assert result == expected_config
        self.mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tenant_pricing_config_not_found(self):
        """Test getting non-existent tenant pricing configuration."""
        # Setup
        tenant_id = str(uuid4())

        # Mock session behavior
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_session.execute.return_value = mock_result
        self.mock_session.__aenter__.return_value = self.mock_session
        self.mock_session.__aexit__.return_value = None

        # Execute
        result = await self.repo.get_tenant_pricing_config(tenant_id)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_save_new_tenant_pricing_config(self):
        """Test saving a new tenant pricing configuration."""
        # Setup
        tenant_id = str(uuid4())
        config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        # Mock the get method to return None (no existing config)
        with patch.object(self.repo, 'get_tenant_pricing_config', return_value=None):
            # Mock session behavior
            self.mock_session.__aenter__.return_value = self.mock_session
            self.mock_session.__aexit__.return_value = None

            # Execute
            result = await self.repo.save_tenant_pricing_config(config)

            # Verify
            self.mock_session.add.assert_called_once_with(config)
            self.mock_session.commit.assert_called_once()
            self.mock_session.refresh.assert_called_once()
            assert result == config

    @pytest.mark.asyncio
    async def test_save_existing_tenant_pricing_config(self):
        """Test updating existing tenant pricing configuration."""
        # Setup
        tenant_id = str(uuid4())
        new_config = TenantPricingConfig.create_default_tenant_config(tenant_id)
        existing_config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        # Mock the get method to return existing config
        with patch.object(self.repo, 'get_tenant_pricing_config', return_value=existing_config):
            # Mock session behavior
            self.mock_session.__aenter__.return_value = self.mock_session
            self.mock_session.__aexit__.return_value = None

            # Execute
            result = await self.repo.save_tenant_pricing_config(new_config)

            # Verify
            self.mock_session.add.assert_not_called()  # Should not add new
            self.mock_session.merge.assert_called_once_with(existing_config)
            self.mock_session.commit.assert_called_once()
            assert result == existing_config

    @pytest.mark.asyncio
    async def test_delete_tenant_pricing_config_success(self):
        """Test deleting existing tenant pricing configuration."""
        # Setup
        tenant_id = str(uuid4())
        config = TenantPricingConfig.create_default_tenant_config(tenant_id)

        # Mock the get method to return config
        with patch.object(self.repo, 'get_tenant_pricing_config', return_value=config):
            # Mock session behavior
            self.mock_session.__aenter__.return_value = self.mock_session
            self.mock_session.__aexit__.return_value = None

            # Execute
            result = await self.repo.delete_tenant_pricing_config(tenant_id)

            # Verify
            assert result is True
            self.mock_session.delete.assert_called_once_with(config)
            self.mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tenant_pricing_config_not_found(self):
        """Test deleting non-existent tenant pricing configuration."""
        # Setup
        tenant_id = str(uuid4())

        # Mock the get method to return None
        with patch.object(self.repo, 'get_tenant_pricing_config', return_value=None):
            # Mock session behavior
            self.mock_session.__aenter__.return_value = self.mock_session
            self.mock_session.__aexit__.return_value = None

            # Execute
            result = await self.repo.delete_tenant_pricing_config(tenant_id)

            # Verify
            assert result is False
            self.mock_session.delete.assert_not_called()
            self.mock_session.commit.assert_not_called()


class TestPricingRepositoryHealthOperations:
    """Test health and analytics operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repo = PricingRepository()

    @pytest.mark.asyncio
    async def test_get_healthy_pricers(self):
        """Test getting healthy pricers."""
        expected_pricers = [PricerRegistry.create_quantlib_pricer()]

        with patch.object(self.repo, 'list_pricers', return_value=expected_pricers) as mock_list:
            result = await self.repo.get_healthy_pricers()

            mock_list.assert_called_once_with(status=PricerStatus.HEALTHY.value)
            assert result == expected_pricers

    @pytest.mark.asyncio
    async def test_get_unhealthy_pricers(self):
        """Test getting unhealthy pricers."""
        expected_pricers = []

        with patch.object(self.repo, 'list_pricers', return_value=expected_pricers) as mock_list:
            result = await self.repo.get_unhealthy_pricers()

            mock_list.assert_called_once_with(status=PricerStatus.UNHEALTHY.value)
            assert result == expected_pricers

    @pytest.mark.asyncio
    async def test_get_pricer_statistics(self):
        """Test getting pricer statistics."""
        # Setup
        all_pricers = [
            PricerRegistry.create_quantlib_pricer(),
            PricerRegistry.create_treasury_pricer()
        ]
        healthy_pricers = [PricerRegistry.create_quantlib_pricer()]
        unhealthy_pricers = []
        all_capabilities = PricerCapability.create_quantlib_capabilities()[:5]

        # Mock session behavior
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = all_capabilities
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        self.repo.session_factory = MagicMock(return_value=mock_session)

        with patch.object(self.repo, 'list_pricers', return_value=all_pricers), \
             patch.object(self.repo, 'get_healthy_pricers', return_value=healthy_pricers), \
             patch.object(self.repo, 'get_unhealthy_pricers', return_value=unhealthy_pricers):

            # Execute
            result = await self.repo.get_pricer_statistics()

            # Verify
            assert result["total_pricers"] == 2
            assert result["healthy_pricers"] == 1
            assert result["unhealthy_pricers"] == 0
            assert result["total_capabilities"] == 5
            assert "instruments_supported" in result
            assert "instrument_capability_counts" in result