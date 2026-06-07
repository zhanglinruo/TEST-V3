import json
import queue
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.analysis_engine.service import run_analysis
from app.dashboard_builder.service import analyze_dashboard, generate_dashboard, list_dashboards, publish_dashboard
from app.data_models.schemas import (
    DashboardDraft,
    DashboardGenerateRequest,
    InsightReport,
    ProductStatusResponse,
    PublishResponse,
    QueryRequest,
    QueryResponse,
)
from app.integrations.hermes import hermes_status
from app.integrations.superset import get_superset_client
from app.semantic_layer.service import build_semantic_context
from app.sql_generator.service import generate_sql

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    semantic_context = build_semantic_context(request)
    sql = generate_sql(request.question, semantic_context)
    rows = run_analysis(sql)
    return QueryResponse(sql=sql, rows=rows)


@router.get("/status", response_model=ProductStatusResponse)
def status() -> ProductStatusResponse:
    return ProductStatusResponse(
        superset=get_superset_client().status(),
        hermes=hermes_status(),
    )


@router.post("/dashboards/generate", response_model=DashboardDraft)
def create_dashboard(request: DashboardGenerateRequest) -> DashboardDraft:
    return generate_dashboard(request.prompt, request.data_source)


@router.post("/dashboards/generate/stream")
def create_dashboard_stream(request: DashboardGenerateRequest) -> StreamingResponse:
    events: queue.Queue[tuple[str, dict]] = queue.Queue()

    def emit(message: str) -> None:
        events.put(("log", {"message": message}))

    def worker() -> None:
        try:
            dashboard = generate_dashboard(request.prompt, request.data_source, emit=emit)
            events.put(("dashboard", dashboard.model_dump()))
        except Exception as exc:
            events.put(("error", {"message": str(exc)}))
        finally:
            events.put(("done", {}))

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            event_name, payload = events.get()
            yield f"event: {event_name}\n"
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            if event_name == "done":
                break

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/dashboards", response_model=list[DashboardDraft])
def dashboards() -> list[DashboardDraft]:
    return list_dashboards()


@router.post("/dashboards/{dashboard_id}/publish", response_model=PublishResponse)
def publish(dashboard_id: str) -> PublishResponse:
    try:
        dashboard = publish_dashboard(dashboard_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dashboard not found") from exc
    share_url = f"/shared/{dashboard.id}"
    if dashboard.superset_dashboard_id is not None:
        share_url = get_superset_client().dashboard_url(dashboard.superset_dashboard_id)
    return PublishResponse(dashboard=dashboard, share_url=share_url)


@router.post("/dashboards/{dashboard_id}/analyze", response_model=InsightReport)
def analyze(dashboard_id: str, competitor_context: str | None = None) -> InsightReport:
    try:
        return analyze_dashboard(dashboard_id, competitor_context)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dashboard not found") from exc
