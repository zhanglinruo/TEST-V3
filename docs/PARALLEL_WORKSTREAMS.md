# Parallel Development Workstreams

This document breaks the target product into parallel tracks so multiple people or agents can work without stepping on each other.

## Workstream A: Dashboard Catalog And Similarity

Goal: Detect whether a user question can reuse an existing dashboard.

Deliverables:

- Product-side dashboard catalog table/model.
- Semantic signature for each dashboard.
- Similar-dashboard search API.
- Candidate explanation payload.
- Frontend candidate selection UI.

Backend files likely touched:

- `backend/app/dashboard_builder/`
- `backend/app/data_models/`
- `backend/app/api/routes.py`

Frontend files likely touched:

- `frontend/src/App.jsx`
- New components under `frontend/src/components/`

Acceptance criteria:

- User asks a question and sees similar dashboard candidates.
- Each candidate shows title, owner/published state, matching metrics/dimensions, and reason for match.
- User can choose reuse or regenerate.

## Workstream B: Semantic Layer And Permission Scope

Goal: Give Hermes a scoped description of usable data objects.

Deliverables:

- Semantic-layer schema for datasets, metrics, dimensions, joins, and relationships.
- User permission model placeholder.
- API to return scoped semantic context.
- Data-plan object generated from semantic context.

Backend files likely touched:

- `backend/app/semantic_layer/`
- `backend/app/core/`
- `backend/app/data_models/`

Acceptance criteria:

- A user request returns candidate datasets, metrics, dimensions, and relationships.
- Permission constraints are visible in the returned data plan.
- Hermes prompt receives only scoped semantic context.

## Workstream C: Data Plan Confirmation UI

Goal: Let the user inspect and adjust Hermes' proposed data plan before creating BI assets.

Deliverables:

- Data-plan confirmation panel.
- Natural-language adjustment loop.
- Confirm/regenerate controls.
- Plan diff display.

Frontend files likely touched:

- `frontend/src/App.jsx`
- `frontend/src/api.js`
- New plan components.

Backend files likely touched:

- `backend/app/api/routes.py`
- `backend/app/dashboard_builder/`

Acceptance criteria:

- User can see candidate datasets/metrics/relationships.
- User can ask Hermes to adjust the plan.
- Dashboard generation only starts after confirmation.

## Workstream D: Superset Dashboard Generation

Goal: Make dashboard generation robust and traceable.

Deliverables:

- Stable Hermes structured output parser.
- Superset MCP result validation.
- Dashboard layout creation.
- Native filters.
- Publish/fork support.
- Better error and fallback handling.

Backend files likely touched:

- `backend/app/integrations/hermes.py`
- `backend/app/integrations/superset.py`
- `tools/create_superset_demo_charts.py`

Acceptance criteria:

- Hermes creates or reuses datasets/charts/dashboard through Superset MCP.
- Product stores Superset ids and chart lineage.
- Realtime logs show meaningful progress.
- Errors are specific enough for users and developers.

## Workstream E: Dashboard Adjustment And Versioning

Goal: Let users modify existing dashboards naturally and publish their own version.

Deliverables:

- Dashboard fork/version model.
- Natural-language adjustment endpoint.
- Change preview before applying.
- Publish adjusted dashboard.

Acceptance criteria:

- User can ask "add channel filter" or "replace bar chart with line chart".
- Product shows a proposed change summary.
- Shared dashboards are not mutated without explicit permission.

## Workstream F: File Upload And Profiling

Goal: Let users upload Excel/CSV files for analysis.

Deliverables:

- Upload API.
- File storage abstraction.
- Excel/CSV schema profiler.
- Preview UI.
- Mapping suggestions to semantic entities.

Backend files likely touched:

- New `backend/app/uploads/`
- `backend/app/data_models/`

Frontend files likely touched:

- Upload control in analysis pane.

Acceptance criteria:

- User uploads an Excel/CSV file.
- Product displays sheets/columns/sample rows.
- Hermes can reference the uploaded file in an analysis plan.

## Workstream G: Deep Analysis Reports

Goal: Generate grounded reports from dashboards, related data, and uploaded files.

Deliverables:

- AnalysisRun model.
- Analysis plan confirmation.
- Analysis skill selection.
- HTML report generation.
- Source references.

Backend files likely touched:

- `backend/app/analysis_engine/`
- New `backend/app/reports/`

Frontend files likely touched:

- `frontend/src/App.jsx`
- Analysis report components.

Acceptance criteria:

- User can start analysis from a dashboard.
- Product shows source dashboards/charts/files before running.
- Report includes assumptions and source references.

## Workstream H: Production Embedding And Auth

Goal: Replace local iframe convenience with production-safe embedding.

Deliverables:

- Superset embedded dashboard setup.
- Guest token backend endpoint.
- User identity and row-level security mapping.
- Secure iframe embedding.

Acceptance criteria:

- Embedded Superset works without requiring user to separately log into Superset.
- Row-level policies match product permissions.
- No broad iframe or insecure cookie settings are required in production.

## Suggested Implementation Order

1. Dashboard catalog data model.
2. Similar-dashboard search placeholder.
3. Semantic data-plan API.
4. Data-plan confirmation UI.
5. Superset generation hardening.
6. Dashboard adjustment/forking.
7. Upload profiling.
8. Deep analysis planning and report generation.
9. Production embedding/auth.

## Branch Naming

Use focused branches:

- `feature/dashboard-catalog`
- `feature/semantic-data-plan`
- `feature/data-plan-ui`
- `feature/dashboard-adjustment`
- `feature/upload-profiling`
- `feature/deep-analysis`
- `feature/embedded-auth`
