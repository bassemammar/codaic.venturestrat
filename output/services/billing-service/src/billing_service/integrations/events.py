"""Event publishing integration with Kafka."""

import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, Optional
import structlog
from aiokafka import AIOKafkaProducer

from billing_service.config import settings

logger = structlog.get_logger(__name__)


def serialize_datetime(obj):
    """
    JSON serializer for datetime and decimal objects.

    Handles datetime, date, and Decimal objects by converting them to
    appropriate JSON-serializable types. This is required because BaseModel
    entities contain created_at/updated_at datetime fields and decimal fields
    that need to be serialized for Kafka events.

    Args:
        obj: Object to serialize

    Returns:
        ISO format string for datetime/date objects, string for Decimal

    Raises:
        TypeError: If object type is not serializable
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class EventPublisher:
    """Kafka event publisher for domain events."""

    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize Kafka producer.

        IMPORTANT: Uses parameters compatible with aiokafka 0.13.0+
        - Removed delivery_timeout_ms (not supported in 0.13.0)
        - Added datetime serialization support via custom JSON encoder
        """
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=serialize_datetime).encode('utf-8'),
                compression_type='gzip',
                acks='all',
                request_timeout_ms=30000,  # 30 seconds per request
            )
            await self.producer.start()
            self._initialized = True
            logger.info("kafka_producer_started",
                       bootstrap_servers=settings.kafka_bootstrap_servers)
        except Exception as e:
            logger.error("kafka_producer_init_failed", error=str(e))

    async def close(self) -> None:
        """Close Kafka producer."""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("kafka_producer_stopped")
            except Exception as e:
                logger.error("kafka_producer_close_failed", error=str(e))

    async def publish(
        self,
        entity_name: str,
        action: str,
        data: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> None:
        """
        Publish domain event to Kafka.

        Events are automatically serialized with datetime support, ensuring
        BaseModel entities with created_at/updated_at fields can be published.

        Args:
            entity_name: Name of the entity (e.g., "currency", "counterparty")
            action: Action performed ("created", "updated", "deleted")
            data: Event data (can contain datetime objects)
            tenant_id: Optional tenant ID for multi-tenant events

        Example:
            >>> await publisher.publish(
            ...     "currency",
            ...     "created",
            ...     {"id": "...", "code": "USD", "created_at": datetime.now()},
            ...     tenant_id="tenant-123"
            ... )
        """
        if not self._initialized or not self.producer:
            logger.warning("kafka_not_initialized", entity=entity_name, action=action)
            return

        topic = f"{settings.kafka_topic_prefix}.{entity_name}.{action}"

        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": f"{entity_name.title()}{action.title()}",
            "entity_name": entity_name,
            "action": action,
            "data": data,  # Can contain datetime objects - will be auto-serialized
            "timestamp": datetime.utcnow().isoformat(),
            "service": settings.service_name,
            "version": settings.service_version,
        }

        if tenant_id:
            event["tenant_id"] = tenant_id

        try:
            await self.producer.send_and_wait(topic, value=event)
            logger.info("event_published",
                       topic=topic,
                       event_id=event["event_id"],
                       entity=entity_name,
                       action=action)
        except Exception as e:
            logger.error("event_publish_failed",
                        topic=topic,
                        entity=entity_name,
                        action=action,
                        error=str(e))


# Global instance
event_publisher = EventPublisher()
