# ADR 001: Polyglot Microservices Boundaries and Independent Data Ownership

## Status
Accepted

## Context
TrustGrid handles multi-tenant compliance, workflows, and risk calculation. Different subdomains have divergent operational profiles:
- Identity and Vendor management require rich relational ORM modeling and rapid administrative interface customization.
- Workflow processing requires high-concurrency state machine guarantees without runtime garbage collection latency spikes.
- Risk scoring requires deterministic, reproducible mathematical calculations with zero side effects.

## Decision
1. We adopt a polyglot microservices architecture organized in a monorepo.
2. Services are partitioned strictly by bounded contexts:
   - Python/Django for Identity & Tenant, Vendor & Assessment, Billing.
   - Go for Workflow State Engine, Webhooks Dispatcher.
   - Rust for Document Processing, Risk Computation.
3. Every microservice owns its database schema. Direct cross-database joins are prohibited.
4. Inter-service data sharing occurs via REST APIs or CloudEvents-compatible RabbitMQ messages.

## Consequences
- Requires independent database migration lifecycles for each service.
- Requires robust local Docker infrastructure orchestration.
- Eliminates single points of failure and avoids monolithic schema locks.
