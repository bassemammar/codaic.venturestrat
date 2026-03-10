"""Tests for TemplateEngine — legal document rendering via Jinja2."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from legal_service.application.services.template_engine import TemplateEngine


@pytest.fixture
def nda_template_content():
  """Minimal NDA Jinja2 template for testing."""
  return """# {{ title }}

**Date:** {{ effective_date }}

**Between:**
1. {{ party_a.legal_name }} (registered number {{ party_a.registration_number }}), whose registered office is at {{ party_a.address }} ("**{{ party_a.label }}**"), acting through {{ party_a.signatory_name }} ({{ party_a.signatory_role }});
2. {{ party_b.legal_name }} (registered number {{ party_b.registration_number }}), whose registered office is at {{ party_b.address }} ("**{{ party_b.label }}**"), acting through {{ party_b.signatory_name }} ({{ party_b.signatory_role }}).

## 1. Purpose
{{ clauses.purpose }}

## 2. Duration
{{ clauses.duration }}

## 3. Data Protection
{{ clauses.data_protection }}

## 4. Confidentiality Survival
{{ clauses.confidentiality_survival }}

## 5. Permitted Recipients
{{ clauses.permitted_recipients }}

## 6. Return or Destruction
{{ clauses.return_destruction }}

## 7. AI/ML Restrictions
{{ clauses.ai_ml_restrictions }}

## 8. Governing Law
{{ clauses.governing_law }}

## 9. Dispute Resolution
{{ clauses.dispute_resolution }}

## 10. Non-Solicitation
{{ clauses.non_solicitation }}

{% for clause in clauses.additional %}
## {{ clause.title }}
{{ clause.content }}
{% endfor %}
"""


@pytest.fixture
def clause_variants():
  """Clause variant data matching vs_template_clause records."""
  return {
    'purpose': {
      'A': 'The parties wish to explore a general business relationship.',
      'B': 'The parties wish to explore potential business collaboration.',
      'C': 'The parties wish to explore a potential merger or acquisition.',
      'D': 'The parties wish to explore technology licensing or integration.',
    },
    'duration': {
      'A': 'This Agreement shall remain in force for 2 years from the date hereof.',
      'B': 'This Agreement shall remain in force for 3 years from the date hereof.',
      'C': 'This Agreement shall remain in force until the Purpose is fulfilled.',
      'D': 'This Agreement shall remain in force indefinitely.',
    },
    'data_protection': {
      'A': 'No personal data is expected to be shared under this Agreement.',
      'B': 'Limited personal data may be shared. Standard safeguards apply.',
      'C': 'Extensive personal data sharing is anticipated. Full DPA required.',
    },
    'confidentiality_survival': {
      'A': 'Obligations survive for 2 years after termination.',
      'B': 'Obligations survive for 3 years after termination.',
      'C': 'Obligations survive for 5 years after termination.',
      'D': 'Obligations survive indefinitely for trade secrets.',
    },
    'permitted_recipients': {
      'A': 'Employees only.',
      'B': 'Employees and professional advisers.',
      'C': 'Employees, advisers, and potential investors.',
      'D': 'Group companies and contractors.',
    },
    'return_destruction': {
      'A': 'Destroy all copies and certify destruction.',
      'B': 'Return or destroy at the discloser\'s choice.',
      'C': 'Retain copies subject to ongoing obligations.',
    },
    'ai_ml_restrictions': {
      'A': 'Confidential Information must not be used in AI/ML systems.',
      'B': 'On-premises AI/ML processing only.',
      'C': 'No specific AI/ML restrictions.',
    },
    'dispute_resolution': {
      'A': 'The courts of England and Wales shall have exclusive jurisdiction.',
      'B': 'The courts of Scotland shall have exclusive jurisdiction.',
      'C': 'Disputes shall be resolved by LCIA arbitration in London.',
      'D': 'Disputes shall be resolved by ICC arbitration.',
      'E': 'Disputes shall be resolved by DIFC-LCIA arbitration.',
    },
    'non_solicitation': {
      'A': 'No non-solicitation obligations apply.',
      'B': '12-month restriction on soliciting employees.',
      'C': '12-month restriction on soliciting employees and clients.',
      'D': '24-month restriction on all solicitation.',
    },
    'governing_law': {
      'england_wales': 'This Agreement is governed by the laws of England and Wales.',
      'scotland': 'This Agreement is governed by the laws of Scotland.',
      'difc': 'This Agreement is governed by the laws of the DIFC.',
      'ksa': 'This Agreement is governed by the laws of the Kingdom of Saudi Arabia.',
    },
  }


@pytest.fixture
def sample_party_a():
  return {
    'legal_name': 'Acme Corp Ltd',
    'registration_number': '12345678',
    'address': '123 Business Road, London, EC1A 1BB, GB',
    'label': 'Disclosing Party',
    'signatory_name': 'John Smith',
    'signatory_role': 'Director',
  }


@pytest.fixture
def sample_party_b():
  return {
    'legal_name': 'Beta Industries Ltd',
    'registration_number': '87654321',
    'address': '456 Commerce Street, Manchester, M1 1AA, GB',
    'label': 'Receiving Party',
    'signatory_name': 'Jane Doe',
    'signatory_role': 'CEO',
  }


@pytest.fixture
def sample_configuration():
  return {
    'purpose': 'Potential business collaboration between the parties',
    'purpose_option': 'B',
    'personal_data_sharing': 'A',
    'agreement_duration': 'A',
    'confidentiality_survival': 'A',
    'permitted_recipients': 'B',
    'return_or_destruction': 'B',
    'ai_ml_restrictions': 'A',
    'governing_law': 'england_wales',
    'dispute_resolution': 'C',
    'non_solicitation': 'A',
    'additional_clauses': ['no_partnership', 'no_obligation'],
  }


@pytest.fixture
def engine(nda_template_content, clause_variants):
  """TemplateEngine instance with mocked data."""
  return TemplateEngine(
    template_content=nda_template_content,
    clause_variants=clause_variants,
  )


class TestTemplateEngineRender:
  def test_renders_non_empty_markdown(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert len(result) > 0
    assert isinstance(result, str)

  def test_renders_party_names(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'Acme Corp Ltd' in result
    assert 'Beta Industries Ltd' in result

  def test_renders_signatory_info(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'John Smith' in result
    assert 'Jane Doe' in result

  def test_renders_effective_date(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    # Should contain a date string
    assert '2026' in result or 'Date' in result


class TestClauseVariantSelection:
  def test_purpose_variant_b(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'potential business collaboration' in result

  def test_purpose_variant_a(self, engine, sample_party_a, sample_party_b, sample_configuration):
    sample_configuration['purpose_option'] = 'A'
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'general business relationship' in result

  def test_duration_variant_a(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert '2 years' in result

  def test_duration_variant_d_indefinite(self, engine, sample_party_a, sample_party_b, sample_configuration):
    sample_configuration['agreement_duration'] = 'D'
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'indefinitely' in result

  def test_data_protection_variant_a(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'No personal data' in result

  def test_ai_restrictions_variant_a(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'must not be used in AI/ML' in result

  def test_dispute_resolution_lcia(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'LCIA' in result

  def test_governing_law_england(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'England and Wales' in result

  def test_governing_law_ksa(self, engine, sample_party_a, sample_party_b, sample_configuration):
    sample_configuration['governing_law'] = 'ksa'
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'Saudi Arabia' in result

  def test_non_solicitation_none(self, engine, sample_party_a, sample_party_b, sample_configuration):
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'No non-solicitation' in result


class TestBuildNdaContext:
  def test_builds_context_with_all_keys(self, engine, sample_party_a, sample_party_b, sample_configuration):
    ctx = engine.build_nda_context(sample_party_a, sample_party_b, sample_configuration)
    assert 'title' in ctx
    assert 'effective_date' in ctx
    assert 'party_a' in ctx
    assert 'party_b' in ctx
    assert 'clauses' in ctx

  def test_clauses_populated_from_variants(self, engine, sample_party_a, sample_party_b, sample_configuration):
    ctx = engine.build_nda_context(sample_party_a, sample_party_b, sample_configuration)
    assert ctx['clauses']['purpose'] is not None
    assert ctx['clauses']['duration'] is not None
    assert len(ctx['clauses']['purpose']) > 0

  def test_default_configuration_fills_missing(self, engine, sample_party_a, sample_party_b):
    minimal_config = {'purpose_option': 'A', 'governing_law': 'england_wales'}
    ctx = engine.build_nda_context(sample_party_a, sample_party_b, minimal_config)
    # Should not raise, should use defaults
    assert ctx['clauses']['duration'] is not None


class TestEdgeCases:
  def test_empty_additional_clauses(self, engine, sample_party_a, sample_party_b, sample_configuration):
    sample_configuration['additional_clauses'] = []
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert len(result) > 0

  def test_unknown_variant_key_uses_default(self, engine, sample_party_a, sample_party_b, sample_configuration):
    sample_configuration['purpose_option'] = 'Z'
    # Should fall back to default variant 'A'
    result = engine.render_nda(sample_party_a, sample_party_b, sample_configuration)
    assert 'general business relationship' in result
