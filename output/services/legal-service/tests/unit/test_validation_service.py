"""Tests for ValidationService — cross-document business rules."""

import pytest
from decimal import Decimal
from legal_service.application.services.validation_service import (
  ValidationService,
  ValidationError,
  ValidationResult,
)


class TestValidateEquity:
  def test_valid_total_under_100(self):
    holdings = [
      {'percentage': Decimal('40.00')},
      {'percentage': Decimal('30.00')},
    ]
    result = ValidationService.validate_equity_total(holdings, authorized_shares=None)
    assert result.valid

  def test_valid_total_exactly_100(self):
    holdings = [
      {'percentage': Decimal('60.00')},
      {'percentage': Decimal('40.00')},
    ]
    result = ValidationService.validate_equity_total(holdings, authorized_shares=None)
    assert result.valid

  def test_invalid_total_over_100(self):
    holdings = [
      {'percentage': Decimal('60.00')},
      {'percentage': Decimal('50.00')},
    ]
    result = ValidationService.validate_equity_total(holdings, authorized_shares=None)
    assert not result.valid
    assert any(e.rule_id == '2.1' for e in result.errors)
    assert any(e.severity == 'CRITICAL' for e in result.errors)

  def test_no_holdings_is_valid(self):
    result = ValidationService.validate_equity_total([], authorized_shares=None)
    assert result.valid

  def test_shares_within_authorized(self):
    holdings = [
      {'percentage': Decimal('50.00'), 'number_of_shares': 500},
      {'percentage': Decimal('30.00'), 'number_of_shares': 300},
    ]
    result = ValidationService.validate_equity_total(holdings, authorized_shares=1000)
    assert result.valid

  def test_shares_exceed_authorized(self):
    holdings = [
      {'percentage': Decimal('50.00'), 'number_of_shares': 600},
      {'percentage': Decimal('30.00'), 'number_of_shares': 500},
    ]
    result = ValidationService.validate_equity_total(holdings, authorized_shares=1000)
    assert not result.valid
    assert any(e.rule_id == '2.2' for e in result.errors)

  def test_null_authorized_shares_skips_share_check(self):
    holdings = [
      {'percentage': Decimal('50.00'), 'number_of_shares': 999999},
    ]
    result = ValidationService.validate_equity_total(holdings, authorized_shares=None)
    assert result.valid


class TestValidatePerson:
  def test_no_warning_when_emails_differ(self):
    existing_founders = [{'email': 'alice@acme.com'}]
    result = ValidationService.validate_person_email(
      email='bob@beta.com',
      existing_founders=existing_founders,
    )
    assert result.valid
    assert len(result.warnings) == 0

  def test_warning_when_email_matches_founder(self):
    existing_founders = [{'email': 'alice@acme.com'}]
    result = ValidationService.validate_person_email(
      email='alice@acme.com',
      existing_founders=existing_founders,
    )
    assert result.valid  # warnings don't block
    assert len(result.warnings) == 1
    assert result.warnings[0].rule_id == '1.3'
    assert result.warnings[0].severity == 'HIGH'

  def test_case_insensitive_match(self):
    existing_founders = [{'email': 'Alice@Acme.com'}]
    result = ValidationService.validate_person_email(
      email='alice@acme.com',
      existing_founders=existing_founders,
    )
    assert len(result.warnings) == 1

  def test_no_founders_no_warning(self):
    result = ValidationService.validate_person_email(
      email='anyone@example.com',
      existing_founders=[],
    )
    assert result.valid
    assert len(result.warnings) == 0


class TestValidateCompanyUpdate:
  def test_allows_name_change_no_documents(self):
    result = ValidationService.validate_company_update(
      field='legal_name',
      has_generated_documents=False,
    )
    assert result.valid

  def test_blocks_name_change_with_documents(self):
    result = ValidationService.validate_company_update(
      field='legal_name',
      has_generated_documents=True,
    )
    assert not result.valid
    assert any(e.rule_id == '1.1' for e in result.errors)
    assert any(e.blocking for e in result.errors)

  def test_blocks_jurisdiction_change_with_documents(self):
    result = ValidationService.validate_company_update(
      field='jurisdiction',
      has_generated_documents=True,
    )
    assert not result.valid
    assert any(e.rule_id == '1.1' for e in result.errors)

  def test_allows_other_field_changes_with_documents(self):
    result = ValidationService.validate_company_update(
      field='authorized_shares',
      has_generated_documents=True,
    )
    assert result.valid


class TestValidationDataclasses:
  def test_validation_error_fields(self):
    err = ValidationError(
      rule_id='2.1',
      severity='CRITICAL',
      message='Total equity exceeds 100%',
      field='percentage',
      blocking=True,
    )
    assert err.rule_id == '2.1'
    assert err.blocking

  def test_validation_result_with_errors(self):
    err = ValidationError('2.1', 'CRITICAL', 'test', 'field', True)
    result = ValidationResult(valid=False, errors=[err], warnings=[])
    assert not result.valid
    assert len(result.errors) == 1

  def test_validation_result_valid(self):
    result = ValidationResult(valid=True, errors=[], warnings=[])
    assert result.valid
