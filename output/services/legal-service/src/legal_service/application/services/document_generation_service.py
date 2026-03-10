"""DocumentGenerationService — orchestrates preview, generate, download, validate.

Wires together TemplateEngine, DOCXGenerator, ValidationService, and the
codegen-generated CRUD services to implement the document generation workflow.
"""

import os
import math
from datetime import datetime
from io import BytesIO
from typing import Any
from uuid import uuid4

import structlog
from fastapi import HTTPException

from legal_service.application.services.template_engine import TemplateEngine
from legal_service.application.services.docx_generator import DOCXGenerator
from legal_service.application.services.validation_service import (
  ValidationService,
  ValidationResult,
)
from legal_service.application.services.legal_entity_service import LegalEntityService
from legal_service.application.services.contact_person_service import ContactPersonService

logger = structlog.get_logger(__name__)

# Placeholder template content — will be replaced by seed data (Wave 5)
FALLBACK_TEMPLATE = """# {{ title }}

**Date:** {{ effective_date }}

## Parties

**{{ party_a.label }}:** {{ party_a.legal_name }} ({{ party_a.registration_number }})
Address: {{ party_a.address }}
Signatory: {{ party_a.signatory_name }}, {{ party_a.signatory_role }}

**{{ party_b.label }}:** {{ party_b.legal_name }} ({{ party_b.registration_number }})
Address: {{ party_b.address }}
Signatory: {{ party_b.signatory_name }}, {{ party_b.signatory_role }}

## 1. Purpose

{{ clauses.purpose }}

## 2. Data Protection

{{ clauses.data_protection }}

## 3. Duration

{{ clauses.duration }}

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

{% if clauses.additional %}
## Additional Clauses

{% for clause in clauses.additional %}
### {{ clause.title }}

{{ clause.content }}

{% endfor %}
{% endif %}

## Signatures

______________________________
{{ party_a.signatory_name }}
{{ party_a.signatory_role }}
{{ party_a.legal_name }}

______________________________
{{ party_b.signatory_name }}
{{ party_b.signatory_role }}
{{ party_b.legal_name }}
"""

# Fallback clause variants — will be replaced by seed data (Wave 5)
FALLBACK_CLAUSE_VARIANTS: dict[str, dict[str, str]] = {
  'purpose': {
    'A': 'The parties wish to explore a potential business relationship.',
    'B': 'The parties wish to explore potential business collaboration and exchange confidential information.',
    'C': 'The parties wish to evaluate a potential investment opportunity.',
    'D': 'The parties wish to discuss a potential merger or acquisition.',
  },
  'data_protection': {
    'A': 'Each party shall comply with applicable data protection legislation.',
    'B': 'The parties acknowledge that personal data may be shared and shall comply with GDPR.',
    'C': 'No personal data shall be shared under this Agreement.',
  },
  'duration': {
    'A': 'This Agreement shall remain in force for 2 years from the date hereof.',
    'B': 'This Agreement shall remain in force for 3 years from the date hereof.',
    'C': 'This Agreement shall remain in force for 5 years from the date hereof.',
    'D': 'This Agreement shall remain in force for 1 year from the date hereof.',
  },
  'confidentiality_survival': {
    'A': 'The obligations of confidentiality shall survive termination for 2 years.',
    'B': 'The obligations of confidentiality shall survive termination for 3 years.',
    'C': 'The obligations of confidentiality shall survive termination for 5 years.',
    'D': 'The obligations of confidentiality shall survive termination indefinitely.',
  },
  'permitted_recipients': {
    'A': 'Confidential Information may only be disclosed to employees directly involved.',
    'B': 'Confidential Information may be disclosed to employees and professional advisors.',
    'C': 'Confidential Information may be disclosed to employees, advisors, and affiliated companies.',
    'D': 'Confidential Information may only be disclosed to named individuals.',
  },
  'return_destruction': {
    'A': 'Upon termination, all Confidential Information shall be returned.',
    'B': 'Upon termination, all Confidential Information shall be destroyed.',
    'C': 'Upon termination, the Receiving Party shall return or destroy all Confidential Information at the Disclosing Party\'s election.',
  },
  'ai_ml_restrictions': {
    'A': 'Confidential Information shall not be used to train AI or machine learning models.',
    'B': 'Confidential Information may be used for internal AI analysis only with prior written consent.',
    'C': 'No restrictions on AI/ML usage apply to Confidential Information.',
  },
  'governing_law': {
    'england_wales': 'This Agreement is governed by the laws of England and Wales.',
    'scotland': 'This Agreement is governed by the laws of Scotland.',
    'new_york': 'This Agreement is governed by the laws of the State of New York.',
    'delaware': 'This Agreement is governed by the laws of the State of Delaware.',
  },
  'dispute_resolution': {
    'A': 'Any dispute shall be resolved by the courts of England and Wales.',
    'B': 'Any dispute shall be resolved by mediation, failing which by arbitration.',
    'C': 'Any dispute shall be resolved by arbitration under the LCIA Rules.',
    'D': 'Any dispute shall be resolved by the courts of the agreed jurisdiction.',
    'E': 'Any dispute shall first be escalated to senior management before legal proceedings.',
  },
  'non_solicitation': {
    'A': 'Neither party shall solicit or hire employees of the other for 12 months.',
    'B': 'Neither party shall solicit employees of the other for 24 months.',
    'C': 'Neither party shall directly solicit key personnel for 6 months.',
    'D': 'No non-solicitation restrictions apply.',
  },
}

STORAGE_BASE = 'storage/documents'


class DocumentGenerationService:
  """Orchestrates document preview, generation, download, and validation."""

  def __init__(
    self,
    template_content: str | None = None,
    clause_variants: dict | None = None,
  ):
    self.template_content = template_content or FALLBACK_TEMPLATE
    self.clause_variants = clause_variants or FALLBACK_CLAUSE_VARIANTS
    self.docx_generator = DOCXGenerator()

  async def _build_party_dict(self, party_ref: dict, label: str) -> dict[str, Any]:
    """Build party context dict by looking up LegalEntity and ContactPerson from DB."""
    company_id = party_ref.get('company_id')

    # Look up entity from DB
    entity_data = None
    if company_id:
      try:
        entity_svc = LegalEntityService()
        entity_data = await entity_svc.get_legal_entity(company_id)
      except Exception as e:
        logger.warning('entity_lookup_failed', company_id=company_id, error=str(e))

    # Look up signatory from DB
    signatory_data = None
    signatory_id = party_ref.get('signatory_person_id')
    if signatory_id:
      try:
        person_svc = ContactPersonService()
        signatory_data = await person_svc.get_contact_person(signatory_id)
      except Exception as e:
        logger.warning('person_lookup_failed', person_id=signatory_id, error=str(e))

    if entity_data:
      legal_name = entity_data.legal_name
      registration_number = entity_data.registration_number
      jurisdiction = entity_data.jurisdiction
    else:
      legal_name = party_ref.get('legal_name', f'{label} Company')
      registration_number = party_ref.get('registration_number', 'N/A')
      jurisdiction = party_ref.get('jurisdiction', '')

    if signatory_data:
      signatory_name = signatory_data.full_name
      signatory_role = signatory_data.role.capitalize() if signatory_data.role else 'Director'
    else:
      signatory_name = party_ref.get('signatory_name', 'Authorised Signatory')
      signatory_role = party_ref.get('signatory_role', 'Director')

    # TODO: Resolve registered_address from LegalAddress table
    address = party_ref.get('address', 'Address not provided')

    return {
      'legal_name': legal_name,
      'registration_number': registration_number,
      'address': address,
      'label': label,
      'signatory_name': signatory_name,
      'signatory_role': signatory_role,
    }

  async def preview_document(
    self,
    document_type: str,
    title: str,
    document_data: dict,
    format: str = 'markdown',
  ) -> dict[str, Any]:
    """Generate document preview without saving."""
    party_a_ref = document_data.get('party_a', {})
    party_b_ref = document_data.get('party_b', {})
    configuration = document_data.get('configuration', {})

    party_a = await self._build_party_dict(party_a_ref, 'Party A')
    party_b = await self._build_party_dict(party_b_ref, 'Party B')

    engine = TemplateEngine(self.template_content, self.clause_variants)
    rendered = engine.render_nda(party_a, party_b, configuration)

    word_count = len(rendered.split())
    estimated_pages = max(1, math.ceil(word_count / 250))

    return {
      'title': 'Mutual Non-Disclosure Agreement',
      'content_preview': rendered,
      'estimated_pages': estimated_pages,
      'word_count': word_count,
    }

  async def generate_document(
    self,
    document_type: str,
    title: str,
    document_data: dict,
    user_id: str = 'anonymous',
    tenant_id: str | None = None,
  ) -> dict[str, Any]:
    """Generate document, create DOCX, store files, return metadata."""
    # Render markdown
    preview = await self.preview_document(document_type, title, document_data)
    rendered_md = preview['content_preview']

    # Generate DOCX
    docx_buffer = self.docx_generator.create_docx(rendered_md, title)
    docx_bytes = docx_buffer.read()
    docx_buffer.seek(0)

    # Create document record
    doc_id = str(uuid4())
    now = datetime.utcnow()

    # Store files
    doc_dir = os.path.join(STORAGE_BASE, user_id, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    docx_path = os.path.join(doc_dir, 'document.docx')
    with open(docx_path, 'wb') as f:
      f.write(docx_bytes)

    md_path = os.path.join(doc_dir, 'document.md')
    with open(md_path, 'w') as f:
      f.write(rendered_md)

    # Count clauses
    configuration = document_data.get('configuration', {})
    clause_count = sum(1 for k in [
      'purpose_option', 'personal_data_sharing', 'agreement_duration',
      'confidentiality_survival', 'permitted_recipients', 'return_or_destruction',
      'ai_ml_restrictions', 'governing_law', 'dispute_resolution', 'non_solicitation',
    ] if k in configuration or k in {'purpose_option', 'agreement_duration'})
    clause_count += len(configuration.get('additional_clauses', []))

    document = {
      'id': doc_id,
      'user_id': user_id,
      'document_type': document_type,
      'title': title,
      'status': 'generated',
      'generated_at': now.isoformat() + 'Z',
      'file_path_docx': docx_path,
      'version': 1,
    }

    logger.info(
      'document_generated',
      doc_id=doc_id,
      word_count=preview['word_count'],
      page_count=preview['estimated_pages'],
    )

    return {
      'document': document,
      'download_url': f'/api/v1/documents/{doc_id}/download?format=docx',
      'preview_url': f'/api/v1/documents/{doc_id}/download?format=md',
      'metadata': {
        'word_count': preview['word_count'],
        'clause_count': max(clause_count, 10),
        'page_count': preview['estimated_pages'],
      },
    }

  async def download_document(
    self,
    document_id: str,
    format: str = 'docx',
    user_id: str | None = None,
  ) -> dict[str, Any]:
    """Retrieve stored document file for download."""
    # Search for the file in storage
    if user_id:
      doc_dir = os.path.join(STORAGE_BASE, user_id, document_id)
    else:
      # Scan storage for the document
      doc_dir = self._find_document_dir(document_id)

    if not doc_dir or not os.path.isdir(doc_dir):
      raise HTTPException(status_code=404, detail='Document not found')

    if format == 'md':
      filepath = os.path.join(doc_dir, 'document.md')
      media_type = 'text/markdown'
      filename = 'document.md'
    else:
      filepath = os.path.join(doc_dir, 'document.docx')
      media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      filename = 'document.docx'

    if not os.path.isfile(filepath):
      raise HTTPException(status_code=404, detail='Document file not found')

    with open(filepath, 'rb') as f:
      content = f.read()

    return {
      'content': content,
      'filename': filename,
      'media_type': media_type,
    }

  def _find_document_dir(self, document_id: str) -> str | None:
    """Scan storage directory tree for a document by ID."""
    if not os.path.isdir(STORAGE_BASE):
      return None
    for user_dir in os.listdir(STORAGE_BASE):
      candidate = os.path.join(STORAGE_BASE, user_dir, document_id)
      if os.path.isdir(candidate):
        return candidate
    return None

  async def validate_entity(
    self,
    legal_entity_id: str,
    validation_type: str,
  ) -> dict[str, Any]:
    """Run validation rules and return results."""
    valid_types = {'equity', 'person', 'company', 'all'}
    if validation_type not in valid_types:
      raise HTTPException(
        status_code=400,
        detail=f'Invalid validation_type. Must be one of: {", ".join(valid_types)}',
      )

    all_errors = []
    all_warnings = []

    if validation_type in ('equity', 'all'):
      # In production, fetch holdings from DB
      result = ValidationService.validate_equity_total([], authorized_shares=None)
      all_errors.extend(self._format_errors(result))
      all_warnings.extend(self._format_warnings(result))

    if validation_type in ('person', 'all'):
      result = ValidationService.validate_person_email('', existing_founders=[])
      all_warnings.extend(self._format_warnings(result))

    if validation_type in ('company', 'all'):
      result = ValidationService.validate_company_update(
        field='legal_name', has_generated_documents=False,
      )
      all_errors.extend(self._format_errors(result))

    return {
      'valid': len(all_errors) == 0,
      'errors': all_errors,
      'warnings': all_warnings,
    }

  @staticmethod
  def _format_errors(result: ValidationResult) -> list[dict]:
    return [
      {
        'rule_id': e.rule_id,
        'severity': e.severity,
        'message': e.message,
        'field': e.field,
        'blocking': e.blocking,
      }
      for e in result.errors
    ]

  @staticmethod
  def _format_warnings(result: ValidationResult) -> list[dict]:
    return [
      {
        'rule_id': w.rule_id,
        'severity': w.severity,
        'message': w.message,
        'field': w.field,
        'blocking': w.blocking,
      }
      for w in result.warnings
    ]
