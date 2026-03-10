# VentureStrat — Platform Instructions

VentureStrat is a PlayformOS-derived platform. It uses FastAPI (backend), React+TypeScript+MUI (frontend), PostgreSQL, and Docker Compose infrastructure.

## Agent OS Documentation

### Product Context
- **Mission & Vision:** @.agent-os/product/mission.md
- **Technical Architecture:** @.agent-os/product/tech-stack.md
- **Development Roadmap:** @.agent-os/product/roadmap.md
- **Decision History:** @.agent-os/product/decisions.md

### Development Standards
- **Code Style:** @~/.agent-os/standards/code-style.md
- **Best Practices:** @~/.agent-os/standards/best-practices.md

### Project Management
- **Active Specs:** @.agent-os/specs/
- **Spec Planning:** Use `@~/.agent-os/instructions/create-spec.md`
- **Tasks Execution:** Use `@~/.agent-os/instructions/execute-tasks.md`

## Platform Variables

| Variable | Value |
|----------|-------|
| PLATFORM | venturestrat |
| DOMAIN_SERVICE | investor-service |
| TABLE_PREFIX | vs_ |
| DB_PORT | 15436 |
| SERVICE_PORT | 8059 |
| AUTH_PORT_EXT | 8106 |
| FRONTEND_PORT | 5178 |

## Quick Start

```bash
# Infrastructure
make infra-up                    # Start PostgreSQL, Redis, Consul, Kafka

# Backend
make service-start               # Start investor-service on :8059

# Frontend
cd services/investor-service/frontend
npm install && npm run dev       # Start Vite on :5178

# Code generation (after adding/editing entity YAMLs)
make codegen                     # Regenerate from entities/
make migrate                     # Apply DB migrations

# Testing
make test                        # Run backend + frontend tests
```

## Default Credentials

| Field | Value |
|-------|-------|
| Username | admin |
| Password | Admin123!@# |
| Tenant ID | 00000000-0000-0000-0000-000000000000 |

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| investor-service | 8059 | http://localhost:8059/docs |
| Auth Service | 8106 | http://localhost:8106/api/v1/auth/login |
| Frontend | 5178 | http://localhost:5178 |
| PostgreSQL | 15436 | psql -h localhost -p 15436 |

## Database

- **Schema:** venturestrat
- **Table prefix:** vs_
- **User:** venturestrat
- **Database:** venturestrat

## Workflow Instructions

1. Check @.agent-os/product/roadmap.md for current priorities
2. For new features: @~/.agent-os/instructions/create-spec.md
3. For task execution: @~/.agent-os/instructions/execute-tasks.md

## Important Notes

- Product-specific files in `.agent-os/product/` override global standards
- VentureStrat uses PlayformOS patterns: FastAPI, React+TS+MUI, PostgreSQL, Docker Compose
- Entity YAML definitions live in `services/investor-service/entities/`
- Codegen output: `venturestrat codegen generate services/investor-service/entities/ --output services/investor-service --outputs all --use-many2one-fk --with-frontend --with-dashboard --overwrite`
