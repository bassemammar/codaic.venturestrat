# Technical Stack

> Last Updated: TBD
> Version: 1.0.0

## Architecture Overview

VentureStrat is a PlayformOS-derived platform using FastAPI backend, React frontend, PostgreSQL, and Docker Compose infrastructure.

## Backend

| Component | Technology | Version | Notes |
|-----------|-----------|---------|-------|
| Language | Python | 3.11+ | Async support |
| Framework | FastAPI | 0.100+ | OpenAPI auto-docs |
| ORM | SQLAlchemy | 2.0+ | Async, declarative models |
| Migrations | Alembic | 1.12+ | Auto-generated from ORM |
| CLI | Typer | 0.9+ | CLI commands |
| Validation | Pydantic | 2.0+ | Request/response schemas |

## Frontend

| Component | Technology | Version | Notes |
|-----------|-----------|---------|-------|
| Framework | React | 18+ | TypeScript 5+ |
| Build Tool | Vite | 5+ | Dev server + builds |
| UI Library | MUI | 5+ | Material Design |
| Data Fetching | TanStack Query | 5+ | Caching, pagination |
| State | Zustand | 4+ | Auth store |
| Charts | Recharts | 2+ | Dashboard widgets |
| Grid | react-grid-layout | 1.4+ | Dashboard drag-and-drop |

## Database

| Component | Technology | Port | Notes |
|-----------|-----------|------|-------|
| Primary DB | PostgreSQL 16+ | 15436 | Schemas: venturestrat, auth, registry, shared, audit |
| Cache | Redis 7.2+ | 16379 | Rate limiting, sessions |
| Discovery | Consul 1.17+ | 8500 | Service registration |
| Events | Kafka 7.5+ | 19092 | Event bus |

## Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| Containers | Docker + Compose | Multi-file compose |
| Network | venturestrat-network | Bridge network |

## Services

| Service | Port | Description |
|---------|------|-------------|
| investor-service | 8059 | Domain service API |
| auth-service | 8106 | JWT authentication |
| registry-service | 8080 | Tenant & model registry |
| Frontend (Vite) | 5178 | React dev server |
