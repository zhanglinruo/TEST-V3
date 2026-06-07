# API Documentation

The backend is a FastAPI service. When running locally, interactive API documentation is available at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Base URL

```text
http://127.0.0.1:8000/api
```

## Status

### `GET /status`

Returns connectivity status for Superset and Hermes.

Example response:

```json
{
  "superset": {
    "name": "Apache Superset",
    "configured": true,
    "reachable": true,
    "detail": "HTTP 200 at http://localhost:8088"
  },
  "hermes": {
    "name": "Hermes Agent",
    "configured": true,
    "reachable": true,
    "detail": "Hermes source found"
  }
}
```

## Query Prototype

### `POST /query`

Prototype endpoint for text-to-SQL style flows.

Request:

```json
{
  "question": "Show revenue by month",
  "user_id": "user_123"
}
```

Response:

```json
{
  "sql": "SELECT ...",
  "rows": []
}
```

## Dashboard Generation

### `POST /dashboards/generate`

Synchronous dashboard generation endpoint. Useful for smoke tests, but the frontend should prefer the streaming endpoint.

Request:

```json
{
  "prompt": "Generate a sales dashboard with revenue trend and region contribution",
  "data_source": "demo_sales",
  "user_id": "user_123"
}
```

Response: `DashboardDraft`

```json
{
  "id": "dash_abc123",
  "title": "Sales dashboard",
  "prompt": "Generate a sales dashboard",
  "status": "draft",
  "charts": [],
  "metrics": [],
  "filters": [],
  "superset_dashboard_id": 3,
  "integration_notes": [],
  "execution_events": []
}
```

### `POST /dashboards/generate/stream`

Streaming dashboard generation endpoint used by the frontend.

Transport: Server-Sent Events over a `POST` request.

Event types:

- `log`: incremental execution log
- `dashboard`: final `DashboardDraft`
- `error`: terminal error
- `done`: stream finished

Example request:

```json
{
  "prompt": "Generate a sales dashboard with revenue trend and region contribution"
}
```

Example stream:

```text
event: log
data: {"message":"Starting Hermes dashboard agent."}

event: log
data: {"message":"MCP: registered 141 tool(s) from 1 server(s)"}

event: dashboard
data: {"id":"dash_abc123","status":"draft"}

event: done
data: {}
```

Implementation note: because browser `EventSource` does not support `POST`, the frontend consumes this endpoint with `fetch()` and a `ReadableStream`.

## Dashboard List

### `GET /dashboards`

Returns in-memory dashboard drafts for the current backend process.

Current MVP limitation: dashboard state is not persisted across backend restarts.

## Publish Dashboard

### `POST /dashboards/{dashboard_id}/publish`

Publishes a dashboard draft. If a Superset dashboard id exists, the backend calls Superset to publish it.

Response:

```json
{
  "dashboard": {},
  "share_url": "http://localhost:8088/superset/dashboard/3/"
}
```

## Analyze Dashboard

### `POST /dashboards/{dashboard_id}/analyze`

Generates a first-pass HTML analysis report from saved dashboard metadata.

Query parameters:

- `competitor_context`: optional pasted context or summary from competitor data

Response:

```json
{
  "dashboard_id": "dash_abc123",
  "title": "Deep analysis: Sales dashboard",
  "html": "<article>...</article>",
  "source_chart_ids": [],
  "notes": []
}
```

## Planned APIs

See [Architecture](ARCHITECTURE.md) for planned APIs around:

- Similar dashboard search
- Data-plan confirmation
- Dashboard adjustment
- File upload and profiling
- Analysis-run planning and streaming execution
