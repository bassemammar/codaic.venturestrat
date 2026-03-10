# Product Roadmap

> Last Updated: TBD
> Version: 1.0.0
> Status: Planning

## Phase 1: Core Setup

**Goal:** Define domain entities, generate full stack, verify end-to-end.

- [ ] Define entity YAMLs in `services/investor-service/entities/`
- [ ] Run codegen: `make codegen`
- [ ] Initialize database: `make db-init && make migrate`
- [ ] Seed reference data: `make seed`
- [ ] Verify: login, CRUD, dashboard, API docs

## Phase 2: Domain Logic

**Goal:** Implement business logic beyond generated CRUD.

- [ ] Custom API endpoints
- [ ] Business rules and validation
- [ ] Domain events (Kafka)
- [ ] Background tasks

## Phase 3: Frontend Polish

**Goal:** Customize UI for domain needs.

- [ ] Custom dashboard widgets
- [ ] Domain-specific pages
- [ ] Reporting and export
- [ ] User experience refinements

## Phase 4: Testing & Quality

**Goal:** Production-grade test coverage and CI/CD.

- [ ] Backend unit + integration tests
- [ ] Frontend component + E2E tests
- [ ] CI/CD pipeline active
- [ ] Coverage thresholds enforced

## Phase 5: Production

**Goal:** Deploy and operate in production.

- [ ] Production Docker configuration
- [ ] Monitoring and alerting
- [ ] Documentation
- [ ] User onboarding

## Platform Variables

| Variable | Value |
|----------|-------|
| PLATFORM | venturestrat |
| DOMAIN_SERVICE | investor-service |
| TABLE_PREFIX | vs_ |
| DB_PORT | 15436 |
| SERVICE_PORT | 8059 |

## Effort Scale

| Size | Duration |
|------|----------|
| XS | 1 day |
| S | 2-3 days |
| M | 1 week |
| L | 2 weeks |
| XL | 3+ weeks |
