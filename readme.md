# TrustGrid — Production-Grade B2B SaaS Platform

[CI Pipeline](https://www.google.com/search?q=https://github.com/taizeem/trustgrid/actions/workflows/ci.yml)
[Security Audit](https://www.google.com/search?q=https://github.com/taizeem/trustgrid/actions/workflows/security.yml)
[](https://opensource.org/licenses/MIT)
[](https://python.org)
[](https://go.dev)
[](https://www.rust-lang.org)

TrustGrid is an enterprise-grade, multi-tenant B2B SaaS platform engineered for third-party vendor risk management, security assessments, automated compliance audits, workflow state orchestration, and deterministic risk scoring.

The platform is designed around strict microservice boundaries, independent relational data ownership across seven isolated PostgreSQL databases, asynchronous inter-service event communication via RabbitMQ with a Transactional Outbox pattern, Traefik edge routing with defense-in-depth security headers, and Prometheus/Grafana operational telemetry.

---

## Architecture & Operational Topology

```
                                  [ Enterprise Clients & External API Consumers ]
                                                         │
                                                         ▼ HTTPS / TLS :8088
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                 TRAEFIK v3.1 API GATEWAY                                                │
│  • Edge Security Headers: HSTS (max-age=31536000), FrameDeny (DENY), nosniff, strict-origin-when-cross-origin, CSP     │
│  • Rate Limiting: 50 req/s (100 burst)  │  Correlation Tracing: X-Correlation-ID  │  Metrics Exporter: :8080/metrics   │
└────────────────────────┬───────────────────────────────────────────────────────────────────────────────┬────────────────┘
                         │                                                                               │
                         ▼ Synchronous REST Ingress                                                      ▼ Telemetry Poll
┌──────────────────────────────────────────────────────────────────────────────────┐   ┌──────────────────────────────────┐
│                               POLYGLOT MICROSERVICES                             │   │    OBSERVABILITY & TELEMETRY     │
│                                                                                  │   │                                  │
│  ┌──────────────────────────┐   ┌──────────────────────────┐                     │   │  ┌────────────────────────────┐  │
│  │     Identity & Tenant    │   │   Vendor & Assessment    │ (Transactional      │   │  │  Prometheus v2.53 (:9090)  │  │
│  │   Python 3.12 / DRF      │   │   Python 3.12 / DRF      │──┐ Outbox Event     │   │  │  • Scrapes GW & Services   │  │
│  │   Port: 8001             │   │   Port: 8002             │  │ Relay            │   │  │  • Evaluates alert_rules   │  │
│  └─────────────┬────────────┘   └─────────────┬────────────┘  │                  │   │  └──────────────┬─────────────┘  │
│                │                              │               │                  │   │                 │                │
│  ┌─────────────▼────────────┐   ┌─────────────▼────────────┐  │                  │   │                 ▼ Auto-Datasource│
│  │      Workflow Engine     │   │    Document Processing   │  │                  │   │  ┌────────────────────────────┐  │
│  │   Go 1.22 / Concurrency  │   │   Rust 2021 / Axum       │  │                  │   │  │    Grafana v11.0 (:3000)   │  │
│  │   Port: 8003             │   │   Port: 8004             │  │                  │   │  │  • Platform Health Dash    │  │
│  └─────────────┬────────────┘   └─────────────┬────────────┘  │                  │   │  │  • p95 Latency & Queue Lag │  │
│                │                              │               │                  │   │  └────────────────────────────┘  │
│  ┌─────────────▼────────────┐   ┌─────────────▼────────────┐  │                  │   └──────────────────────────────────┘
│  │   Deterministic Risk     │   │  Integrations & Webhooks │  │                  │
│  │   Rust 2021 / Pure Rules │   │   Go 1.22 / HMAC-SHA256  │  │                  │
│  │   Port: 8005             │   │   Port: 8006             │  │                  │
│  └─────────────┬────────────┘   └─────────────┬────────────┘  │                  │
│                │                              │               │                  │
│  ┌─────────────▼────────────┐   ┌─────────────▼────────────┐  │                  │
│  │     Billing & Usage      │   │     Audit & Reporting    │  │                  │
│  │   Python 3.12 / DRF      │   │   Python 3.12 / DRF      │  │                  │
│  │   Port: 8007             │   │   Port: 8008             │  │                  │
│  └─────────────┬────────────┘   └─────────────▲────────────┘  │                  │
└────────────────┼──────────────────────────────┼───────────────┼──────────────────┘
                 │ Independent Connection Pools │               │
                 ▼                              │               ▼
┌────────────────────────────────────────────┐  │  ┌──────────────────────────────────────────────────────────────┐
│       POSTGRESQL 16 CLUSTER (7 DBs)        │  │  │                  RABBITMQ 3.13 MESSAGE BROKER                │
│                                            │  │  │                                                              │
│  • trustgrid_identity   • trustgrid_integ  │  │  │  Topic Exchange: trustgrid.events                            │
│  • trustgrid_vendor     • trustgrid_billing│  └──┼─►  Routing Key: vendor.assessment.submitted.v1              │
│  • trustgrid_workflow   • trustgrid_audit  │     │  Dead Letter:   trustgrid.dlx (Exponential Backoff x3)       │
│  • trustgrid_document                      │     │  Consumer Lag:  Exposed via :15692 Metrics                   │
└────────────────────────────────────────────┘     └──────────────────────────────────────────────────────────────┘
```

---

## Service Responsibilities & Domain Matrix

| Service | Technology Stack | Owned Database | Primary Responsibilities |
| :--- | :--- | :--- | :--- |
| **Identity & Tenant** | Python 3.12, Django REST, `uv` | `trustgrid_identity` | Organizations, tenant membership, user auth, invitations, role permissions (RBAC). |
| **Vendor & Assessment** | Python 3.12, Django REST, `uv` | `trustgrid_vendor` | Vendor catalog, questionnaires, assessment answers, versions, transactional outbox publishing. |
| **Workflow Engine** | Go 1.22, standard library, `pq` | `trustgrid_workflow` | State machine transitions, optimistic locking, concurrency control, approval assignments. |
| **Document Processing**| Rust 2021, Axum, Tokio, SQLx | `trustgrid_document` | Evidence metadata, SHA-256 validation, S3 object storage integration, async parsing. |
| **Risk Computation** | Rust 2021, Axum, Serde | In-memory / pure compute | Deterministic scoring algorithms, weighted factor calculations, explainable risk trees. |
| **Integrations & Webhooks** | Go 1.22, Crypto HMAC | `trustgrid_integrations` | Outbound webhooks, HMAC-SHA256 request signing, SSRF mitigation, retry policies. |
| **Billing & Usage** | Python 3.12, Django REST, `uv` | `trustgrid_billing` | Subscription plans, feature quotas, usage ingestion with idempotency, Stripe sandbox. |
| **Audit & Reporting** | Python 3.12, Django REST, `uv` | `trustgrid_audit` | AMQP consumer for domain events, immutable append-only audit trail, compliance reports. |
| **API Gateway** | Traefik v3.1 | Gateway Config | Reverse proxy, path routing, rate limiting, HSTS/CSP security headers, correlation IDs. |

---

## Technology Stack Details

- **Application Languages**: Python 3.12 (managed via `uv`), Go 1.22, Rust 1.78+ (Edition 2021).
- **Web Frameworks**: Django 5.1 / Django REST Framework 3.15, Go `net/http` standard library, Rust Axum 0.7.
- **Relational Storage**: PostgreSQL 16 Alpine with 7 decoupled database schemas and dedicated least-privilege user accounts.
- **Asynchronous Messaging**: RabbitMQ 3.13 Management Alpine with topic exchanges, transactional outbox publishing, and dead-letter routing.
- **Caching & Ephemeral State**: Redis 7 Alpine with authenticated access.
- **Gateway & Ingress**: Traefik v3.1 with dynamic file provider.
- **Monitoring & Metrics**: Prometheus v2.53 and Grafana v11.0.
- **Code Quality & Testing**: `pytest`, `pytest-django`, `ruff` (Python), `go test -race`, `go vet` (Go), `cargo test`, `cargo clippy` (Rust), and `locust` (load testing).

---

## Repository Structure

```
trustgrid/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Multi-language CI matrix (Python, Go, Rust, Compose)
│       └── security.yml           # Security audit (Trivy, Bandit, Gitleaks)
├── docs/
│   ├── benchmarks/
│   │   └── load-test-baseline.md  # Documented p50/p95/p99 latency and throughput baselines
│   ├── decisions/
│   │   ├── adr-001-microservices-boundaries.md
│   │   └── adr-002-production-readiness.md
│   └── runbooks/
│       ├── disaster-recovery.md   # RPO/RTO SLAs, multi-service recovery ordering
│       └── secret-rotation.md     # Zero-downtime JWT and database secret rotation
├── infrastructure/
│   ├── backups/                   # Timestamped database dumps (.dump)
│   ├── docker/
│   │   └── postgres/
│   │       ├── init-databases.sh
│   │       └── init-databases.sql # Multi-database and role provisioning
│   ├── gateway/
│   │   ├── dynamic_conf.yaml      # Traefik routes, security headers, rate limiting
│   │   └── traefik.yaml           # Traefik global entrypoints and logging
│   ├── monitoring/
│   │   ├── grafana/
│   │   │   ├── dashboards/
│   │   │   │   └── trustgrid-overview.json
│   │   │   └── provisioning/
│   │   │       ├── dashboards/dashboards.yml
│   │   │       └── datasources/datasource.yml
│   │   └── prometheus/
│   │       ├── alert_rules.yml    # SLO alerts (p95 latency, 5xx, queue backlog)
│   │       └── prometheus.yml     # Scrape targets across services and gateway
│   └── scripts/
│       ├── backup-databases.ps1   # Multi-database backup script using docker cp
│       ├── restore-databases.ps1  # Automated point-in-time restore drill
│       ├── run-load-tests.ps1     # Headless Locust load runner
│       └── verify-production.ps1  # Comprehensive platform verification audit
├── services/
│   ├── audit-reporting-service/   # Django event consumer & reporting microservice
│   ├── billing-service/           # Django subscription plans, quotas, and Stripe sandbox
│   ├── document-service/          # Rust Axum file processor & metadata storage
│   ├── identity-service/          # Django tenant auth, memberships, and JWT issuance
│   ├── integrations-service/      # Go outbound webhook dispatcher with HMAC signatures
│   ├── risk-service/              # Rust Axum deterministic scoring engine
│   ├── vendor-assessment-service/ # Django vendor lifecycle, assessments, and outbox publisher
│   └── workflow-service/          # Go approval workflow state machine
├── tests/
│   ├── conftest.py                # Pytest shared fixtures & API client wrapper
│   ├── integration/
│   │   ├── test_e2e_workflow.py   # Full platform lifecycle end-to-end integration
│   │   ├── test_event_schemas.py  # CloudEvents contract validation
│   │   └── test_fault_injection.py# Idempotency, atomic rollbacks, concurrency locks
│   └── load/
│       └── locustfile.py          # Distributed multi-tenant load testing scenario
├── .env.example                   # Local development configuration template
├── .env.production.example        # Hardened production configuration template
├── compose.yaml                   # Complete multi-service local infrastructure orchestration
├── pyproject.toml                 # Monorepo uv specification & unified ruff rules
└── README.md
```

---

## Prerequisites

- **Git**: 2.38+
- **Docker & Docker Compose**: Docker Desktop 4.25+ or Docker Engine 24.0+ with Compose v2.20+
- **Python**: 3.12+ with `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `winget install astral-sh.uv`)
- **Go**: 1.22+ (for running Go unit tests locally)
- **Rust**: 1.78+ with Cargo (for running Rust tests locally)

---

## Local Setup & Quickstart

### 1. Clone the Repository

```bash
git clone https://github.com/taizeem/trustgrid.git
cd trustgrid
```

### 2. Configure Environment

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux / macOS
cp .env.example .env
```

### 3. Build & Launch the Entire Platform

```powershell
docker compose up -d --build
```

---

## Production Verification & Live Audit

Execute the automated Phase 13 verification suite to audit security headers, health endpoints, metrics scraping, backup drills, and integration tests:

```powershell
.\infrastructure\scripts\verify-production.ps1
```

Expected output:
```

[1/5] Auditing API Gateway Security Headers...
  [OK] Gateway enforces Security Headers (FrameDeny: 'DENY', HSTS: 'max-age=31536000')!

[2/5] Auditing Microservices Health & Liveness...
  [OK] Identity Service is healthy (Status: healthy)
  [OK] Vendor Service is healthy (Status: healthy)
  [OK] Workflow Service is healthy (Status: healthy)
  [OK] Document Service is healthy (Status: healthy)
  [OK] Risk Service is healthy (Status: healthy)
  [OK] Integrations Service is healthy (Status: healthy)
  [OK] Billing Service is healthy (Status: healthy)
  [OK] Audit Service is healthy (Status: healthy)

[3/5] Auditing Prometheus & Grafana Telemetry...
  [OK] Prometheus is scraping 9 active service targets!

[4/5] Executing Automated Database Backup Drill...
  [OK] All 7 microservice databases backed up cleanly to infrastructure\backups\<timestamp>

[5/5] Running Platform Integration & Isolation Suite...
  tests/integration/test_e2e_workflow.py::test_full_platform_lifecycle PASSED
  tests/integration/test_event_schemas.py::test_assessment_submitted_event_contract PASSED
  tests/integration/test_fault_injection.py::test_idempotent_duplicate_billing_events PASSED
  tests/integration/test_fault_injection.py::test_outbox_atomic_rollback_on_database_failure PASSED
  tests/integration/test_fault_injection.py::test_cross_tenant_isolation_under_concurrency PASSED
  tests/integration/test_fault_injection.py::test_concurrent_workflow_transitions_optimistic_locking PASSED
  [OK] All platform integration tests passed!


```

---

## Disaster Recovery & Backup Drills

### 1. Run Decoupled Database Backups

Takes independent PostgreSQL snapshots of each service database into timestamped directories using `docker cp`:

```powershell
.\infrastructure\scripts\backup-databases.ps1
```

### 2. Execute Point-in-Time Restoration Drill

Restores all seven service databases from the latest backup (or a specified timestamp):

```powershell
# Automatically restores the newest backup
.\infrastructure\scripts\restore-databases.ps1

# Or target a specific timestamp
.\infrastructure\scripts\restore-databases.ps1 -BackupTimestampDir infrastructure\backups\20261102_120407
```

---

## Performance & Load Testing

Execute headless multi-tenant load testing exercising concurrent vendor creation, assessment submissions, and risk calculations:

```powershell
# Run 50 concurrent tenant sessions for 45 seconds
.\infrastructure\scripts\run-load-tests.ps1 -Users 50 -SpawnRate 10 -RunTime "45s"
```

Performance baseline summary:
- `GET /api/v1/vendors/` (Django): **142 req/s**, p95: **28.5 ms**
- `POST /api/v1/risk/compute` (Rust): **48 req/s**, p95: **8.2 ms**
- Full benchmark report: [docs/benchmarks/load-test-baseline.md](https://www.google.com/search?q=docs/benchmarks/load-test-baseline.md).

---

## Automated Test Suites

### Python Microservices (`uv` + `pytest` + `ruff`)

```powershell
# Monorepo linting check
uv run ruff check .

# Monorepo format check
uv run ruff format --check .

# Service unit tests
uv run pytest services/identity-service/tests/ -v
uv run pytest services/vendor-assessment-service/tests/ -v
uv run pytest services/billing-service/tests/ -v
uv run pytest services/audit-reporting-service/tests/ -v

# Platform integration tests
python -m pytest tests/ -v
```

### Go Microservices (`go test` with race detector)

```powershell
cd services/workflow-service
go test -v -race ./...
cd ../..

cd services/integrations-service
go test -v -race ./...
cd ../..
```

### Rust Microservices (`cargo test` + `cargo clippy`)

```powershell
cd services/risk-service
cargo clippy --all-targets -- -D warnings
cargo test
cd ../..

cd services/document-service
cargo clippy --all-targets -- -D warnings
cargo test
cd ../..
```

---

## API Documentation & Example Requests

All API routes are exposed through Traefik Gateway at port **`8088`**.

### 1. Register User & Create Organization (Identity Service)

```bash
curl -X POST http://localhost:8088/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme-corp.com",
    "password": "SecurePassword123!",
    "first_name": "Alice",
    "last_name": "Admin"
  }'
```

Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "e6a2b8e0-f38b-4b68-9842-bc08a8d052fa",
    "email": "admin@acme-corp.com"
  }
}
```

### 2. Create Vendor (Vendor Service)

```bash
curl -X POST http://localhost:8088/api/v1/vendors/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cloudflare Edge Services",
    "website": "https://cloudflare.com",
    "tier": "tier_1",
    "primary_contact_name": "Security Operations"
  }'
```

### 3. Deterministic Risk Computation (Rust Service)

```bash
curl -X POST http://localhost:8088/api/v1/risk/compute \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_id": "c1f7a0b4-3a2b-4c5d-8e9f-0123456789ab",
    "answers": {
      "mfa_enforced": "compliant",
      "data_encryption_at_rest": "compliant",
      "annual_soc2_audit": "non_compliant"
    }
  }'
```

Response:
```json
{
  "vendor_id": "c1f7a0b4-3a2b-4c5d-8e9f-0123456789ab",
  "score": 72.5,
  "risk_tier": "Medium",
  "explainability": [
    { "factor": "mfa_enforced", "weight": 35.0, "status": "compliant", "contribution": 35.0 },
    { "factor": "data_encryption_at_rest", "weight": 35.0, "status": "compliant", "contribution": 35.0 },
    { "factor": "annual_soc2_audit", "weight": 30.0, "status": "non_compliant", "contribution": 2.5 }
  ],
  "calculated_at": "2026-11-02T12:00:00Z"
}
```

### 4. Transition Workflow State (Go Service)

```bash
curl -X POST http://localhost:8088/api/v1/workflows/b8d9c0e1-2a3b-4c5d-6e7f-890123456789/transitions \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "comment": "Security controls verified in SOC2 report.",
    "version": 1
  }'
```

---

## Architectural Decisions (ADRs)

1. [ADR 001: Polyglot Microservices Boundaries \& Independent Data Ownership](https://www.google.com/search?q=docs/decisions/adr-001-microservices-boundaries.md)
   - Adopts a polyglot monorepo partitioned strictly by domain boundaries.
   - Prohibits cross-database foreign keys, joins, and shared ORM models.
2. [ADR 002: Production Readiness, Container Isolation \& Observability](https://www.google.com/search?q=docs/decisions/adr-002-production-readiness.md)
   - Mandates non-root container users, edge security headers, rate limiting, and unified Prometheus metrics polling.

---

## Known Limitations & Roadmap

- **Storage Backend**: Currently configured for local MinIO / S3 emulation. Production deployment requires setting `S3_ENDPOINT` to AWS S3 or Google Cloud Storage.
- **Asymmetric JWT**: Development uses symmetric HMAC-SHA256 tokens (`HS256`). For zero-shared-secret verification at scale, transition to RS256 / EdDSA using an OIDC JWKS endpoint.
- **Distributed Tracing**: Metrics are fully scraped via Prometheus. Future iterations will introduce OpenTelemetry tracing with Grafana Tempo.

---

## Contributing & License

1. Fork repository: [https://github.com/taizeem/trustgrid](https://www.google.com/search?q=https://github.com/taizeem/trustgrid)
2. Create feature branch: `git checkout -b feat/your-feature`
3. Commit changes following conventional commits: `git commit -m "feat(scope): describe change"`
4. Push to branch: `git push origin feat/your-feature`
5. Open a Pull Request.

Licensed under the [MIT License](https://www.google.com/search?q=LICENSE).
