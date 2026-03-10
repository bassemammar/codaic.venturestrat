"""Kafka consumer for outreach.send_email topic.

Subscribes to outreach.send_email events and dispatches the actual
email send through the appropriate provider (Gmail, Microsoft, SendGrid).

On success: updates message status to 'sent', publishes outreach.message.sent.
On failure: retries up to 3 times with exponential backoff, then routes to DLQ.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

import structlog
from aiokafka import AIOKafkaConsumer

from outreach_service.application.services.email_account_service import EmailAccountService
from outreach_service.application.services.message_service import MessageService
from outreach_service.config import settings
from outreach_service.events.producer import event_producer
from outreach_service.providers import gmail, microsoft, sendgrid
from outreach_service.schemas.message import MessageUpdate

logger = structlog.get_logger(__name__)

TOPIC = 'outreach.send_email'
DLQ_TOPIC = 'outreach.send_email.dlq'
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2


class EmailSendConsumer:
  """Async Kafka consumer that processes outreach.send_email events.

  Each event contains a message_id. The consumer:
  1. Looks up the Message and its EmailAccount
  2. Dispatches to the correct provider (Gmail/Microsoft/SendGrid)
  3. Updates the message status
  4. Publishes outreach.message.sent on success or routes to DLQ on failure
  """

  def __init__(self) -> None:
    self._consumer: Optional[AIOKafkaConsumer] = None
    self._running = False
    self._task: Optional[asyncio.Task] = None

  async def start(self) -> None:
    """Start the consumer in a background task."""
    if self._running:
      return
    self._running = True
    self._task = asyncio.create_task(self._run())
    logger.info('email_send_consumer_started', topic=TOPIC)

  async def stop(self) -> None:
    """Stop the consumer gracefully."""
    self._running = False
    if self._consumer:
      try:
        await self._consumer.stop()
      except Exception:
        pass
    if self._task:
      self._task.cancel()
      try:
        await self._task
      except asyncio.CancelledError:
        pass
    logger.info('email_send_consumer_stopped')

  async def _run(self) -> None:
    """Main consumer loop with auto-reconnect."""
    while self._running:
      try:
        self._consumer = AIOKafkaConsumer(
          TOPIC,
          bootstrap_servers=settings.kafka_bootstrap_servers,
          group_id=f'{settings.service_name}-send-email',
          auto_offset_reset='earliest',
          enable_auto_commit=False,
          value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        )
        await self._consumer.start()
        logger.info('email_send_consumer_connected', topic=TOPIC)

        async for msg in self._consumer:
          if not self._running:
            break
          try:
            await self._handle_message(msg.value)
            await self._consumer.commit()
          except Exception as e:
            logger.error(
              'email_send_consumer_message_error',
              error=str(e),
              topic=msg.topic,
              offset=msg.offset,
            )
            await self._consumer.commit()

      except asyncio.CancelledError:
        break
      except Exception as e:
        logger.error('email_send_consumer_connection_error', error=str(e))
        if self._running:
          await asyncio.sleep(5)

  async def _handle_message(self, event: dict) -> None:
    """Process a single outreach.send_email event.

    Expected event payload:
        {
          "data": {
            "message_id": "<uuid>",
            "tenant_id": "<uuid>"  (optional)
          }
        }
    """
    data = event.get('data', event)
    message_id_str = data.get('message_id')
    tenant_id = data.get('tenant_id')

    if not message_id_str:
      logger.warning('email_send_consumer_missing_message_id', event=event)
      return

    message_id = UUID(message_id_str)

    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
      try:
        await self._send_email(message_id, tenant_id)
        return
      except Exception as e:
        last_error = e
        logger.warning(
          'email_send_retry',
          message_id=message_id_str,
          attempt=attempt,
          max_retries=MAX_RETRIES,
          error=str(e),
        )
        if attempt < MAX_RETRIES:
          await asyncio.sleep(BACKOFF_BASE_SECONDS ** attempt)

    # All retries exhausted — route to DLQ
    logger.error(
      'email_send_to_dlq',
      message_id=message_id_str,
      error=str(last_error),
    )
    await self._publish_to_dlq(event, str(last_error))

    # Mark message as failed
    try:
      msg_service = MessageService()
      await msg_service.update_message(
        message_id,
        MessageUpdate(status='failed'),
      )
    except Exception as update_err:
      logger.error(
        'email_send_status_update_failed',
        message_id=message_id_str,
        error=str(update_err),
      )

  async def _send_email(self, message_id: UUID, tenant_id: Optional[str] = None) -> None:
    """Look up the message and email account, dispatch to provider."""
    msg_service = MessageService()
    acct_service = EmailAccountService()

    message = await msg_service.get_message(message_id)
    if not message:
      raise ValueError(f'Message {message_id} not found')

    if not message.email_account_id:
      raise ValueError(f'Message {message_id} has no email_account_id')

    account = await acct_service.get_email_account(UUID(message.email_account_id))
    if not account:
      raise ValueError(f'EmailAccount {message.email_account_id} not found')

    if not account.is_active:
      raise ValueError(f'EmailAccount {message.email_account_id} is not active')

    # Parse addresses
    to_addrs = message.to_addresses if isinstance(message.to_addresses, list) else []
    cc_addrs = message.cc_addresses if isinstance(message.cc_addresses, list) else []

    # Threading headers
    in_reply_to = message.provider_message_id if message.previous_message_id else None
    references = message.provider_references

    provider = (account.provider or '').lower()
    provider_message_id = None
    provider_thread_id = message.thread_id

    if provider == 'gmail':
      result = await gmail.send_email(
        access_token=account.access_token or '',
        from_address=message.from_address,
        to_addresses=to_addrs,
        cc_addresses=cc_addrs,
        subject=message.subject,
        body_html=message.body,
        thread_id=message.thread_id,
        in_reply_to=in_reply_to,
        references=references,
      )
      provider_message_id = result.get('id')
      provider_thread_id = result.get('threadId', message.thread_id)

    elif provider == 'microsoft':
      result = await microsoft.send_email(
        access_token=account.access_token or '',
        from_address=message.from_address,
        to_addresses=to_addrs,
        cc_addresses=cc_addrs,
        subject=message.subject,
        body_html=message.body,
        thread_id=message.thread_id,
        in_reply_to=in_reply_to,
        references=references,
      )
      provider_message_id = result.get('id')
      provider_thread_id = result.get('conversationId', message.thread_id)

    elif provider == 'sendgrid':
      result = await sendgrid.send_email(
        access_token=account.access_token or '',
        from_address=message.from_address,
        to_addresses=to_addrs,
        cc_addresses=cc_addrs,
        subject=message.subject,
        body_html=message.body,
        in_reply_to=in_reply_to,
        references=references,
        api_key=settings.sendgrid_api_key,
      )
      provider_message_id = result.get('message_id')

    else:
      raise ValueError(f'Unsupported provider: {provider}')

    # Update message status to sent
    sent_at = datetime.utcnow()
    await msg_service.update_message(
      message_id,
      MessageUpdate(
        status='sent',
        provider_message_id=provider_message_id,
        thread_id=provider_thread_id,
      ),
    )

    # Publish outreach.message.sent event
    await event_producer.publish_event(
      'outreach.message.sent',
      {
        'message_id': str(message_id),
        'user_id': message.user_id,
        'investor_id': message.investor_id,
        'subject': message.subject,
        'sent_at': sent_at.isoformat(),
      },
      tenant_id=tenant_id,
    )

    logger.info(
      'email_sent_via_consumer',
      message_id=str(message_id),
      provider=provider,
    )

  async def _publish_to_dlq(self, original_event: dict, error_msg: str) -> None:
    """Publish a failed event to the dead letter queue topic."""
    dlq_event = {
      'original_event': original_event,
      'error': error_msg,
      'failed_at': datetime.utcnow().isoformat(),
      'retries_exhausted': MAX_RETRIES,
    }
    await event_producer.publish_event(DLQ_TOPIC, dlq_event)


# Global singleton — start/stop from main.py lifespan
email_send_consumer = EmailSendConsumer()
