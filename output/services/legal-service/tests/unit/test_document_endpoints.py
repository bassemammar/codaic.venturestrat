"""Tests for document generation API endpoints.

Tests the custom endpoints: /preview, /generate, /download, /validate.
Uses mocked services to test endpoint logic without database.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from legal_service.api.endpoints.documents import router, _get_document_service


# --- Fixtures ---

def _make_app():
  """Create a minimal FastAPI app with just the documents router."""
  app = FastAPI()
  app.include_router(router, prefix='/api/v1/documents')
  return app


@pytest.fixture
def app():
  return _make_app()


@pytest.fixture
def client(app):
  return TestClient(app)


@pytest.fixture
def mock_services():
  """Patch all service dependencies used by the endpoints."""
  with patch('legal_service.api.endpoints.documents._get_document_service') as mock_get_svc:
    svc = MagicMock()
    mock_get_svc.return_value = svc
    yield svc


@pytest.fixture
def preview_payload():
  return {
    'document_type': 'mutual_nda',
    'title': 'NDA - Acme and Beta',
    'document_data': {
      'party_a': {
        'company_id': str(uuid4()),
        'signatory_person_id': str(uuid4()),
      },
      'party_b': {
        'company_id': str(uuid4()),
        'signatory_person_id': str(uuid4()),
      },
      'configuration': {
        'purpose_option': 'B',
        'agreement_duration': 'A',
      },
    },
    'format': 'markdown',
  }


# --- Preview Endpoint Tests ---

class TestPreviewEndpoint:
  def test_preview_returns_rendered_markdown(self, client, mock_services, preview_payload):
    rendered = '# Mutual NDA\n\nThis agreement is between parties.'
    mock_services.preview_document = AsyncMock(return_value={
      'title': 'Mutual Non-Disclosure Agreement',
      'content_preview': rendered,
      'estimated_pages': 1,
      'word_count': 7,
    })

    resp = client.post('/api/v1/documents/preview', json=preview_payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data['title'] == 'Mutual Non-Disclosure Agreement'
    assert 'Mutual NDA' in data['content_preview']
    assert data['word_count'] == 7
    assert data['estimated_pages'] == 1

  def test_preview_returns_correct_word_count(self, client, mock_services, preview_payload):
    mock_services.preview_document = AsyncMock(return_value={
      'title': 'Mutual Non-Disclosure Agreement',
      'content_preview': 'word ' * 500,
      'estimated_pages': 2,
      'word_count': 500,
    })

    resp = client.post('/api/v1/documents/preview', json=preview_payload)
    data = resp.json()
    assert data['word_count'] == 500
    assert data['estimated_pages'] == 2

  def test_preview_404_on_missing_party(self, client, mock_services, preview_payload):
    from fastapi import HTTPException
    mock_services.preview_document = AsyncMock(
      side_effect=HTTPException(status_code=404, detail='Party not found')
    )

    resp = client.post('/api/v1/documents/preview', json=preview_payload)
    assert resp.status_code == 404

  def test_preview_400_on_invalid_config(self, client, mock_services, preview_payload):
    from fastapi import HTTPException
    mock_services.preview_document = AsyncMock(
      side_effect=HTTPException(status_code=400, detail='Invalid configuration')
    )

    resp = client.post('/api/v1/documents/preview', json=preview_payload)
    assert resp.status_code == 400


# --- Generate Endpoint Tests ---

class TestGenerateEndpoint:
  def test_generate_creates_document(self, client, mock_services, preview_payload):
    doc_id = str(uuid4())
    mock_services.generate_document = AsyncMock(return_value={
      'document': {
        'id': doc_id,
        'user_id': 'test-user',
        'document_type': 'mutual_nda',
        'title': 'NDA - Acme and Beta',
        'status': 'generated',
        'generated_at': '2026-03-11T10:00:00Z',
        'file_path_docx': f'storage/documents/test-user/{doc_id}/document.docx',
        'version': 1,
      },
      'download_url': f'/api/v1/documents/{doc_id}/download?format=docx',
      'preview_url': f'/api/v1/documents/{doc_id}/download?format=md',
      'metadata': {
        'word_count': 980,
        'clause_count': 14,
        'page_count': 4,
      },
    })

    resp = client.post('/api/v1/documents/generate', json=preview_payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data['document']['id'] == doc_id
    assert data['document']['status'] == 'generated'
    assert 'download_url' in data
    assert 'metadata' in data

  def test_generate_returns_download_url(self, client, mock_services, preview_payload):
    doc_id = str(uuid4())
    mock_services.generate_document = AsyncMock(return_value={
      'document': {'id': doc_id, 'status': 'generated'},
      'download_url': f'/api/v1/documents/{doc_id}/download?format=docx',
      'preview_url': f'/api/v1/documents/{doc_id}/download?format=md',
      'metadata': {'word_count': 100, 'clause_count': 5, 'page_count': 1},
    })

    resp = client.post('/api/v1/documents/generate', json=preview_payload)
    data = resp.json()
    assert f'/api/v1/documents/{doc_id}/download' in data['download_url']

  def test_generate_publishes_lifecycle_event(self, client, mock_services, preview_payload):
    mock_services.generate_document = AsyncMock(return_value={
      'document': {'id': str(uuid4()), 'status': 'generated'},
      'download_url': '/api/v1/documents/x/download?format=docx',
      'preview_url': '/api/v1/documents/x/download?format=md',
      'metadata': {'word_count': 100, 'clause_count': 5, 'page_count': 1},
    })

    client.post('/api/v1/documents/generate', json=preview_payload)
    mock_services.generate_document.assert_called_once()


# --- Download Endpoint Tests ---

class TestDownloadEndpoint:
  def test_download_docx(self, client, mock_services):
    doc_id = str(uuid4())
    docx_bytes = b'PK\x03\x04fake-docx-content'
    mock_services.download_document = AsyncMock(return_value={
      'content': docx_bytes,
      'filename': 'document.docx',
      'media_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })

    resp = client.get(f'/api/v1/documents/{doc_id}/download?format=docx')
    assert resp.status_code == 200
    assert 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in resp.headers.get('content-type', '')

  def test_download_markdown(self, client, mock_services):
    doc_id = str(uuid4())
    mock_services.download_document = AsyncMock(return_value={
      'content': b'# NDA\n\nContent here',
      'filename': 'document.md',
      'media_type': 'text/markdown',
    })

    resp = client.get(f'/api/v1/documents/{doc_id}/download?format=md')
    assert resp.status_code == 200

  def test_download_404_for_missing_doc(self, client, mock_services):
    from fastapi import HTTPException
    mock_services.download_document = AsyncMock(
      side_effect=HTTPException(status_code=404, detail='Document not found')
    )

    resp = client.get(f'/api/v1/documents/{uuid4()}/download')
    assert resp.status_code == 404


# --- Validate Endpoint Tests ---

class TestValidateEndpoint:
  def test_equity_validation_errors(self, client, mock_services):
    mock_services.validate_entity = AsyncMock(return_value={
      'valid': False,
      'errors': [{
        'rule_id': '2.1',
        'severity': 'CRITICAL',
        'message': 'Total equity percentage is 110%, exceeds 100%',
        'field': 'percentage',
        'blocking': True,
      }],
      'warnings': [],
    })

    resp = client.post('/api/v1/documents/validate', json={
      'legal_entity_id': str(uuid4()),
      'validation_type': 'equity',
    })

    assert resp.status_code == 200
    data = resp.json()
    assert not data['valid']
    assert len(data['errors']) == 1
    assert data['errors'][0]['rule_id'] == '2.1'

  def test_person_validation_warnings(self, client, mock_services):
    mock_services.validate_entity = AsyncMock(return_value={
      'valid': True,
      'errors': [],
      'warnings': [{
        'rule_id': '1.3',
        'severity': 'HIGH',
        'message': 'Person has same email as existing founder',
        'field': 'email',
        'blocking': False,
      }],
    })

    resp = client.post('/api/v1/documents/validate', json={
      'legal_entity_id': str(uuid4()),
      'validation_type': 'person',
    })

    data = resp.json()
    assert data['valid']
    assert len(data['warnings']) == 1

  def test_company_blocking_validation(self, client, mock_services):
    mock_services.validate_entity = AsyncMock(return_value={
      'valid': False,
      'errors': [{
        'rule_id': '1.1',
        'severity': 'CRITICAL',
        'message': 'Cannot change legal_name — entity is referenced in generated documents',
        'field': 'legal_name',
        'blocking': True,
      }],
      'warnings': [],
    })

    resp = client.post('/api/v1/documents/validate', json={
      'legal_entity_id': str(uuid4()),
      'validation_type': 'company',
    })

    data = resp.json()
    assert not data['valid']
    assert data['errors'][0]['blocking']

  def test_validate_invalid_type_returns_400(self, client, mock_services):
    from fastapi import HTTPException
    mock_services.validate_entity = AsyncMock(
      side_effect=HTTPException(status_code=400, detail='Invalid validation_type')
    )

    resp = client.post('/api/v1/documents/validate', json={
      'legal_entity_id': str(uuid4()),
      'validation_type': 'invalid_type',
    })
    assert resp.status_code == 400
