"""AI-powered email generation and text editing endpoints."""

import structlog
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from outreach_service.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix='/ai', tags=['AI'])

OPENAI_CHAT_URL = 'https://api.openai.com/v1/chat/completions'
MODEL = 'gpt-4o-mini'


class GenerateEmailRequest(BaseModel):
  """Request body for AI email generation."""
  investor_name: str = Field(description='Name of the investor')
  investor_company: str = Field(description='Company the investor belongs to')
  context: str = Field(
    default='professional',
    description='Tone/context for the email (e.g. professional, warm, follow-up)',
  )
  instructions: str = Field(
    default='',
    description='Additional user instructions for the AI (e.g. mention a recent deal)',
  )


class GenerateEmailResponse(BaseModel):
  """Response with AI-generated email content."""
  subject: str = Field(description='Generated email subject line')
  body: str = Field(description='Generated email body (HTML)')


class EditTextRequest(BaseModel):
  """Request body for AI text editing."""
  original_text: str = Field(description='The text to edit or improve')
  edit_instruction: str = Field(
    description='What to change (e.g. "make it more concise", "add a CTA")'
  )


class EditTextResponse(BaseModel):
  """Response with AI-edited text."""
  edited_text: str = Field(description='The edited/improved text')


async def _call_openai(messages: list[dict], temperature: float = 0.7) -> str:
  """Call OpenAI chat completions API via httpx.

  Args:
      messages: List of chat messages (system, user, assistant).
      temperature: Sampling temperature (0-2).

  Returns:
      The assistant's response text.

  Raises:
      HTTPException: If the API key is missing or the API call fails.
  """
  if not settings.openai_api_key:
    raise HTTPException(
      status_code=500,
      detail='OPENAI_API_KEY is not configured',
    )

  async with httpx.AsyncClient(timeout=30.0) as client:
    try:
      resp = await client.post(
        OPENAI_CHAT_URL,
        headers={
          'Authorization': f'Bearer {settings.openai_api_key}',
          'Content-Type': 'application/json',
        },
        json={
          'model': MODEL,
          'messages': messages,
          'temperature': temperature,
        },
      )
      resp.raise_for_status()
      data = resp.json()
      return data['choices'][0]['message']['content']
    except httpx.HTTPStatusError as e:
      logger.error('openai_api_error', status=e.response.status_code, body=e.response.text)
      raise HTTPException(
        status_code=502,
        detail=f'OpenAI API error: {e.response.status_code}',
      )
    except httpx.RequestError as e:
      logger.error('openai_request_error', error=str(e))
      raise HTTPException(
        status_code=502,
        detail=f'Failed to reach OpenAI API: {str(e)}',
      )


@router.post(
  '/generate-email',
  response_model=GenerateEmailResponse,
  summary='Generate an outreach email using AI',
  description=(
    'Uses GPT-4o-mini to generate a personalized investor outreach email. '
    'Returns both subject and HTML body.'
  ),
  responses={
    200: {'description': 'Email generated successfully'},
    500: {
      'description': 'OpenAI API key not configured',
      'content': {'application/json': {'example': {'detail': 'OPENAI_API_KEY is not configured'}}},
    },
    502: {
      'description': 'OpenAI API error',
      'content': {'application/json': {'example': {'detail': 'OpenAI API error: 429'}}},
    },
  },
)
async def generate_email(body: GenerateEmailRequest) -> GenerateEmailResponse:
  """Generate a personalized investor outreach email."""
  system_prompt = (
    'You are an expert at writing investor outreach emails for a venture fund. '
    'Write concise, professional emails that feel personal, not templated. '
    'Return your response in exactly this format:\n'
    'SUBJECT: <subject line>\n'
    'BODY:\n<html email body>\n\n'
    'Use simple HTML with <p> tags. Do not include <html>, <head>, or <body> tags. '
    'Keep the email under 200 words.'
  )

  user_prompt = (
    f'Write an outreach email to {body.investor_name} at {body.investor_company}.\n'
    f'Tone/context: {body.context}\n'
  )
  if body.instructions:
    user_prompt += f'Additional instructions: {body.instructions}\n'

  messages = [
    {'role': 'system', 'content': system_prompt},
    {'role': 'user', 'content': user_prompt},
  ]

  raw = await _call_openai(messages, temperature=0.7)

  # Parse SUBJECT: and BODY: from the response
  subject = ''
  email_body = raw

  if 'SUBJECT:' in raw and 'BODY:' in raw:
    parts = raw.split('BODY:', 1)
    subject_part = parts[0]
    email_body = parts[1].strip() if len(parts) > 1 else ''

    if 'SUBJECT:' in subject_part:
      subject = subject_part.split('SUBJECT:', 1)[1].strip()
  else:
    # Fallback: first line as subject, rest as body
    lines = raw.strip().split('\n', 1)
    subject = lines[0].strip()
    email_body = lines[1].strip() if len(lines) > 1 else ''

  return GenerateEmailResponse(subject=subject, body=email_body)


@router.post(
  '/edit-text',
  response_model=EditTextResponse,
  summary='Edit or improve text using AI',
  description=(
    'Uses GPT-4o-mini to edit or improve text based on the provided instruction. '
    'Useful for refining email drafts, making text more concise, adding CTAs, etc.'
  ),
  responses={
    200: {'description': 'Text edited successfully'},
    502: {
      'description': 'OpenAI API error',
      'content': {'application/json': {'example': {'detail': 'OpenAI API error: 429'}}},
    },
  },
)
async def edit_text(body: EditTextRequest) -> EditTextResponse:
  """Edit or improve text based on user instructions."""
  system_prompt = (
    'You are a professional editor. Edit the provided text according to the instruction. '
    'Return ONLY the edited text, nothing else. '
    'Preserve the original format (HTML if HTML, plain text if plain text). '
    'Do not add explanations or comments.'
  )

  user_prompt = (
    f'Original text:\n{body.original_text}\n\n'
    f'Edit instruction: {body.edit_instruction}'
  )

  messages = [
    {'role': 'system', 'content': system_prompt},
    {'role': 'user', 'content': user_prompt},
  ]

  edited = await _call_openai(messages, temperature=0.3)

  return EditTextResponse(edited_text=edited.strip())
