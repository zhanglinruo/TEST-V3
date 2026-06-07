from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from app.core.config import settings
from app.data_models.schemas import ChartSpec, DashboardDraft, InsightReport
from app.integrations.hermes import HermesAgentError, plan_dashboard, run_dashboard_agent
from app.integrations.superset import get_superset_client

_DASHBOARDS: dict[str, DashboardDraft] = {}


def _sample_rows(metric: str) -> list[dict[str, float | str]]:
    values = [118000, 124500, 121200, 136800, 152300, 148900]
    if metric == "Orders":
        values = [820, 860, 845, 910, 980, 955]
    if metric == "Average Order Value":
        values = [143.9, 144.8, 143.4, 150.3, 155.4, 155.9]
    months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
    return [{"month": month, "value": value} for month, value in zip(months, values, strict=True)]


def generate_dashboard(
    prompt: str,
    data_source: str | None = None,
    emit: Callable[[str], None] | None = None,
) -> DashboardDraft:
    plan = plan_dashboard(prompt)
    dashboard_id = f"dash_{uuid4().hex[:10]}"
    source = data_source or "demo_sales"
    integration_notes: list[str] = []
    execution_events: list[str] = ["Received dashboard generation request."]
    if emit:
        emit("Received dashboard generation request.")
        emit("Prepared semantic dashboard plan.")
    hermes_result = None
    if settings.use_hermes_for_dashboards:
        try:
            if emit:
                emit("Starting Hermes dashboard agent.")
            hermes_result = run_dashboard_agent(prompt, emit=emit)
            execution_events.extend(hermes_result.get("_execution_events", []))
            execution_events.append("Hermes returned a dashboard result.")
            if emit:
                emit("Hermes returned a dashboard result.")
        except HermesAgentError as exc:
            execution_events.extend(exc.events)
            execution_events.append("Fell back to local chart preview because Hermes did not return a usable dashboard object.")
            integration_notes.append(f"Hermes dashboard agent failed, using local fallback: {exc}")
            if emit:
                emit("Falling back to local chart preview.")
        except Exception as exc:
            execution_events.append("Fell back to local chart preview after an unexpected Hermes error.")
            integration_notes.append(f"Hermes dashboard agent failed, using local fallback: {exc}")
            if emit:
                emit(f"Falling back after unexpected Hermes error: {exc}")

    superset_id = hermes_result.get("dashboard_id") if hermes_result else None
    charts = [
        ChartSpec(
            id=f"{dashboard_id}_trend",
            title="Revenue trend",
            chart_type="line",
            metric="Total Revenue",
            dimension="month",
            query=f"SELECT toStartOfMonth(date) AS month, sum(revenue) AS value FROM {source} GROUP BY month ORDER BY month",
            rows=_sample_rows("Total Revenue"),
        ),
        ChartSpec(
            id=f"{dashboard_id}_region",
            title="Revenue by region",
            chart_type="bar",
            metric="Total Revenue",
            dimension="region",
            query=f"SELECT region, sum(revenue) AS value FROM {source} GROUP BY region ORDER BY value DESC LIMIT 10",
            rows=[
                {"region": "East", "value": 186000},
                {"region": "South", "value": 164000},
                {"region": "North", "value": 151000},
                {"region": "West", "value": 128000},
            ],
        ),
        ChartSpec(
            id=f"{dashboard_id}_aov",
            title="Average order value",
            chart_type="kpi",
            metric="Average Order Value",
            query=f"SELECT sum(revenue) / count(order_id) AS value FROM {source}",
            rows=[{"value": 151.2}],
        ),
    ]
    if hermes_result:
        chart_ids = hermes_result.get("chart_ids") or []
        for chart, superset_chart_id in zip(charts, chart_ids, strict=False):
            chart.superset_chart_id = int(superset_chart_id)
    elif superset_id is not None:
        superset = get_superset_client()
        superset_chart_ids, integration_note = superset.attach_demo_charts(superset_id)
        for chart, superset_chart_id in zip(charts, superset_chart_ids, strict=False):
            chart.superset_chart_id = superset_chart_id
        if integration_note:
            integration_notes.append(integration_note)
    elif not settings.use_hermes_for_dashboards:
        superset = get_superset_client()
        try:
            superset_id = superset.create_dashboard_shell(plan["title"])
        except Exception as exc:
            integration_notes.append(
                "Superset dashboard could not be created automatically. "
                f"Check that Superset is running with write access to its metadata DB. Error: {exc}"
            )
    draft = DashboardDraft(
        id=dashboard_id,
        title=hermes_result.get("summary", plan["title"]) if hermes_result else plan["title"],
        prompt=prompt,
        status="draft",
        charts=charts,
        metrics=plan["metrics"],
        filters=plan["filters"],
        superset_dashboard_id=superset_id,
        integration_notes=integration_notes,
        execution_events=execution_events,
    )
    _DASHBOARDS[dashboard_id] = draft
    if emit:
        emit("Dashboard draft is ready.")
    return draft


def list_dashboards() -> list[DashboardDraft]:
    return list(_DASHBOARDS.values())


def publish_dashboard(dashboard_id: str) -> DashboardDraft:
    draft = _DASHBOARDS[dashboard_id]
    if draft.superset_dashboard_id is not None:
        get_superset_client().publish_dashboard(draft.superset_dashboard_id)
    published = draft.model_copy(update={"status": "published"})
    _DASHBOARDS[dashboard_id] = published
    return published


def analyze_dashboard(dashboard_id: str, competitor_context: str | None = None) -> InsightReport:
    dashboard = _DASHBOARDS[dashboard_id]
    trend = dashboard.charts[0].rows
    first = float(trend[0]["value"])
    last = float(trend[-1]["value"])
    growth = ((last - first) / first) * 100 if first else 0
    context_note = ""
    if competitor_context:
        context_note = "<p>The uploaded competitor context should be mapped against the dashboard metrics before direct comparison.</p>"
    html = f"""
    <article>
      <h1>{dashboard.title}</h1>
      <p>This report is generated from {len(dashboard.charts)} published chart specs, so every conclusion can be traced back to the dashboard metadata.</p>
      <h2>Executive read</h2>
      <p>Revenue moved from {first:,.0f} to {last:,.0f}, a {growth:.1f}% change across the visible period.</p>
      <h2>What to inspect next</h2>
      <p>Region mix is uneven. The next drill path should compare region, channel, and product category before making allocation decisions.</p>
      {context_note}
    </article>
    """
    return InsightReport(
        dashboard_id=dashboard_id,
        title=f"Deep analysis: {dashboard.title}",
        html=html,
        source_chart_ids=[chart.id for chart in dashboard.charts],
        notes=["Uses chart rows and queries saved in dashboard metadata.", "Competitor data mapping is not automated yet."],
    )
