# VentureStrat Platform Makefile
.PHONY: help infra-up infra-down infra-logs obs-up obs-down obs-logs service-start service-stop codegen migrate seed test status clean

help:
	@echo ""
	@echo "VentureStrat Platform - Development Commands"
	@echo "========================================="
	@echo ""
	@echo "Infrastructure:"
	@echo "  make infra-up        Start infrastructure (PostgreSQL, Redis, Consul, Kafka)"
	@echo "  make infra-down      Stop infrastructure"
	@echo "  make infra-logs      View infrastructure logs"
	@echo ""
	@echo "Observability:"
	@echo "  make obs-up          Start observability (Prometheus, Grafana, Loki)"
	@echo "  make obs-down        Stop observability stack"
	@echo "  make obs-logs        View observability logs"
	@echo ""
	@echo "Services:"
	@echo "  make service-start   Start investor-service (uvicorn on :8059)"
	@echo "  make service-stop    Stop investor-service"
	@echo ""
	@echo "Code Generation:"
	@echo "  make codegen         Regenerate all code from YAML entities"
	@echo ""
	@echo "Database:"
	@echo "  make db-init         Initialize Alembic for investor-service"
	@echo "  make migrate         Generate and apply database migrations"
	@echo "  make seed            Load seed data"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run all tests (pytest + vitest)"
	@echo "  make test-backend    Run backend tests only"
	@echo "  make test-frontend   Run frontend tests only"
	@echo ""
	@echo "Utilities:"
	@echo "  make status          Show running containers"
	@echo "  make clean           Clean up containers and volumes"
	@echo "  make install         Install CLI and service dependencies"
	@echo ""

# Infrastructure
infra-up:
	docker compose -f docker-compose.infra.yaml up -d
	@echo "Infrastructure started. PostgreSQL: localhost:15436, Redis: localhost:16379"

infra-down:
	docker compose -f docker-compose.infra.yaml down

infra-logs:
	docker compose -f docker-compose.infra.yaml logs -f

# Observability
obs-up:
	docker compose -f docker-compose.observability.yaml up -d
	@echo "Observability started. Grafana: localhost:3001, Prometheus: localhost:9090"

obs-down:
	docker compose -f docker-compose.observability.yaml down

obs-logs:
	docker compose -f docker-compose.observability.yaml logs -f

# Services
service-start:
	cd services/investor-service && uvicorn src.investor_service.main:app --reload --port 8059

service-stop:
	@pkill -f "uvicorn.*investor_service" || echo "No investor-service process found"

# Code Generation
codegen:
	venturestrat codegen generate services/investor-service/entities/ \
		--output services/investor-service \
		--outputs all \
		--use-many2one-fk \
		--with-frontend \
		--overwrite

# Database
db-init:
	venturestrat db init investor-service

migrate:
	venturestrat db generate investor-service -m "Schema update"
	venturestrat db upgrade investor-service

seed:
	venturestrat seed investor-service --verbose

# Testing
test: test-backend test-frontend

test-backend:
	cd services/investor-service && python -m pytest --cov --cov-report=term-missing

test-frontend:
	cd services/investor-service/frontend && npm test -- --run

# Utilities
status:
	@docker ps --filter "name=venturestrat" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

clean:
	docker compose -f docker-compose.infra.yaml down -v
	docker compose -f docker-compose.observability.yaml down -v 2>/dev/null || true
	@echo "Cleaned up containers and volumes"

install:
	pip install -e cli/
	pip install agent-os
	cd services/investor-service && pip install -e ".[dev]" 2>/dev/null || pip install -r requirements.txt 2>/dev/null || echo "No service deps to install yet"
