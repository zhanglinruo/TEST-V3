# Architecture

## System Overview

The product is split into five layers:

1. Frontend workspace
2. Product backend
3. Hermes orchestration layer
4. Semantic and governance layer
5. Superset BI engine

```mermaid
flowchart LR
  User["User"] --> FE["AI-BI Frontend"]
  FE --> API["Product Backend API"]
  API --> Catalog["Dashboard Catalog"]
  API --> Semantic["Semantic Layer + Permissions"]
  API --> Hermes["Hermes Agent Runtime"]
  Hermes --> MCP["Superset MCP"]
  MCP --> Superset["Apache Superset"]
  API --> Uploads["Uploaded Files Store"]
  Hermes --> Reports["Analysis Report Generator"]
  Superset --> FE
  Reports --> FE
```

## Responsibilities

### Frontend Workspace

- Prompt input
- Realtime agent logs
- Similar-dashboard confirmation
- Data-plan confirmation
- Embedded Superset dashboard
- Publish/share controls
- Natural-language adjustment UI
- Deep-analysis report UI
- File upload UI

### Product Backend

- API contracts
- Streaming orchestration endpoints
- Request/session state
- Dashboard catalog
- User permissions
- Semantic-layer metadata
- Uploaded file profiling
- Hermes runtime isolation
- Result persistence

### Hermes Runtime

- Interprets user intent
- Chooses reuse vs generation path
- Calls Superset MCP tools
- Produces structured plans and results
- Runs analysis skills
- Generates analysis reports

Hermes should not own product state. It proposes and executes operations through explicit tools and returns structured outputs.

### Semantic Layer

The semantic layer describes:

- Business entities
- Datasets
- Metrics
- Dimensions
- Join relationships
- Time fields
- Access policies
- Certified data objects

Hermes receives a scoped semantic context for the current user, not unrestricted database access.

### Superset

Superset owns:

- Database connections
- Datasets
- Charts
- Dashboards
- Native filters
- BI interactions such as drill/filter/explore

The product embeds Superset dashboards and stores product-level metadata separately.

## Core Domain Objects

### BIRequest

Represents one user request.

Fields:

- `id`
- `user_id`
- `prompt`
- `mode`
- `status`
- `created_at`
- `selected_dashboard_id`
- `selected_data_plan_id`

### DashboardCatalogItem

Represents a reusable dashboard.

Fields:

- `id`
- `owner_id`
- `superset_dashboard_id`
- `title`
- `description`
- `semantic_signature`
- `dataset_ids`
- `metric_names`
- `dimension_names`
- `published`
- `visibility`
- `created_at`
- `updated_at`

### DataPlan

The confirmed plan for dashboard generation.

Fields:

- `id`
- `request_id`
- `datasets`
- `metrics`
- `dimensions`
- `relationships`
- `filters`
- `permission_constraints`
- `assumptions`
- `status`

### DashboardDraft

Product-side representation of generated or reused dashboard.

Fields:

- `id`
- `title`
- `status`
- `superset_dashboard_id`
- `chart_ids`
- `data_plan_id`
- `lineage`
- `execution_events`
- `integration_notes`

### AnalysisRun

Represents a deep-analysis job.

Fields:

- `id`
- `dashboard_ids`
- `uploaded_file_ids`
- `analysis_skill`
- `analysis_plan`
- `status`
- `report_html`
- `source_references`

## Main Workflows

### Similar Dashboard Reuse

```mermaid
sequenceDiagram
  participant U as User
  participant FE as Frontend
  participant API as Backend
  participant H as Hermes
  participant C as Catalog
  participant S as Superset

  U->>FE: Ask business question
  FE->>API: Create BI request
  API->>C: Search similar dashboards
  API->>H: Ask for reuse recommendation
  H-->>API: Similar dashboard candidates
  API-->>FE: Show candidates
  U->>FE: Choose existing dashboard
  FE->>API: Apply filters / permission scope
  API->>S: Resolve dashboard metadata
  API-->>FE: Embedded dashboard URL + metadata
```

### New Dashboard Generation

```mermaid
sequenceDiagram
  participant U as User
  participant FE as Frontend
  participant API as Backend
  participant Sem as Semantic Layer
  participant H as Hermes
  participant S as Superset MCP

  U->>FE: Ask question
  FE->>API: Create request
  API->>Sem: Get scoped data context
  API->>H: Build data plan
  H-->>API: Candidate datasets/metrics/relationships
  API-->>FE: Show data plan
  U->>FE: Confirm or adjust
  FE->>API: Confirm plan
  API->>H: Generate dashboard
  H->>S: Create datasets/charts/dashboard
  H-->>API: Superset ids + summary
  API-->>FE: Embed dashboard + execution logs
```

### Deep Analysis

```mermaid
sequenceDiagram
  participant U as User
  participant FE as Frontend
  participant API as Backend
  participant H as Hermes
  participant S as Superset
  participant F as File Profiler

  U->>FE: Request analysis
  FE->>API: Start analysis run
  API->>S: Get chart/dashboard data lineage
  API->>F: Profile uploaded files
  API->>H: Build analysis plan
  H-->>API: Sources, mappings, assumptions
  API-->>FE: Show analysis plan
  U->>FE: Confirm
  API->>H: Generate report
  H-->>API: HTML report + references
  API-->>FE: Render report
```

## API Surface To Build

### Dashboard Planning

- `POST /api/bi/requests`
- `GET /api/bi/requests/{id}/similar-dashboards`
- `POST /api/bi/requests/{id}/reuse-dashboard`
- `POST /api/bi/requests/{id}/data-plan`
- `POST /api/bi/data-plans/{id}/confirm`

### Dashboard Generation and Adjustment

- `POST /api/dashboards/generate/stream`
- `POST /api/dashboards/{id}/adjust/stream`
- `POST /api/dashboards/{id}/publish`
- `POST /api/dashboards/{id}/fork`

### Analysis

- `POST /api/uploads`
- `POST /api/analysis-runs`
- `POST /api/analysis-runs/{id}/plan`
- `POST /api/analysis-runs/{id}/run/stream`
- `GET /api/analysis-runs/{id}`

## Runtime Isolation

The product uses `.hermes-runtime/config.yaml` so backend-driven Hermes runs only see product-approved MCP servers. This prevents global Hermes MCP tools, credentials, or user experiments from leaking into product execution.

## Security And Governance

- Never pass unrestricted database catalogs to Hermes.
- Always scope semantic context by user permissions.
- Treat uploaded files as untrusted input.
- Store lineage and assumptions for generated dashboards and reports.
- Do not commit secrets or runtime logs.
- Local iframe embedding is a development convenience; production should use Superset embedded dashboards and guest tokens.
