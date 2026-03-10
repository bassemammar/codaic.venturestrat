"""
Attachment endpoints for outreach-service.

POST   /api/v1/messages/{message_id}/attachments  — upload a file attachment
GET    /api/v1/messages/{message_id}/attachments  — list attachments for a message
GET    /api/v1/attachments/{attachment_id}/download — download an attachment
DELETE /api/v1/attachments/{attachment_id}         — remove an attachment
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File, Path as FPath
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
  'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv',
  'png', 'jpg', 'jpeg', 'gif', 'txt',
}

ALLOWED_CONTENT_TYPES = {
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/csv',
  'image/png',
  'image/jpeg',
  'image/gif',
  'text/plain',
  # Browsers sometimes send these generic types
  'application/octet-stream',
}

# Base upload dir — relative to the service working directory
UPLOADS_BASE = Path(os.getenv('UPLOADS_DIR', 'uploads/attachments'))

# ---------------------------------------------------------------------------
# In-memory attachment store (replace with DB if needed)
# ---------------------------------------------------------------------------

# attachment_id -> metadata dict
_store: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AttachmentResponse(BaseModel):
  id: str = Field(description='Attachment UUID')
  message_id: str = Field(description='Parent message UUID')
  filename: str = Field(description='Original filename')
  size: int = Field(description='File size in bytes')
  content_type: str = Field(description='MIME type')
  created_at: str = Field(description='ISO 8601 timestamp')


# ---------------------------------------------------------------------------
# Routers — two separate routers so prefixes work cleanly
# ---------------------------------------------------------------------------

messages_router = APIRouter(tags=['Attachments'])
attachments_router = APIRouter(tags=['Attachments'])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _attachment_dir(message_id: str) -> Path:
  """Return (and create) the storage directory for a message's attachments."""
  target = UPLOADS_BASE / message_id
  target.mkdir(parents=True, exist_ok=True)
  return target


def _extension_ok(filename: str) -> bool:
  ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
  return ext in ALLOWED_EXTENSIONS


def _content_type_ok(content_type: str) -> bool:
  # Strip parameters like '; charset=utf-8'
  base = content_type.split(';')[0].strip().lower()
  return base in ALLOWED_CONTENT_TYPES


# ---------------------------------------------------------------------------
# POST /messages/{message_id}/attachments
# ---------------------------------------------------------------------------

@messages_router.post(
  '/{message_id}/attachments',
  response_model=AttachmentResponse,
  status_code=201,
  summary='Upload an attachment for a message',
)
async def upload_attachment(
  message_id: str = FPath(..., description='Parent message UUID'),
  file: UploadFile = File(..., description='File to attach (max 10 MB)'),
) -> AttachmentResponse:
  """Upload a file and associate it with a message."""

  # Validate extension
  if not _extension_ok(file.filename or ''):
    raise HTTPException(
      status_code=400,
      detail=(
        f'File type not allowed. Allowed extensions: '
        f'{", ".join(sorted(ALLOWED_EXTENSIONS))}'
      ),
    )

  # Validate content-type (best-effort; browsers may send octet-stream)
  if file.content_type and not _content_type_ok(file.content_type):
    raise HTTPException(
      status_code=400,
      detail=f'Content-Type not allowed: {file.content_type}',
    )

  # Read file content (enforce size limit)
  content = await file.read()
  if len(content) > MAX_FILE_SIZE:
    raise HTTPException(
      status_code=413,
      detail=f'File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB.',
    )

  if not content:
    raise HTTPException(status_code=400, detail='Uploaded file is empty.')

  # Persist to filesystem
  attachment_id = str(uuid.uuid4())
  safe_filename = f'{attachment_id}_{Path(file.filename or "file").name}'
  dest_dir = _attachment_dir(message_id)
  dest_path = dest_dir / safe_filename

  async with aiofiles.open(dest_path, 'wb') as f:
    await f.write(content)

  logger.info(
    'attachment_uploaded',
    message_id=message_id,
    attachment_id=attachment_id,
    filename=file.filename,
    size=len(content),
  )

  metadata = {
    'id': attachment_id,
    'message_id': message_id,
    'filename': file.filename or 'file',
    'size': len(content),
    'content_type': file.content_type or 'application/octet-stream',
    'created_at': datetime.utcnow().isoformat() + 'Z',
    'path': str(dest_path),
  }
  _store[attachment_id] = metadata

  return AttachmentResponse(**{k: v for k, v in metadata.items() if k != 'path'})


# ---------------------------------------------------------------------------
# GET /messages/{message_id}/attachments
# ---------------------------------------------------------------------------

@messages_router.get(
  '/{message_id}/attachments',
  response_model=list[AttachmentResponse],
  summary='List attachments for a message',
)
async def list_attachments(
  message_id: str = FPath(..., description='Parent message UUID'),
) -> list[AttachmentResponse]:
  """Return all attachments associated with a message."""
  results = [
    AttachmentResponse(**{k: v for k, v in meta.items() if k != 'path'})
    for meta in _store.values()
    if meta['message_id'] == message_id
  ]
  return sorted(results, key=lambda a: a.created_at)


# ---------------------------------------------------------------------------
# GET /attachments/{attachment_id}/download
# ---------------------------------------------------------------------------

@attachments_router.get(
  '/{attachment_id}/download',
  summary='Download an attachment',
  response_class=FileResponse,
)
async def download_attachment(
  attachment_id: str = FPath(..., description='Attachment UUID'),
) -> FileResponse:
  """Stream the file back with Content-Disposition: attachment."""
  meta = _store.get(attachment_id)
  if not meta:
    raise HTTPException(status_code=404, detail='Attachment not found')

  file_path = Path(meta['path'])
  if not file_path.exists():
    logger.error('attachment_file_missing', attachment_id=attachment_id, path=str(file_path))
    raise HTTPException(status_code=404, detail='Attachment file not found on disk')

  return FileResponse(
    path=str(file_path),
    filename=meta['filename'],
    media_type=meta['content_type'],
    headers={
      'Content-Disposition': f'attachment; filename="{meta["filename"]}"',
    },
  )


# ---------------------------------------------------------------------------
# DELETE /attachments/{attachment_id}
# ---------------------------------------------------------------------------

@attachments_router.delete(
  '/{attachment_id}',
  status_code=204,
  summary='Remove an attachment',
)
async def delete_attachment(
  attachment_id: str = FPath(..., description='Attachment UUID'),
) -> None:
  """Delete an attachment from storage and the metadata store."""
  meta = _store.get(attachment_id)
  if not meta:
    raise HTTPException(status_code=404, detail='Attachment not found')

  file_path = Path(meta['path'])
  if file_path.exists():
    file_path.unlink()

  del _store[attachment_id]

  logger.info('attachment_deleted', attachment_id=attachment_id, filename=meta['filename'])
