# Frontend Architecture

The frontend is a React + Vite workspace for the AI+BI product shell.

## Goals

- Let users ask dashboard and analysis questions.
- Show Hermes execution logs in realtime.
- Embed Superset dashboards inside the product workspace.
- Provide local chart previews and fallback states.
- Provide the analysis panel for future report workflows.

## Current File Structure

```text
frontend/
  index.html
  package.json
  src/
    main.jsx       React entrypoint
    App.jsx        Current single-page workspace
    api.js         Backend API client
    styles.css     Application styles
```

The current MVP keeps components in `App.jsx` for speed. As the product grows, split components into `src/components/`.

## Current Components

### `StatusPill`

Shows whether a backend integration is online, configured, or missing.

Inputs:

- `service.name`
- `service.configured`
- `service.reachable`

### `ChartPreview`

Fallback chart renderer used when Superset/Hermes generation fails or when product metadata needs a quick preview.

Supports:

- KPI preview
- Bar-like preview
- Line-like preview
- Query metadata display

### `ExecutionTimeline`

Displays realtime agent progress from the streaming dashboard endpoint.

Consumes events emitted by:

```text
POST /api/dashboards/generate/stream
```

Expected event flow:

1. `log`
2. `log`
3. `dashboard`
4. `done`

### `App`

Main workspace layout:

- Left sidebar: prompt input and connector status.
- Center workspace: dashboard metadata, embedded Superset dashboard, execution logs, fallback chart previews.
- Right pane: competitor context and analysis report output.

## API Client

`src/api.js` exposes:

- `getStatus()`
- `generateDashboardStream(prompt, onEvent)`
- `publishDashboard(id)`
- `analyzeDashboard(id, competitorContext)`
- `runQuery(question)`

`generateDashboardStream` uses `fetch()` with a readable stream because native `EventSource` does not support `POST` bodies.

## Superset Embedding

The iframe source is:

```text
http://localhost:8088/superset/dashboard/{id}/
```

The user may need to be logged into Superset in the same browser. For local development, open `http://localhost:8088` and log in before using embedded dashboards.

Production should replace this with Superset embedded dashboards and guest tokens.

## Recommended Component Split

As the UI grows, split `App.jsx` into:

```text
src/components/
  ConnectorStatus.jsx
  PromptComposer.jsx
  ExecutionTimeline.jsx
  DashboardSummary.jsx
  SupersetEmbed.jsx
  ChartPreview.jsx
  AnalysisPane.jsx
  DataPlanPanel.jsx
  SimilarDashboardPicker.jsx
```

Suggested state boundaries:

- Keep request/session state in a top-level workspace container.
- Keep display-only components stateless.
- Move streaming logic into a hook such as `useDashboardGeneration`.

## UX Principles

- Show agent progress as it happens.
- Ask for confirmation before expensive or destructive actions.
- Keep Superset embedded as the main BI canvas.
- Use local previews only as fallback or metadata inspection.
- Always surface data lineage, filters, and assumptions when available.

## Near-Term Frontend Work

- Similar dashboard picker.
- Data plan confirmation panel.
- Natural-language dashboard adjustment flow.
- Upload file panel with schema preview.
- Analysis plan confirmation and report viewer.
