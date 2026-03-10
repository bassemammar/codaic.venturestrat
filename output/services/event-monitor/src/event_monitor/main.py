"""Event Monitor — FastAPI service for Kafka event observability."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from event_monitor.config import settings
from event_monitor.observer import KafkaObserver
from event_monitor.router import router, set_pool, set_services_dir
from event_monitor.writer import EventAuditWriter

# Structured logging
structlog.configure(
  processors=[
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt='iso'),
    structlog.dev.ConsoleRenderer()
    if settings.log_format == 'console'
    else structlog.processors.JSONRenderer(),
  ],
  wrapper_class=structlog.make_filtering_bound_logger(
    logging.getLevelName(settings.log_level.upper())
  ),
  context_class=dict,
  logger_factory=structlog.PrintLoggerFactory(),
  cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Shared instances (initialized in lifespan)
_writer: EventAuditWriter | None = None
_observer: KafkaObserver | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
  global _writer, _observer

  logger.info('service_starting', service=settings.service_name, port=settings.port)

  # 1. Start audit writer (asyncpg pool)
  _writer = EventAuditWriter(settings.database_url)
  await _writer.start()

  # 2. Create a shared pool for the API router
  pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
  set_pool(pool)
  set_services_dir(settings.services_dir)

  # 3. Start Kafka observer (background task)
  _observer = KafkaObserver(
    bootstrap_servers=settings.kafka_bootstrap_servers,
    group_id=settings.observer_group_id,
    writer=_writer,
    topic_pattern=settings.topic_pattern,
  )
  await _observer.start()

  logger.info('service_ready', port=settings.port)
  yield

  # Shutdown
  logger.info('service_shutting_down')
  if _observer:
    await _observer.stop()
  if _writer:
    await _writer.stop()
  if pool:
    await pool.close()


app = FastAPI(
  title='VentureStrat Event Monitor',
  description='Kafka event observer, audit trail, trace explorer, and topology API',
  version=settings.service_version,
  lifespan=lifespan,
)

# CORS
app.add_middleware(
  CORSMiddleware,
  allow_origins=settings.cors_origins_list,
  allow_credentials=True,
  allow_methods=['GET', 'POST'],
  allow_headers=['*'],
)

# Health endpoints
@app.get('/health/live', tags=['Health'])
async def liveness():
  return {'status': 'alive', 'service': settings.service_name}


@app.get('/health/ready', tags=['Health'])
async def readiness():
  ok = _writer is not None and _observer is not None
  return {
    'status': 'healthy' if ok else 'starting',
    'writer': _writer is not None,
    'observer': _observer is not None and _observer._running,
  }


# Event monitor API
app.include_router(router)


@app.get('/', tags=['Root'])
async def root():
  return {
    'service': 'VentureStrat Event Monitor',
    'version': settings.service_version,
    'docs': '/docs',
  }


def main():
  import uvicorn
  uvicorn.run(
    'event_monitor.main:app',
    host=settings.host,
    port=settings.port,
    reload=settings.reload,
    log_level=settings.log_level.lower(),
  )


if __name__ == '__main__':
  main()
