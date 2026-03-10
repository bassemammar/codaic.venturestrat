"""Kafka event consumers for crm-service."""

from crm_service.consumers.activity_consumer import ActivityConsumer
from crm_service.consumers.shortlist_status_consumer import ShortlistStatusConsumer

__all__ = ['ActivityConsumer', 'ShortlistStatusConsumer']
