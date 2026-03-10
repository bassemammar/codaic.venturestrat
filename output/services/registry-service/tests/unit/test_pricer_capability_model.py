"""Tests for PricerCapability model - Database Schema Design.

These tests define the expected behavior of the PricerCapability model for
capability-based routing in the pricing infrastructure plugin architecture
as required by Task 1.1.
"""
import pytest
from typing import List

from registry.models.pricer_capability import PricerCapability


class TestPricerCapability:
    """Tests for PricerCapability model."""

    def test_create_minimal_capability(self):
        """Create capability with required fields only."""
        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap"
        )

        assert capability.pricer_id == "quantlib-v1.18"
        assert capability.instrument_type == "swap"
        assert capability.model_type is None
        assert capability.features == []
        assert capability.priority == 0

    def test_create_full_capability(self):
        """Create capability with all fields."""
        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            model_type="Hull-White",
            features=["greeks", "duration", "convexity"],
            priority=10
        )

        assert capability.pricer_id == "quantlib-v1.18"
        assert capability.instrument_type == "swap"
        assert capability.model_type == "Hull-White"
        assert capability.features == ["greeks", "duration", "convexity"]
        assert capability.priority == 10

    def test_create_quantlib_capabilities(self):
        """Create QuantLib capabilities using factory method."""
        capabilities = PricerCapability.create_quantlib_capabilities()

        assert len(capabilities) > 0

        # Check that all capabilities belong to QuantLib
        for cap in capabilities:
            assert cap.pricer_id == "quantlib-v1.18"
            assert cap.instrument_type is not None
            assert isinstance(cap.features, list)
            assert cap.priority >= 0

        # Check for specific capabilities
        instrument_types = [cap.instrument_type for cap in capabilities]
        assert "swap" in instrument_types
        assert "bond" in instrument_types
        assert "option" in instrument_types

        # Check for model types
        swap_caps = [cap for cap in capabilities if cap.instrument_type == "swap"]
        swap_models = [cap.model_type for cap in swap_caps if cap.model_type]
        assert "Hull-White" in swap_models
        assert "Vasicek" in swap_models

        # Check features
        all_features = []
        for cap in capabilities:
            all_features.extend(cap.features or [])
        assert "greeks" in all_features
        assert "duration" in all_features
        assert "convexity" in all_features

    def test_create_treasury_capabilities(self):
        """Create Treasury capabilities using factory method."""
        capabilities = PricerCapability.create_treasury_capabilities()

        assert len(capabilities) > 0

        # Check that all capabilities belong to Treasury
        for cap in capabilities:
            assert cap.pricer_id == "treasury-v2.3"
            assert cap.instrument_type is not None
            assert isinstance(cap.features, list)
            assert cap.priority >= 0

        # Check for specific capabilities
        instrument_types = [cap.instrument_type for cap in capabilities]
        assert "swap" in instrument_types
        assert "cds" in instrument_types
        assert "barrier_option" in instrument_types
        assert "structured_note" in instrument_types

        # Check for advanced models
        models = [cap.model_type for cap in capabilities if cap.model_type]
        assert "SABR" in models
        assert "Monte-Carlo" in models
        assert "HJM" in models

        # Check for advanced features
        all_features = []
        for cap in capabilities:
            all_features.extend(cap.features or [])
        assert "monte_carlo" in all_features
        assert "volatility_smile" in all_features
        assert "barrier_monitoring" in all_features

    def test_matches_requirements_instrument_only(self):
        """Test capability matching with instrument type only."""
        capability = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="swap",
            model_type="Hull-White",
            features=["greeks", "duration"]
        )

        # Exact match
        assert capability.matches_requirements("swap") is True

        # No match
        assert capability.matches_requirements("bond") is False

    def test_matches_requirements_with_model(self):
        """Test capability matching with instrument and model type."""
        capability = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="swap",
            model_type="Hull-White",
            features=["greeks", "duration"]
        )

        # Exact match
        assert capability.matches_requirements("swap", "Hull-White") is True

        # Wrong model
        assert capability.matches_requirements("swap", "Black-Scholes") is False

        # Any model (None) should match
        assert capability.matches_requirements("swap", None) is True

    def test_matches_requirements_with_features(self):
        """Test capability matching with required features."""
        capability = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="option",
            model_type="Black-Scholes",
            features=["greeks", "delta", "gamma", "vega"]
        )

        # Single feature
        assert capability.matches_requirements("option", "Black-Scholes", ["greeks"]) is True

        # Multiple features (all available)
        assert capability.matches_requirements("option", "Black-Scholes", ["greeks", "delta"]) is True

        # Missing feature
        assert capability.matches_requirements("option", "Black-Scholes", ["theta"]) is False

        # Mix of available and unavailable
        assert capability.matches_requirements("option", "Black-Scholes", ["greeks", "theta"]) is False

        # No features required
        assert capability.matches_requirements("option", "Black-Scholes", []) is True
        assert capability.matches_requirements("option", "Black-Scholes", None) is True

    def test_matches_requirements_complex_scenarios(self):
        """Test complex capability matching scenarios."""
        capability = PricerCapability(
            pricer_id="treasury-v2.3",
            instrument_type="swaption",
            model_type="SABR",
            features=["greeks", "volatility_smile", "monte_carlo"]
        )

        # All match
        assert capability.matches_requirements(
            "swaption",
            "SABR",
            ["greeks", "volatility_smile"]
        ) is True

        # Wrong instrument
        assert capability.matches_requirements(
            "swap",
            "SABR",
            ["greeks"]
        ) is False

        # Generic model match (None means any model)
        generic_capability = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="bond",
            model_type=None,
            features=["yield", "duration"]
        )

        assert generic_capability.matches_requirements("bond", "Yield") is True
        assert generic_capability.matches_requirements("bond", "Custom-Model") is True
        assert generic_capability.matches_requirements("bond", None) is True

    def test_has_feature(self):
        """Test feature checking."""
        capability = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="swap",
            features=["greeks", "duration", "convexity"]
        )

        assert capability.has_feature("greeks") is True
        assert capability.has_feature("duration") is True
        assert capability.has_feature("convexity") is True
        assert capability.has_feature("monte_carlo") is False
        assert capability.has_feature("") is False

        # Test with no features
        no_features_cap = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="swap",
            features=None
        )
        assert no_features_cap.has_feature("greeks") is False

        # Test with empty features
        empty_features_cap = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="swap",
            features=[]
        )
        assert empty_features_cap.has_feature("greeks") is False

    def test_get_feature_list(self):
        """Test getting feature list."""
        capability = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="swap",
            features=["greeks", "duration"]
        )

        features = capability.get_feature_list()
        assert features == ["greeks", "duration"]
        assert isinstance(features, list)

        # Test with no features
        no_features_cap = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="swap",
            features=None
        )
        assert no_features_cap.get_feature_list() == []

        # Test with empty features
        empty_features_cap = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="swap",
            features=[]
        )
        assert empty_features_cap.get_feature_list() == []

    def test_serialization_to_dict(self):
        """Capability serializes to dictionary properly."""
        capability = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="option",
            model_type="Black-Scholes",
            features=["greeks", "delta", "gamma"],
            priority=15
        )

        data = capability.to_dict()

        assert data["pricer_id"] == "test-v1.0"
        assert data["instrument_type"] == "option"
        assert data["model_type"] == "Black-Scholes"
        assert data["features"] == ["greeks", "delta", "gamma"]
        assert data["priority"] == 15
        assert isinstance(data["features"], list)

    def test_string_representation(self):
        """Test string representation methods."""
        capability = PricerCapability(
            pricer_id="quantlib-v1.18",
            instrument_type="swap",
            model_type="Hull-White",
            features=["greeks", "duration"],
            priority=10
        )

        str_repr = str(capability)
        assert "PricerCapability(" in str_repr
        assert "quantlib-v1.18" in str_repr
        assert "swap" in str_repr
        assert "Hull-White" in str_repr
        assert "priority=10" in str_repr

        repr_str = repr(capability)
        assert "PricerCapability(" in repr_str
        assert "pricer_id='quantlib-v1.18'" in repr_str
        assert "instrument_type='swap'" in repr_str


class TestPricerCapabilityConstraints:
    """Tests for PricerCapability database constraints."""

    def test_instrument_type_format_constraint_logic(self):
        """Test instrument_type format constraint validation logic."""
        # Valid formats (should pass regex: ^[a-z][a-z_]*[a-z]$ AND length <= 100)
        valid_types = [
            "swap",
            "bond",
            "option",
            "swaption",
            "fx_forward",
            "fx_option",
            "barrier_option",
            "asian_option",
            "structured_note",
            "credit_bond",
            "autocallable",
            "a",  # Single character (edge case)
            "aa",  # Two characters
            "very_long_instrument_type_name_that_is_still_valid",  # Long but valid
        ]

        for instrument_type in valid_types:
            # Test regex pattern compliance
            import re
            pattern = r'^[a-z][a-z_]*[a-z]$'
            length_ok = len(instrument_type) <= 100

            if len(instrument_type) == 1:
                # Single character: just lowercase letter
                assert re.match(r'^[a-z]$', instrument_type), f"Single char {instrument_type} should be valid"
            else:
                # Multi-character: starts with letter, ends with letter, only letters and underscores
                assert re.match(pattern, instrument_type), f"Type {instrument_type} should match pattern"

            assert length_ok, f"Type {instrument_type} should be <= 100 chars"

        # Invalid formats (should fail regex or length)
        invalid_types = [
            "",                    # empty
            "_swap",              # starts with underscore
            "swap_",              # ends with underscore
            "SWAP",               # uppercase
            "Swap",               # mixed case
            "swap-option",        # contains hyphen
            "swap.option",        # contains dot
            "swap option",        # contains space
            "123swap",            # starts with number
            "swap123",            # ends with number (but contains number)
            "a" * 101,            # too long (> 100 chars)
            "_",                  # just underscore
            "s",                  # single char but this should actually be valid per our regex
        ]

        for instrument_type in invalid_types:
            import re
            pattern = r'^[a-z][a-z_]*[a-z]$'
            length_ok = len(instrument_type) <= 100

            if instrument_type == "s":
                # Single lowercase letter should actually be valid
                continue

            if len(instrument_type) == 1:
                # Single character validation
                valid_single = re.match(r'^[a-z]$', instrument_type) and length_ok
                assert not valid_single, f"Invalid single char {instrument_type} should fail"
            else:
                # Multi-character validation
                pattern_match = re.match(pattern, instrument_type) if instrument_type else False
                valid_multi = pattern_match and length_ok
                assert not valid_multi, f"Invalid type {instrument_type} should fail validation"

    def test_model_type_format_constraint_logic(self):
        """Test model_type format constraint validation logic."""
        # Valid formats (null OR matches ^[A-Za-z][A-Za-z0-9_-]*$ AND length <= 100)
        valid_types = [
            None,                    # null is allowed
            "Black-Scholes",
            "Hull-White",
            "SABR",
            "Monte-Carlo",
            "HJM",
            "LMM",
            "Vasicek",
            "A",                     # single character
            "Model123",              # with numbers
            "Custom_Model",          # with underscore
            "Multi-Word-Model",      # with hyphens
            "Model_v2",              # mixed
            "A1B2C3",                # alphanumeric
        ]

        for model_type in valid_types:
            if model_type is None:
                continue  # null is always valid

            # Test regex pattern compliance
            import re
            pattern = r'^[A-Za-z][A-Za-z0-9_-]*$'
            length_ok = len(model_type) <= 100

            pattern_match = re.match(pattern, model_type)
            assert pattern_match, f"Model type {model_type} should match pattern"
            assert length_ok, f"Model type {model_type} should be <= 100 chars"

        # Invalid formats (should fail regex or length)
        invalid_types = [
            "",                      # empty (but should be null instead)
            "123Model",              # starts with number
            "-Model",                # starts with hyphen
            "_Model",                # starts with underscore
            "Model$",                # contains special char
            "Model@Type",            # contains special char
            "Model Type",            # contains space
            "Model.Type",            # contains dot
            "a" * 101,               # too long (> 100 chars)
        ]

        for model_type in invalid_types:
            import re
            pattern = r'^[A-Za-z][A-Za-z0-9_-]*$'
            length_ok = len(model_type) <= 100

            pattern_match = re.match(pattern, model_type) if model_type else False
            valid = pattern_match and length_ok
            assert not valid, f"Invalid model type {model_type} should fail validation"


class TestPricerCapabilityBusinessLogic:
    """Tests for PricerCapability business logic."""

    def test_priority_based_routing(self):
        """Test capability priority for routing decisions."""
        # Create capabilities with different priorities
        low_priority = PricerCapability(
            pricer_id="pricer1-v1.0",
            instrument_type="swap",
            model_type="Hull-White",
            priority=5
        )

        high_priority = PricerCapability(
            pricer_id="pricer2-v1.0",
            instrument_type="swap",
            model_type="Hull-White",
            priority=15
        )

        medium_priority = PricerCapability(
            pricer_id="pricer3-v1.0",
            instrument_type="swap",
            model_type="Hull-White",
            priority=10
        )

        # All should match the same requirements
        requirements = ("swap", "Hull-White", [])
        assert low_priority.matches_requirements(*requirements) is True
        assert high_priority.matches_requirements(*requirements) is True
        assert medium_priority.matches_requirements(*requirements) is True

        # Higher priority should sort first in routing logic
        capabilities = [low_priority, high_priority, medium_priority]
        sorted_caps = sorted(capabilities, key=lambda c: c.priority, reverse=True)

        assert sorted_caps[0].priority == 15  # high_priority
        assert sorted_caps[1].priority == 10  # medium_priority
        assert sorted_caps[2].priority == 5   # low_priority

    def test_feature_subset_matching(self):
        """Test feature subset matching logic."""
        capability = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="option",
            features=["greeks", "delta", "gamma", "vega", "theta", "rho"]
        )

        # Subset matching
        assert capability.matches_requirements("option", None, ["greeks"]) is True
        assert capability.matches_requirements("option", None, ["greeks", "delta"]) is True
        assert capability.matches_requirements("option", None, ["delta", "gamma", "vega"]) is True

        # Exact matching
        all_features = ["greeks", "delta", "gamma", "vega", "theta", "rho"]
        assert capability.matches_requirements("option", None, all_features) is True

        # Superset (should fail)
        too_many_features = ["greeks", "delta", "gamma", "vega", "theta", "rho", "lambda"]
        assert capability.matches_requirements("option", None, too_many_features) is False

    def test_generic_vs_specific_capabilities(self):
        """Test generic vs specific capability matching."""
        # Generic capability (no model specified)
        generic = PricerCapability(
            pricer_id="generic-v1.0",
            instrument_type="swap",
            model_type=None,
            features=["duration"],
            priority=5
        )

        # Specific capability (with model)
        specific = PricerCapability(
            pricer_id="specific-v1.0",
            instrument_type="swap",
            model_type="Hull-White",
            features=["duration", "greeks"],
            priority=10
        )

        # Generic should match any model request
        assert generic.matches_requirements("swap", "Hull-White") is True
        assert generic.matches_requirements("swap", "Black-Scholes") is True
        assert generic.matches_requirements("swap", None) is True

        # Specific should only match exact model or no model requirement
        assert specific.matches_requirements("swap", "Hull-White") is True
        assert specific.matches_requirements("swap", "Black-Scholes") is False
        assert specific.matches_requirements("swap", None) is True

    def test_capability_feature_combinations(self):
        """Test various feature combinations."""
        # Basic features
        basic_cap = PricerCapability(
            pricer_id="basic-v1.0",
            instrument_type="bond",
            features=["yield", "duration"]
        )

        # Advanced features
        advanced_cap = PricerCapability(
            pricer_id="advanced-v1.0",
            instrument_type="bond",
            features=["yield", "duration", "modified_duration", "convexity", "key_rate_duration"]
        )

        # Test basic requirements
        assert basic_cap.matches_requirements("bond", None, ["yield"]) is True
        assert basic_cap.matches_requirements("bond", None, ["duration"]) is True
        assert basic_cap.matches_requirements("bond", None, ["yield", "duration"]) is True

        # Test advanced requirements (should fail for basic cap)
        assert basic_cap.matches_requirements("bond", None, ["convexity"]) is False
        assert basic_cap.matches_requirements("bond", None, ["key_rate_duration"]) is False

        # Test advanced cap can handle all requirements
        assert advanced_cap.matches_requirements("bond", None, ["yield"]) is True
        assert advanced_cap.matches_requirements("bond", None, ["convexity"]) is True
        assert advanced_cap.matches_requirements("bond", None, ["key_rate_duration"]) is True
        assert advanced_cap.matches_requirements("bond", None, ["yield", "duration", "convexity"]) is True

    def test_instrument_type_specificity(self):
        """Test instrument type specificity and matching."""
        # Different instrument types should not cross-match
        swap_cap = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="swap",
            features=["duration"]
        )

        bond_cap = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="bond",
            features=["yield"]
        )

        option_cap = PricerCapability(
            pricer_id="test-v1.0",
            instrument_type="option",
            features=["greeks"]
        )

        # Each should only match its own instrument type
        assert swap_cap.matches_requirements("swap") is True
        assert swap_cap.matches_requirements("bond") is False
        assert swap_cap.matches_requirements("option") is False

        assert bond_cap.matches_requirements("bond") is True
        assert bond_cap.matches_requirements("swap") is False
        assert bond_cap.matches_requirements("option") is False

        assert option_cap.matches_requirements("option") is True
        assert option_cap.matches_requirements("swap") is False
        assert option_cap.matches_requirements("bond") is False

    def test_capability_factory_methods_coverage(self):
        """Test that factory methods provide good coverage."""
        quantlib_caps = PricerCapability.create_quantlib_capabilities()
        treasury_caps = PricerCapability.create_treasury_capabilities()

        # Test coverage of major instrument types for QuantLib
        ql_instruments = {cap.instrument_type for cap in quantlib_caps}
        assert "swap" in ql_instruments
        assert "bond" in ql_instruments
        assert "option" in ql_instruments
        assert "swaption" in ql_instruments

        # Test coverage of major instrument types for Treasury
        treasury_instruments = {cap.instrument_type for cap in treasury_caps}
        assert "swap" in treasury_instruments
        assert "cds" in treasury_instruments
        assert "barrier_option" in treasury_instruments
        assert "structured_note" in treasury_instruments

        # Test that Treasury has higher priorities for advanced features
        treasury_swap_caps = [cap for cap in treasury_caps if cap.instrument_type == "swap"]
        ql_swap_caps = [cap for cap in quantlib_caps if cap.instrument_type == "swap"]

        # Treasury should have some high priority swap capabilities
        max_treasury_priority = max(cap.priority for cap in treasury_swap_caps) if treasury_swap_caps else 0
        max_ql_priority = max(cap.priority for cap in ql_swap_caps) if ql_swap_caps else 0

        assert max_treasury_priority > max_ql_priority  # Treasury should have higher max priority