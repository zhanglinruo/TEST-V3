import React, { useEffect, useMemo, useState } from "react";

import { analyzeDashboard, generateDashboardStream, getStatus, publishDashboard } from "./api.js";

function StatusPill({ service }) {
  const label = service?.reachable ? "online" : service?.configured ? "configured" : "missing";
  return (
    <div className={`status-pill ${label}`}>
      <span>{service?.name}</span>
      <strong>{label}</strong>
    </div>
  );
}

function ChartPreview({ chart }) {
  const rows = chart.rows || [];
  const max = Math.max(...rows.map((row) => Number(row.value || 0)), 1);

  if (chart.chart_type === "kpi") {
    return (
      <section className="panel chart-panel">
        <div className="chart-head">
          <h3>{chart.title}</h3>
          <span>{chart.metric}</span>
        </div>
        <div className="kpi-value">{Number(rows[0]?.value || 0).toLocaleString()}</div>
      </section>
    );
  }

  return (
    <section className="panel chart-panel">
      <div className="chart-head">
        <h3>{chart.title}</h3>
        <span>{chart.metric}</span>
      </div>
      <div className={`bars ${chart.chart_type}`}>
        {rows.map((row) => {
          const label = row.month || row.region || row.name;
          const value = Number(row.value || 0);
          return (
            <div className="bar-row" key={label}>
              <span>{label}</span>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${Math.max((value / max) * 100, 4)}%` }} />
              </div>
              <strong>{value.toLocaleString()}</strong>
            </div>
          );
        })}
      </div>
      <details>
        <summary>Query metadata</summary>
        <pre>{chart.query}</pre>
      </details>
    </section>
  );
}

function ExecutionTimeline({ events = [], loading }) {
  const visibleEvents = loading && events.length === 0 ? ["Sending request to Hermes dashboard agent..."] : events;
  if (!visibleEvents.length) return null;

  return (
    <section className="execution-panel">
      <div className="execution-head">
        <span>Agent run</span>
        <strong>{loading ? "Running" : "Complete"}</strong>
      </div>
      <ol>
        {visibleEvents.map((event, index) => (
          <li key={`${event}-${index}`}>
            <span>{index + 1}</span>
            <p>{event}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

export default function App() {
  const [prompt, setPrompt] = useState("生成一个销售经营看板，包含收入趋势、区域贡献、客单价，并支持筛选和下钻分析");
  const [dashboard, setDashboard] = useState(null);
  const [status, setStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [runEvents, setRunEvents] = useState([]);
  const [competitorContext, setCompetitorContext] = useState("");
  const supersetUrl = dashboard?.superset_dashboard_id
    ? `http://localhost:8088/superset/dashboard/${dashboard.superset_dashboard_id}/`
    : "";

  useEffect(() => {
    getStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  const sourceCharts = useMemo(() => dashboard?.charts?.map((chart) => chart.id).join(", ") || "", [dashboard]);
  const timelineEvents = dashboard?.execution_events?.length ? dashboard.execution_events : runEvents;

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setRunEvents(["Sending request to backend.", "Starting Hermes dashboard agent."]);
    try {
      const data = await generateDashboardStream(prompt, (event, payload) => {
        if (event === "log" && payload.message) {
          setRunEvents((events) => [...events, payload.message]);
        }
        if (event === "dashboard") {
          setRunEvents(payload.execution_events || []);
        }
      });
      setDashboard(data);
      setRunEvents(data.execution_events || []);
      setReport(null);
    } catch (error) {
      setRunEvents((events) => [...events, error.message || "Dashboard generation failed."]);
      throw error;
    } finally {
      setLoading(false);
    }
  }

  async function onPublish() {
    if (!dashboard) return;
    const data = await publishDashboard(dashboard.id);
    setDashboard(data.dashboard);
  }

  async function onAnalyze() {
    if (!dashboard) return;
    const data = await analyzeDashboard(dashboard.id, competitorContext);
    setReport(data);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">AI + BI workspace</p>
          <h1>Hermes BI Studio</h1>
        </div>
        <form onSubmit={onSubmit} className="prompt-form">
          <label>
            Business question
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={7} />
          </label>
          <button type="submit" disabled={loading || !prompt.trim()}>
            {loading ? "Generating" : "Generate dashboard"}
          </button>
        </form>
        <div className="connector-list">
          {status && <StatusPill service={status.hermes} />}
          {status && <StatusPill service={status.superset} />}
        </div>
      </aside>

      <main className="workspace">
        <header className="workspace-head">
          <div>
            <p className="eyebrow">Generated asset</p>
            <h2>{dashboard?.title || "No dashboard yet"}</h2>
          </div>
          <div className="actions">
            <button type="button" onClick={onPublish} disabled={!dashboard || dashboard.status === "published"}>
              Publish
            </button>
            <button type="button" className="secondary" onClick={onAnalyze} disabled={!dashboard}>
              Deep analysis
            </button>
          </div>
        </header>

        {dashboard ? (
          <>
            <section className="meta-strip">
              <div><span>Status</span><strong>{dashboard.status}</strong></div>
              <div><span>Charts</span><strong>{dashboard.charts.length}</strong></div>
              <div><span>Metrics</span><strong>{dashboard.metrics.length}</strong></div>
              <div><span>Trace</span><strong>{sourceCharts}</strong></div>
            </section>
            {supersetUrl && (
              <section className="superset-embed">
                <div className="superset-embed-head">
                  <span>Superset dashboard #{dashboard.superset_dashboard_id}</span>
                  <a href={supersetUrl} target="_blank" rel="noreferrer">Open in Superset</a>
                </div>
                <iframe title={`Superset dashboard ${dashboard.superset_dashboard_id}`} src={supersetUrl} loading="lazy" />
              </section>
            )}
            {dashboard.integration_notes?.map((note) => (
              <section className="notice" key={note}>{note}</section>
            ))}
            <ExecutionTimeline events={timelineEvents} loading={loading} />
            <div className="chart-grid">
              {dashboard.charts.map((chart) => <ChartPreview chart={chart} key={chart.id} />)}
            </div>
          </>
        ) : (
          <>
            <ExecutionTimeline events={timelineEvents} loading={loading} />
            <section className="empty-state">
              <h2>Ask for a dashboard to start the BI loop.</h2>
              <p>The backend will create chart specs, query metadata, filters, publish state, and analysis-ready rows.</p>
            </section>
          </>
        )}
      </main>

      <aside className="insight-pane">
        <h2>AI analysis</h2>
        <label>
          Competitor data notes
          <textarea
            value={competitorContext}
            onChange={(e) => setCompetitorContext(e.target.value)}
            rows={5}
            placeholder="Paste competitor CSV summary or mapping notes"
          />
        </label>
        {report ? (
          <div className="report" dangerouslySetInnerHTML={{ __html: report.html }} />
        ) : (
          <p className="muted">Publish or inspect a dashboard, then run deep analysis from the saved chart metadata.</p>
        )}
      </aside>
    </div>
  );
}
