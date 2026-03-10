"""OpenTelemetry distributed tracing integration."""

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource

from legal_service.config import settings

logger = structlog.get_logger(__name__)


def setup_tracing(app):
    """Setup OpenTelemetry tracing."""
    try:
        # Create resource
        resource = Resource.create({
            "service.name": settings.service_name,
            "service.version": settings.service_version,
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Add OTLP exporter (Jaeger)
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otlp_endpoint,
            insecure=True,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)

        logger.info("tracing_enabled",
                   service=settings.service_name,
                   endpoint=settings.otlp_endpoint)

    except Exception as e:
        logger.error("tracing_setup_failed", error=str(e))
