# ADR-001: Separate Product State From Hermes And Superset Execution

## Status

Accepted

## Date

2026-06-07

## Context

The product needs Hermes to reason over user intent and Superset to provide mature BI functionality such as charts, dashboards, filters, drill paths, and publishing.

If the product stores all state only in Superset, it becomes hard to manage natural-language planning, similarity search, analysis lineage, uploaded files, user-specific forks, and product-specific permissions.

If Hermes owns persistent state, product behavior becomes difficult to audit and reproduce.

## Decision

Use a three-part boundary:

- Product backend owns product state, workflow state, catalog metadata, permissions, uploaded files, and report metadata.
- Hermes owns reasoning, planning, tool selection, and report generation.
- Superset owns BI execution assets: databases, datasets, charts, dashboards, filters, and BI interactions.

Hermes runs through an isolated product runtime config so it only sees approved MCP tools for product workflows.

## Alternatives Considered

### Put Everything In Superset

Pros:

- Less product persistence to build.
- Superset already stores dashboards and charts.

Cons:

- Weak fit for natural-language workflow state.
- Harder to support uploaded-file analysis.
- Harder to track AI assumptions, analysis lineage, and user-specific forks.

Rejected because the product needs AI workflow state beyond BI asset storage.

### Let Hermes Own Workflow State

Pros:

- Faster to prototype.
- Agent can store context naturally.

Cons:

- Hard to audit.
- Hard to coordinate multiple users.
- Hard to enforce permissions.
- Hard to recover and version product workflows.

Rejected because BI workflows require durable, auditable state.

### Product Backend Owns State, Hermes/Superset Execute

Pros:

- Clear security boundary.
- Easy to version and audit.
- Supports parallel development.
- Keeps Superset replaceable as an engine.
- Keeps Hermes replaceable as an agent runtime.

Cons:

- Requires product metadata models.
- Requires integration contracts between backend, Hermes, and Superset.

Accepted.

## Consequences

- We need product-side models for dashboard catalog, data plans, analysis runs, uploads, and lineage.
- We need structured Hermes outputs and robust parsing/validation.
- We need to keep Superset ids mapped into product metadata.
- Production embedding should use guest tokens and permission mapping rather than local iframe settings.
