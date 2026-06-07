# Changelog

All notable project changes are tracked here so contributors can understand product progress without reading every diff.

## Unreleased

- Document target AI+BI workflow, architecture boundaries, ADR, and parallel workstreams.

## 2026-06-07

- Initialized the AI+BI MVP repository.
- Added FastAPI backend with dashboard generation, publishing, status checks, and analysis endpoints.
- Added React frontend with prompt-driven dashboard generation, realtime agent run logs, Superset dashboard embedding, and analysis panel.
- Added isolated Hermes runtime config for Superset MCP so product runs do not inherit unrelated global MCP servers.
- Added Superset demo registration and dashboard/chart helper scripts.
- Added local fallback dashboard previews when Hermes or Superset automation fails.
