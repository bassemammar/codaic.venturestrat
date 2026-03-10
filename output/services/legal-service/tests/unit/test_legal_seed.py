"""Tests for seed data — NDA template and clause categories."""

import sys
import os
import pytest

# Add seeds dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'seeds'))

from legal_seed import (
  get_template_seed,
  get_clause_seeds,
  get_clause_variants_dict,
  NDA_TEMPLATE_CONTENT,
  CLAUSE_SEEDS,
)


class TestTemplateSeed:
  def test_template_has_non_empty_content(self):
    seed = get_template_seed()
    assert len(seed['template_content']) > 100

  def test_template_has_jinja2_variables(self):
    seed = get_template_seed()
    content = seed['template_content']
    assert '{{ title }}' in content
    assert '{{ party_a.legal_name }}' in content
    assert '{{ party_b.legal_name }}' in content
    assert '{{ clauses.purpose }}' in content

  def test_template_is_mutual_nda(self):
    seed = get_template_seed()
    assert seed['document_type'] == 'mutual_nda'
    assert seed['jurisdiction'] == 'england_wales'
    assert 'Mutual NDA' in seed['name']

  def test_template_is_active(self):
    seed = get_template_seed()
    assert seed['is_active'] is True

  def test_template_has_configuration_schema(self):
    seed = get_template_seed()
    schema = seed['configuration_schema']
    assert 'required' in schema
    assert 'purpose_option' in schema['required']
    assert len(schema['required']) >= 10

  def test_template_has_all_clause_references(self):
    """Template content should reference all 11 clause categories."""
    content = NDA_TEMPLATE_CONTENT
    expected = [
      'clauses.purpose', 'clauses.data_protection', 'clauses.duration',
      'clauses.confidentiality_survival', 'clauses.permitted_recipients',
      'clauses.return_destruction', 'clauses.ai_ml_restrictions',
      'clauses.governing_law', 'clauses.dispute_resolution',
      'clauses.non_solicitation', 'clauses.additional',
    ]
    for ref in expected:
      assert ref in content, f'Template missing reference to {ref}'

  def test_template_has_signature_block(self):
    content = NDA_TEMPLATE_CONTENT
    assert 'Signature' in content
    assert 'party_a.signatory_name' in content
    assert 'party_b.signatory_name' in content


class TestClauseSeeds:
  def test_all_11_categories_loaded(self):
    seeds = get_clause_seeds()
    assert len(seeds) == 11

  def test_each_clause_has_at_least_2_variants(self):
    seeds = get_clause_seeds()
    for clause in seeds:
      assert len(clause['variants']) >= 2, (
        f'Clause {clause["category"]} has only {len(clause["variants"])} variant(s)'
      )

  def test_clause_categories_are_unique(self):
    seeds = get_clause_seeds()
    categories = [c['category'] for c in seeds]
    assert len(categories) == len(set(categories))

  def test_expected_categories_present(self):
    seeds = get_clause_seeds()
    categories = {c['category'] for c in seeds}
    expected = {
      'purpose', 'data_protection', 'duration', 'confidentiality_survival',
      'permitted_recipients', 'return_destruction', 'ai_ml_restrictions',
      'dispute_resolution', 'non_solicitation', 'governing_law', 'additional',
    }
    assert categories == expected

  def test_variant_counts_match_spec(self):
    """Verify variant counts match the spec requirements."""
    seeds = get_clause_seeds()
    expected_counts = {
      'purpose': 4,
      'data_protection': 3,
      'duration': 4,
      'confidentiality_survival': 4,
      'permitted_recipients': 4,
      'return_destruction': 3,
      'ai_ml_restrictions': 3,
      'dispute_resolution': 5,
      'non_solicitation': 4,
      'governing_law': 4,
      'additional': 4,
    }
    for clause in seeds:
      expected = expected_counts[clause['category']]
      actual = len(clause['variants'])
      assert actual == expected, (
        f'{clause["category"]}: expected {expected} variants, got {actual}'
      )

  def test_clauses_have_sort_order(self):
    seeds = get_clause_seeds()
    orders = [c['sort_order'] for c in seeds]
    assert orders == sorted(orders)

  def test_each_variant_has_label_and_content(self):
    seeds = get_clause_seeds()
    for clause in seeds:
      for key, variant in clause['variants'].items():
        assert 'label' in variant, f'{clause["category"]}.{key} missing label'
        assert 'content' in variant, f'{clause["category"]}.{key} missing content'
        assert len(variant['content']) > 10, f'{clause["category"]}.{key} content too short'

  def test_all_clauses_apply_to_mutual_nda(self):
    seeds = get_clause_seeds()
    for clause in seeds:
      assert 'mutual_nda' in clause['applicable_document_types'], (
        f'{clause["category"]} not applicable to mutual_nda'
      )


class TestClauseVariantsDict:
  def test_returns_all_categories(self):
    variants = get_clause_variants_dict()
    assert len(variants) == 11

  def test_variants_are_plain_strings(self):
    """TemplateEngine expects {category: {key: content_string}}."""
    variants = get_clause_variants_dict()
    for category, options in variants.items():
      for key, content in options.items():
        assert isinstance(content, str), (
          f'{category}.{key} is {type(content)}, expected str'
        )

  def test_integrates_with_template_engine(self):
    """Verify seed data works with TemplateEngine."""
    from legal_service.application.services.template_engine import TemplateEngine

    variants = get_clause_variants_dict()
    engine = TemplateEngine(NDA_TEMPLATE_CONTENT, variants)

    party_a = {
      'legal_name': 'Acme Corp', 'registration_number': '12345678',
      'address': '1 London Road', 'label': 'Party A',
      'signatory_name': 'Jane Doe', 'signatory_role': 'Director',
    }
    party_b = {
      'legal_name': 'Beta Inc', 'registration_number': '87654321',
      'address': '2 Manchester Ave', 'label': 'Party B',
      'signatory_name': 'John Smith', 'signatory_role': 'CEO',
    }

    rendered = engine.render_nda(party_a, party_b, {})
    assert 'Acme Corp' in rendered
    assert 'Beta Inc' in rendered
    assert len(rendered) > 500

  def test_all_default_variants_exist(self):
    """Each clause's default_variant key must exist in its variants."""
    for clause in CLAUSE_SEEDS:
      default = clause['default_variant']
      assert default in clause['variants'], (
        f'{clause["category"]}: default_variant "{default}" not in variants'
      )
