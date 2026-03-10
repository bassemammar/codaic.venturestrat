"""TemplateEngine — Jinja2-based legal document rendering.

Renders legal documents (NDA, founders agreement, etc.) from Jinja2 templates
with conditional clause selection based on user configuration.
"""

from datetime import date
from typing import Any
from jinja2 import Environment, BaseLoader


# Default configuration values when user doesn't provide them
DEFAULT_NDA_CONFIG = {
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
  'additional_clauses': [],
}

# Additional clause definitions
ADDITIONAL_CLAUSES = {
  'no_partnership': {
    'title': 'No Partnership',
    'content': 'Nothing in this Agreement creates a partnership, joint venture, or agency relationship between the parties.',
  },
  'no_obligation': {
    'title': 'No Obligation to Proceed',
    'content': 'Nothing in this Agreement obliges either party to enter into any further agreement or transaction.',
  },
  'publicity': {
    'title': 'Publicity',
    'content': 'Neither party shall make any public announcement regarding this Agreement without prior written consent.',
  },
  'residual_info': {
    'title': 'Residual Information',
    'content': 'Nothing in this Agreement prevents either party from using residual information retained in unaided memory.',
  },
}


class TemplateEngine:
  """Renders legal documents from Jinja2 templates with clause variant selection."""

  def __init__(
    self,
    template_content: str,
    clause_variants: dict[str, dict[str, str]],
  ):
    self.template_content = template_content
    self.clause_variants = clause_variants
    self.env = Environment(
      loader=BaseLoader(),
      autoescape=False,
      trim_blocks=True,
      lstrip_blocks=True,
    )

  def _get_variant(self, category: str, key: str) -> str:
    """Get clause variant content, falling back to first variant if key unknown."""
    variants = self.clause_variants.get(category, {})
    if key in variants:
      return variants[key]
    # Fall back to first variant
    if variants:
      first_key = next(iter(variants))
      return variants[first_key]
    return ''

  def build_nda_context(
    self,
    party_a: dict[str, Any],
    party_b: dict[str, Any],
    configuration: dict[str, Any],
  ) -> dict[str, Any]:
    """Build Jinja2 template context from party data and configuration.

    Args:
      party_a: Dict with legal_name, registration_number, address, label,
               signatory_name, signatory_role
      party_b: Same structure as party_a
      configuration: User-selected clause options (purpose_option, etc.)

    Returns:
      Complete template context dict ready for Jinja2 rendering.
    """
    # Merge with defaults for missing keys
    config = {**DEFAULT_NDA_CONFIG, **configuration}

    # Resolve clause variants
    clauses = {
      'purpose': self._get_variant('purpose', config['purpose_option']),
      'duration': self._get_variant('duration', config['agreement_duration']),
      'data_protection': self._get_variant('data_protection', config['personal_data_sharing']),
      'confidentiality_survival': self._get_variant('confidentiality_survival', config['confidentiality_survival']),
      'permitted_recipients': self._get_variant('permitted_recipients', config['permitted_recipients']),
      'return_destruction': self._get_variant('return_destruction', config['return_or_destruction']),
      'ai_ml_restrictions': self._get_variant('ai_ml_restrictions', config['ai_ml_restrictions']),
      'governing_law': self._get_variant('governing_law', config['governing_law']),
      'dispute_resolution': self._get_variant('dispute_resolution', config['dispute_resolution']),
      'non_solicitation': self._get_variant('non_solicitation', config['non_solicitation']),
      'additional': [
        ADDITIONAL_CLAUSES[c]
        for c in config.get('additional_clauses', [])
        if c in ADDITIONAL_CLAUSES
      ],
    }

    return {
      'title': 'Mutual Non-Disclosure Agreement',
      'effective_date': date.today().strftime('%d %B %Y'),
      'party_a': party_a,
      'party_b': party_b,
      'clauses': clauses,
    }

  def render_nda(
    self,
    party_a: dict[str, Any],
    party_b: dict[str, Any],
    configuration: dict[str, Any],
  ) -> str:
    """Render NDA document as markdown.

    Args:
      party_a: Party A data dict
      party_b: Party B data dict
      configuration: NDA configuration with clause selections

    Returns:
      Rendered markdown string.
    """
    context = self.build_nda_context(party_a, party_b, configuration)
    template = self.env.from_string(self.template_content)
    return template.render(**context)
