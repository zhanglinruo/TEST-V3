import json
import os
import re
import subprocess
import ast
from pathlib import Path
from typing import Any, Callable

from app.core.config import settings
from app.data_models.schemas import ConnectionStatus, DashboardDraft


class HermesAgentError(RuntimeError):
    def __init__(self, message: str, events: list[str]):
        super().__init__(message)
        self.events = events


def hermes_status() -> ConnectionStatus:
    root = Path(settings.hermes_agent_root)
    configured = root.exists()
    command_ready = bool(settings.hermes_command.strip())
    detail = "Hermes source found"
    if command_ready:
        detail = "Hermes command configured"
    elif not configured:
        detail = f"Hermes root not found: {root}"
    return ConnectionStatus(
        name="Hermes Agent",
        configured=configured or command_ready,
        reachable=configured or command_ready,
        detail=detail,
    )


def plan_dashboard(prompt: str) -> dict:
    """First adapter seam for Hermes.

    The current Hermes install is primarily CLI/TUI based. This deterministic
    planner gives the product a stable contract now, and can later be replaced
    by a Hermes service/MCP call without changing the frontend.
    """
    lower = prompt.lower()
    focus = "revenue"
    if any(word in lower for word in ["cost", "expense", "成本"]):
        focus = "cost"
    elif any(word in lower for word in ["user", "客户", "用户"]):
        focus = "users"
    elif any(word in lower for word in ["order", "订单"]):
        focus = "orders"

    return {
        "title": prompt.strip()[:48] or "AI Generated BI Dashboard",
        "focus": focus,
        "metrics": [
            {"name": "Total Revenue", "expression": "sum(revenue)", "format": "$#,##0"},
            {"name": "Orders", "expression": "count(order_id)", "format": "#,##0"},
            {"name": "Average Order Value", "expression": "sum(revenue) / count(order_id)", "format": "$#,##0.00"},
        ],
        "filters": [
            {"field": "date", "type": "time_range", "default": "Last 90 days"},
            {"field": "region", "type": "select", "default": "All"},
        ],
    }


def _loads_loose_object(candidate: str) -> dict[str, Any] | None:
    repaired = re.sub(r"(?m)([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', candidate)
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        for parser_input in (repaired, candidate):
            try:
                value = ast.literal_eval(parser_input)
                break
            except (SyntaxError, ValueError):
                try:
                    value = json.loads(parser_input)
                    break
                except json.JSONDecodeError:
                    value = None
        if value is None:
            return None
    if isinstance(value, dict):
        return value
    return None


def _iter_json_like_objects(text: str) -> list[str]:
    objects: list[str] = []
    stack = 0
    start: int | None = None
    in_string: str | None = None
    escaped = False

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char in {'"', "'"}:
            in_string = char
            continue
        if char == "{":
            if stack == 0:
                start = index
            stack += 1
        elif char == "}" and stack:
            stack -= 1
            if stack == 0 and start is not None:
                objects.append(text[start : index + 1])
                start = None
    return objects


def _is_dashboard_result(value: dict[str, Any]) -> bool:
    return ("dashboard_id" in value and "chart_ids" in value) or (
        "error" in value and "dashboard_id" in value
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    fenced_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    for candidate in reversed(fenced_blocks):
        value = _loads_loose_object(candidate)
        if value and _is_dashboard_result(value):
            return value

    for candidate in reversed(_iter_json_like_objects(text)):
        value = _loads_loose_object(candidate)
        if value and _is_dashboard_result(value):
            return value

    raise ValueError(f"Hermes did not return a dashboard JSON object: {text[-1000:]}")


def _build_execution_events(output: str) -> list[str]:
    events = ["Started Hermes dashboard agent with isolated Superset MCP runtime."]
    patterns = [
        ("Loaded environment variables", "Loaded Hermes environment variables."),
        ("MCP server 'superset'", "Connected to Superset MCP server."),
        ("registered 141 tool", "Registered Superset MCP tools."),
        ("registered 137 tool", "Registered Superset MCP tools."),
        ("Failed to connect to MCP server", "An MCP server failed to connect."),
        ("dashboard", "Hermes worked on dashboard creation."),
        ("chart", "Hermes worked on chart creation."),
        ("dataset", "Hermes inspected or updated datasets."),
    ]
    for needle, message in patterns:
        if needle.lower() in output.lower() and message not in events:
            events.append(message)

    tail_lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in tail_lines[-6:]:
        clean = re.sub(r"bce-v3/[A-Za-z0-9/_-]+", "[REDACTED]", line)
        if len(clean) > 180:
            clean = clean[:177] + "..."
        if clean and clean not in events:
            events.append(clean)
    return events[:12]


def _load_env_file(path: str) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _sanitize_log_line(line: str) -> str:
    clean = re.sub(r"bce-v3/[A-Za-z0-9/_-]+", "[REDACTED]", line.strip())
    return clean[:500]


def run_dashboard_agent(prompt: str, emit: Callable[[str], None] | None = None) -> dict[str, Any]:
    agent_prompt = f"""
You are building a Superset BI dashboard for an AI+BI product.

Use only the configured Superset MCP tools. Do not use terminal, npm, npx, PowerBI, browser, or unrelated tools.

Goal:
1. Inspect Superset for database connections and datasets.
2. Prefer the existing demo_sales dataset if it exists.
3. Create useful charts for the user request.
4. Create and publish one dashboard.
5. Your final answer must be ONLY one JSON object. Do not include markdown, explanation, session_id, or text before/after it.

User request:
{prompt}

JSON schema:
{{
  "dashboard_id": 123,
  "dashboard_url": "http://localhost:8088/superset/dashboard/123/",
  "dataset_ids": [1],
  "chart_ids": [1, 2, 3],
  "summary": "short summary"
}}
""".strip()
    inherited_keys = [
        "PATH",
        "Path",
        "PATHEXT",
        "SYSTEMROOT",
        "SystemRoot",
        "WINDIR",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "LOCALAPPDATA",
        "APPDATA",
        "COMSPEC",
    ]
    env = {key: value for key, value in os.environ.items() if key in inherited_keys}
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(_load_env_file(settings.hermes_env_path))
    env["SUPERSET_BASE_URL"] = "http://127.0.0.1:8088"
    env["SUPERSET_USERNAME"] = settings.superset_username
    env["SUPERSET_PASSWORD"] = settings.superset_password
    env["SUPERSET_AUTH_PROVIDER"] = settings.superset_provider
    if settings.hermes_home:
        env["HERMES_HOME"] = settings.hermes_home
    command = [
        settings.hermes_python,
        "-m",
        "hermes_cli.main",
        "chat",
        "--query",
        agent_prompt,
        "--toolsets",
        "superset",
        "--quiet",
        "--max-turns",
        "40",
        "--source",
        "tool",
    ]
    if emit:
        emit("Launching Hermes CLI with isolated Superset MCP runtime.")
    process = subprocess.Popen(
        command,
        cwd=settings.hermes_agent_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    lines: list[str] = []
    try:
        assert process.stdout is not None
        for line in process.stdout:
            lines.append(line)
            clean = _sanitize_log_line(line)
            if emit and clean:
                emit(clean)
        return_code = process.wait(timeout=settings.hermes_timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        output = "".join(lines)
        events = _build_execution_events(output)
        if emit:
            emit("Hermes dashboard agent timed out.")
        raise HermesAgentError("Hermes dashboard agent timed out.", events) from exc

    output = "".join(lines)
    events = _build_execution_events(output)
    if return_code != 0:
        raise HermesAgentError(output.strip(), events)
    try:
        result = _extract_json_object(output)
    except Exception as exc:
        raise HermesAgentError(str(exc), events) from exc
    if result.get("error") or result.get("dashboard_id") is None:
        message = result.get("summary") or result.get("details") or result.get("error") or "Hermes did not create a dashboard."
        raise HermesAgentError(str(message), events)
    result["_execution_events"] = events
    return result
