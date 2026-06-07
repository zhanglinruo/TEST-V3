from typing import Any

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    user_id: str | None = None


class QueryResponse(BaseModel):
    sql: str
    rows: list[dict[str, Any]]


class ConnectionStatus(BaseModel):
    name: str
    configured: bool
    reachable: bool
    detail: str


class ProductStatusResponse(BaseModel):
    superset: ConnectionStatus
    hermes: ConnectionStatus


class DashboardGenerateRequest(BaseModel):
    prompt: str
    data_source: str | None = None
    user_id: str | None = None


class ChartSpec(BaseModel):
    id: str
    title: str
    chart_type: str
    metric: str
    dimension: str | None = None
    filters: dict[str, Any] = {}
    query: str
    rows: list[dict[str, Any]]
    superset_chart_id: int | None = None


class DashboardDraft(BaseModel):
    id: str
    title: str
    prompt: str
    status: str
    charts: list[ChartSpec]
    metrics: list[dict[str, Any]]
    filters: list[dict[str, Any]]
    superset_dashboard_id: int | None = None
    integration_notes: list[str] = []
    execution_events: list[str] = []


class PublishResponse(BaseModel):
    dashboard: DashboardDraft
    share_url: str


class InsightReport(BaseModel):
    dashboard_id: str
    title: str
    html: str
    source_chart_ids: list[str]
    notes: list[str]
