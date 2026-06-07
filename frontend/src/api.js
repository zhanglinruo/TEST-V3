const API_BASE = "http://localhost:8000/api";

export async function runQuery(question) {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  });
  if (!response.ok) {
    throw new Error("Request failed");
  }
  return response.json();
}

export async function getStatus() {
  const response = await fetch(`${API_BASE}/status`);
  if (!response.ok) {
    throw new Error("Status request failed");
  }
  return response.json();
}

export async function generateDashboard(prompt) {
  const response = await fetch(`${API_BASE}/dashboards/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt })
  });
  if (!response.ok) {
    throw new Error("Dashboard generation failed");
  }
  return response.json();
}

export async function generateDashboardStream(prompt, onEvent) {
  const response = await fetch(`${API_BASE}/dashboards/generate/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt })
  });
  if (!response.ok || !response.body) {
    throw new Error("Dashboard generation stream failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalDashboard = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      const eventLine = lines.find((line) => line.startsWith("event:"));
      const dataLine = lines.find((line) => line.startsWith("data:"));
      if (!eventLine || !dataLine) continue;

      const event = eventLine.replace("event:", "").trim();
      const data = JSON.parse(dataLine.replace("data:", "").trim() || "{}");
      onEvent?.(event, data);
      if (event === "dashboard") {
        finalDashboard = data;
      }
      if (event === "error") {
        throw new Error(data.message || "Dashboard generation failed");
      }
    }
  }

  if (!finalDashboard) {
    throw new Error("Dashboard generation stream ended without a dashboard");
  }
  return finalDashboard;
}

export async function publishDashboard(id) {
  const response = await fetch(`${API_BASE}/dashboards/${id}/publish`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error("Publish failed");
  }
  return response.json();
}

export async function analyzeDashboard(id, competitorContext = "") {
  const params = competitorContext ? `?competitor_context=${encodeURIComponent(competitorContext)}` : "";
  const response = await fetch(`${API_BASE}/dashboards/${id}/analyze${params}`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error("Analysis failed");
  }
  return response.json();
}
