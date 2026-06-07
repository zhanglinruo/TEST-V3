# AI+BI Product Specification

## Objective

Build an AI-assisted BI workspace where a user can ask a business question in natural language, reuse or generate dashboards, adjust dashboards through conversation, publish reusable BI assets, and run deep analysis that combines dashboard data, related dashboards, semantic-layer context, and uploaded files such as Excel.

The product should feel like one coherent AI+BI system:

- Hermes is the planning and reasoning agent.
- Superset is the BI execution and visualization engine.
- The product frontend is the unified workspace for confirmation, preview, publishing, embedding, and analysis.
- The semantic layer and permission system decide what data is available and safe to use.

## Core User Journey

### 1. User Asks a Question

The user enters a natural-language request, for example:

> Show me sales performance by region and channel for this quarter.

The backend creates a `BIRequest` and sends it to Hermes with user identity, permissions, semantic-layer metadata, and dashboard catalog context.

### 2. Similar Dashboard Detection

Hermes first checks whether similar dashboards already exist.

Similarity should consider:

- Business intent
- Metrics and dimensions
- Dataset lineage
- Filters and time ranges
- User/team ownership
- Published dashboard catalog metadata
- Permission visibility

If similar dashboards exist, the user must choose:

- View and adapt an existing dashboard
- Generate a new dashboard

### 3. Existing Dashboard Path

If the user chooses an existing dashboard:

1. Load the dashboard metadata and embedded Superset view.
2. Apply user-specific permission filters and requested filters.
3. Let the user inspect the result in the product workspace.
4. If the user asks for changes, Hermes updates filters, chart selection, layout, metrics, or derived chart specs.
5. The user can publish the adjusted version as their own dashboard.

This creates a new dashboard version or fork instead of mutating a shared dashboard without confirmation.

### 4. New Dashboard Path

If no similar dashboard exists, or the user asks to regenerate:

1. Hermes uses the semantic layer and permissions to identify available datasets, data objects, metrics, dimensions, joins, and relationships.
2. The product shows a "data planning" confirmation view:
   - Candidate datasets
   - Candidate metrics
   - Candidate dimensions
   - Join paths and relationships
   - Permission constraints
   - Assumptions and missing information
3. The user can adjust this plan in natural language.
4. After user confirmation, Hermes creates datasets/charts/dashboard through Superset MCP.
5. The dashboard is embedded in the workspace.
6. The user can publish, share, or continue adjusting it.

### 5. Deep Analysis Path

After a dashboard exists, the user can ask Hermes to run deeper analysis.

Hermes must identify:

- The dashboard's charts and saved queries
- The datasets behind each chart
- Applied filters and user permission filters
- Related dashboards selected by the user
- Uploaded Excel/CSV files and their schema
- Analysis skills/templates selected by the user

Hermes then generates an analysis plan for confirmation:

- Source dashboard data
- Related dashboard data
- Uploaded file mappings
- Assumptions
- Analysis method
- Output format

After confirmation, Hermes generates an analysis report, preferably HTML at first, with source references back to charts, datasets, and uploaded files.

## Product States

| State | Meaning | Primary User Action |
| --- | --- | --- |
| `question_received` | User asked a question | Wait for planning |
| `similar_found` | Existing dashboards match | Choose reuse or regenerate |
| `data_plan_ready` | Candidate data objects are available | Confirm or adjust |
| `generating_dashboard` | Hermes is creating Superset assets | Watch realtime logs |
| `dashboard_ready` | Dashboard exists and can be inspected | Publish, adjust, analyze |
| `adjusting_dashboard` | User requested changes | Confirm updated dashboard |
| `published` | Dashboard is reusable/shareable | Analyze or share |
| `analysis_planning` | Hermes is mapping data sources | Confirm analysis plan |
| `analysis_running` | Hermes is generating report | Watch realtime logs |
| `analysis_ready` | Report is ready | Inspect/export/share |

## Key Product Requirements

### Dashboard Reuse

- Detect similar dashboards before creating new assets.
- Show why a dashboard is considered similar.
- Never silently reuse a dashboard without user confirmation.
- Apply user permissions and requested filters when reusing.

### Semantic-Layer Confirmation

- Show available datasets, metrics, dimensions, relationships, and permission filters before generation.
- Allow natural-language correction of the data plan.
- Preserve the final data plan as dashboard metadata.

### Natural-Language Adjustment

- Users can ask for chart, filter, metric, layout, and time-range changes.
- Hermes should return a proposed change plan before destructive changes.
- Published shared dashboards should be forked or versioned for user-specific changes.

### Publishing and Sharing

- Draft dashboards are private to the creator/session.
- Published dashboards are shareable assets with metadata.
- Published dashboard metadata must include lineage, semantic-layer plan, and generated chart ids.

### Deep Analysis

- Analysis must be grounded in specific dashboard/chart data, not only screenshots.
- Uploaded files must be profiled and mapped to semantic entities before use.
- Reports should include source references and assumptions.
- The first report format is HTML rendered in the product frontend.

## Non-Goals For MVP

- Multi-tenant production authentication.
- Full enterprise governance workflow.
- Pixel-perfect dashboard designer.
- Production-grade Superset embedded guest-token auth.
- Automated Excel semantic matching beyond basic schema/profile extraction.

## MVP Acceptance Criteria

- User can ask a question and see realtime Hermes execution logs.
- Product can detect and present placeholder similar dashboard candidates.
- Product can show a data plan before generation.
- Hermes can create or reuse Superset assets through isolated Superset MCP.
- Superset dashboard can be embedded in the product workspace.
- User can publish a dashboard draft.
- User can run a first-pass HTML analysis report based on dashboard chart metadata.

## Open Questions

- What is the primary permission model: user, team, role, row-level policy, or all of these?
- Where should canonical dashboard metadata live: product DB, Superset metadata DB, or both?
- Should similar-dashboard search use embeddings, SQL metadata matching, or a hybrid?
- What Excel upload size and formats are in scope for MVP?
- Should published dashboards always fork from reused dashboards, or can users modify owned dashboards in place?
