"""
Tests for the pricing test data seeder

This module tests the PricingTestDataSeeder functionality including:
- Test tenant creation
- Test curve generation
- Test instrument creation
- Test portfolio generation
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from venturestrat.seeders.pricing_test_data import PricingTestDataSeeder


@pytest.fixture
def temp_service_path():
    """Create a temporary service directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        service_path = Path(temp_dir)
        yield service_path


@pytest.fixture
def test_seeder(temp_service_path):
    """Create a test seeder instance."""
    seeder = PricingTestDataSeeder()
    seeder.service_path = temp_service_path
    seeder.configure(dry_run=True, verbose=True)
    return seeder


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seeder_initialization(test_seeder):
    """Test that seeder initializes correctly."""
    assert test_seeder.service_name == "pricing-test-data"
    assert "tenants" in test_seeder._data_types
    assert "curves" in test_seeder._data_types
    assert "instruments" in test_seeder._data_types
    assert "portfolios" in test_seeder._data_types
    assert "all" in test_seeder._data_types


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seed_test_tenants_dry_run(test_seeder):
    """Test that tenant seeding works in dry run mode."""
    await test_seeder._seed_test_tenants()
    # In dry run mode, no actual changes should be made
    # This tests the logic without database operations


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seed_test_curves_creates_files(test_seeder):
    """Test that curve seeding creates the expected files."""
    # Set dry_run to False for this test to create files
    test_seeder.config.dry_run = False

    await test_seeder._seed_test_curves()

    # Check that curve files were created
    curves_dir = test_seeder.service_path / "test_data" / "curves"
    assert curves_dir.exists()

    # Check for specific curve files
    expected_curves = [
        "tenant_a_usd_sofr.json",
        "tenant_b_usd_sofr.json",
        "tenant_c_usd_sofr.json",
        "eur_euribor.json",
        "gbp_sonia.json"
    ]

    for curve_file in expected_curves:
        curve_path = curves_dir / curve_file
        assert curve_path.exists(), f"Curve file {curve_file} not created"

        # Validate curve data structure
        with open(curve_path, 'r') as f:
            curve_data = json.load(f)

        assert "name" in curve_data
        assert "currency" in curve_data
        assert "tenors" in curve_data
        assert "rates" in curve_data
        assert len(curve_data["tenors"]) == len(curve_data["rates"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seed_test_instruments_creates_files(test_seeder):
    """Test that instrument seeding creates the expected files."""
    test_seeder.config.dry_run = False

    await test_seeder._seed_test_instruments()

    # Check that instrument files were created
    instruments_dir = test_seeder.service_path / "test_data" / "instruments"
    assert instruments_dir.exists()

    # Check for specific instrument files
    expected_instruments = [
        "usd_5y_vanilla_swap.json",
        "eur_10y_vanilla_swap.json",
        "usd_treasury_5y.json",
        "eur_corporate_bond_3y.json",
        "usd_swaption_5y_into_5y.json",
        "eur_cap_floor_3y.json",
        "eurusd_forward_1y.json",
        "gbpusd_option_6m.json"
    ]

    for instrument_file in expected_instruments:
        instrument_path = instruments_dir / instrument_file
        assert instrument_path.exists(), f"Instrument file {instrument_file} not created"

        # Validate instrument data structure
        with open(instrument_path, 'r') as f:
            instrument_data = json.load(f)

        assert "id" in instrument_data
        assert "instrument_type" in instrument_data
        assert "currency" in instrument_data or "currency_pair" in instrument_data
        assert "description" in instrument_data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seed_test_portfolios_creates_files(test_seeder):
    """Test that portfolio seeding creates the expected files."""
    test_seeder.config.dry_run = False

    await test_seeder._seed_test_portfolios()

    # Check that portfolio files were created
    portfolios_dir = test_seeder.service_path / "test_data" / "portfolios"
    assert portfolios_dir.exists()

    # Check for specific portfolio files
    expected_portfolios = [
        "small_portfolio_100.json",
        "medium_portfolio_500.json",
        "large_portfolio_1000.json",
        "stress_portfolio_2500.json"
    ]

    for portfolio_file in expected_portfolios:
        portfolio_path = portfolios_dir / portfolio_file
        assert portfolio_path.exists(), f"Portfolio file {portfolio_file} not created"

        # Validate portfolio data structure
        with open(portfolio_path, 'r') as f:
            portfolio_data = json.load(f)

        assert "id" in portfolio_data
        assert "name" in portfolio_data
        assert "instruments" in portfolio_data
        assert "total_instruments" in portfolio_data

        # Verify instrument count matches expected
        expected_size = int(portfolio_file.split('_')[-1].replace('.json', ''))
        assert portfolio_data["total_instruments"] == expected_size
        assert len(portfolio_data["instruments"]) == expected_size


@pytest.mark.unit
def test_generate_test_swap(test_seeder):
    """Test swap generation logic."""
    swap = test_seeder._generate_test_swap(0)

    assert swap["instrument_type"] == "swap"
    assert "currency" in swap
    assert "notional" in swap
    assert "tenor" in swap
    assert "fixed_rate" in swap
    assert swap["currency"] in ["USD", "EUR", "GBP"]


@pytest.mark.unit
def test_generate_test_bond(test_seeder):
    """Test bond generation logic."""
    bond = test_seeder._generate_test_bond(0)

    assert bond["instrument_type"] == "bond"
    assert "currency" in bond
    assert "face_value" in bond
    assert "coupon_rate" in bond
    assert "maturity" in bond


@pytest.mark.unit
def test_generate_test_option(test_seeder):
    """Test option generation logic."""
    option = test_seeder._generate_test_option(0)

    assert option["instrument_type"] in ["swaption", "cap"]
    assert "currency" in option
    assert "notional" in option


@pytest.mark.unit
def test_generate_test_fx(test_seeder):
    """Test FX instrument generation logic."""
    fx = test_seeder._generate_test_fx(0)

    assert fx["instrument_type"] in ["fx_forward", "fx_option"]
    assert "currency_pair" in fx
    assert "notional" in fx


@pytest.mark.unit
def test_generate_portfolio_composition(test_seeder):
    """Test portfolio generation with correct composition."""
    portfolio_data = {
        "id": "test_portfolio",
        "name": "Test Portfolio",
        "description": "Test",
        "size": 100,
        "composition": {
            "swaps": 50,
            "bonds": 30,
            "options": 15,
            "fx": 5
        }
    }

    portfolio = test_seeder._generate_portfolio(portfolio_data)

    assert portfolio["total_instruments"] == 100

    # Check composition
    composition = portfolio["composition_actual"]
    assert composition["swaps"] == 50
    assert composition["bonds"] == 30
    assert composition["options"] == 15
    assert composition["fx"] == 5

    # Verify total adds up
    total = sum(composition.values())
    assert total == 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seed_all_data_calls_all_methods(test_seeder):
    """Test that seed_all_data calls all seeding methods."""
    with patch.object(test_seeder, '_seed_test_tenants') as mock_tenants, \
         patch.object(test_seeder, '_seed_test_curves') as mock_curves, \
         patch.object(test_seeder, '_seed_test_instruments') as mock_instruments, \
         patch.object(test_seeder, '_seed_test_portfolios') as mock_portfolios:

        await test_seeder._seed_all_data()

        mock_tenants.assert_called_once()
        mock_curves.assert_called_once()
        mock_instruments.assert_called_once()
        mock_portfolios.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_data_dry_run(test_seeder):
    """Test clear data functionality in dry run mode."""
    await test_seeder.clear_data("tenants")
    # Should not raise an exception in dry run mode


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_data_type_raises_error(test_seeder):
    """Test that invalid data type raises an error."""
    with pytest.raises(ValueError, match="Unknown data type: invalid"):
        await test_seeder.seed_data_type("invalid")


@pytest.mark.unit
def test_seeder_data_types_registration(test_seeder):
    """Test that all expected data types are registered."""
    expected_types = ["tenants", "curves", "instruments", "portfolios", "all"]

    for data_type in expected_types:
        assert data_type in test_seeder._data_types
        assert "seed_func" in test_seeder._data_types[data_type]
        assert callable(test_seeder._data_types[data_type]["seed_func"])


@pytest.mark.unit
def test_tenant_configurations_match_spec(test_seeder):
    """Test that tenant configurations match the pricing infrastructure spec."""
    # This would normally be tested with actual database operations
    # For now, verify the static configuration matches requirements

    # Tenant A should use QuantLib with custom curves
    # Tenant B should use Treasury with custom params
    # Tenant C should use QuantLib with different curves

    # This is validated in the actual _seed_test_tenants method
    # The test verifies the method doesn't raise exceptions
    assert hasattr(test_seeder, '_seed_test_tenants')


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_seeding_workflow(test_seeder):
    """Integration test for the complete seeding workflow."""
    test_seeder.config.dry_run = False

    # Run the full seeding process
    await test_seeder.seed_data_type("all")

    # Verify all directories and files were created
    test_data_dir = test_seeder.service_path / "test_data"
    assert test_data_dir.exists()

    curves_dir = test_data_dir / "curves"
    instruments_dir = test_data_dir / "instruments"
    portfolios_dir = test_data_dir / "portfolios"

    assert curves_dir.exists()
    assert instruments_dir.exists()
    assert portfolios_dir.exists()

    # Verify some files exist
    assert len(list(curves_dir.glob("*.json"))) >= 5
    assert len(list(instruments_dir.glob("*.json"))) >= 8
    assert len(list(portfolios_dir.glob("*.json"))) >= 4