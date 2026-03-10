"""VentureStrat Forge Service — main application."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.models import Base

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
  """Yield a database session."""
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Application lifespan — create tables on startup."""
  logger.info('Starting VentureStrat Forge Service')
  with engine.begin() as conn:
    conn.execute(text('CREATE SCHEMA IF NOT EXISTS forge'))
  Base.metadata.create_all(bind=engine)
  logger.info('Database tables ready')
  yield
  logger.info('Shutting down VentureStrat Forge Service')


app = FastAPI(
  title='VentureStrat Forge',
  description='Requirements intake, spec generation, and ADW execution service',
  version='1.0.0',
  lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(',') if o.strip()]
if origins:
  app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
  )


@app.get('/health/live')
def health_live():
  """Liveness probe."""
  return {'status': 'ok'}


@app.get('/health/ready')
def health_ready():
  """Readiness probe — checks DB connectivity."""
  try:
    db = SessionLocal()
    db.execute(text('SELECT 1'))
    db.close()
    return {'status': 'ready'}
  except Exception as e:
    return {'status': 'not_ready', 'error': str(e)}


@app.get('/metrics')
def metrics():
  """Basic metrics endpoint."""
  return {
    'service': settings.SERVICE_NAME,
    'platform': settings.PLATFORM_NAME,
    'status': 'running',
  }


# Import and include API routers
from api.v1.router import router as api_router  # noqa: E402

app.include_router(api_router, prefix='/api/v1/forge')


if __name__ == '__main__':
  import uvicorn
  uvicorn.run('src.main:app', host='0.0.0.0', port=settings.PORT, reload=True)
