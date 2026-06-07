import json
import http.cookiejar
import os
import re
import subprocess
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings
from app.data_models.schemas import ConnectionStatus


class SupersetClient:
    def __init__(self) -> None:
        self.base_url = settings.superset_base_url.rstrip("/")
        self._token: str | None = None
        self._csrf_token: str | None = None
        self._cookie_jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._cookie_jar))

    def status(self) -> ConnectionStatus:
        try:
            with urllib.request.urlopen(f"{self.base_url}/health", timeout=2) as response:
                reachable = 200 <= response.status < 500
                detail = f"HTTP {response.status} at {self.base_url}"
        except Exception as exc:
            reachable = False
            detail = f"Not reachable at {self.base_url}: {exc}"
        return ConnectionStatus(
            name="Apache Superset",
            configured=bool(self.base_url),
            reachable=reachable,
            detail=detail,
        )

    def _json_request(
        self,
        path: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json", "Referer": self.base_url}
        if authenticated:
            if not self._token:
                self._login()
            headers["Authorization"] = f"Bearer {self._token}"
            if method in {"POST", "PUT", "PATCH", "DELETE"}:
                if not self._csrf_token:
                    self._fetch_csrf_token()
                headers["X-CSRFToken"] = self._csrf_token
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with self._opener.open(request, timeout=8) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Superset API {method} {path} failed: HTTP {exc.code} {body}") from exc

    def _ensure_auth(self) -> None:
        if self._token and self._csrf_token:
            return
        if not self._token:
            self._login()
        if not self._csrf_token:
            self._fetch_csrf_token()

    def _login(self) -> None:
        login = self._json_request(
            "/api/v1/security/login",
            method="POST",
            payload={
                "username": settings.superset_username,
                "password": settings.superset_password,
                "provider": settings.superset_provider,
                "refresh": True,
            },
            authenticated=False,
        )
        self._token = login["access_token"]

    def _fetch_csrf_token(self) -> None:
        request = urllib.request.Request(
            f"{self.base_url}/api/v1/security/csrf_token/",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
                "Referer": self.base_url,
            },
            method="GET",
        )
        with self._opener.open(request, timeout=8) as response:
            csrf = json.loads(response.read().decode("utf-8"))
        self._csrf_token = csrf["result"]

    def create_dashboard_shell(self, title: str) -> int:
        result = self._json_request(
            "/api/v1/dashboard/",
            method="POST",
            payload={"dashboard_title": title, "published": False, "json_metadata": "{}"},
        )
        return int(result["id"])

    def publish_dashboard(self, dashboard_id: int) -> None:
        self._json_request(f"/api/v1/dashboard/{dashboard_id}", method="PUT", payload={"published": True})

    def dashboard_url(self, dashboard_id: int) -> str:
        return f"{self.base_url}/superset/dashboard/{dashboard_id}/"

    def attach_demo_charts(self, dashboard_id: int) -> tuple[list[int], str | None]:
        env = os.environ.copy()
        env["SUPERSET_CONFIG_PATH"] = settings.superset_config_path
        if settings.superset_vendor_pythonpath:
            env["PYTHONPATH"] = settings.superset_vendor_pythonpath
        command = [settings.superset_python, settings.superset_demo_chart_script, str(dashboard_id)]
        try:
            completed = subprocess.run(
                command,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception as exc:
            manual = (
                f"$env:SUPERSET_CONFIG_PATH='{settings.superset_config_path}'; "
                f"$env:PYTHONPATH='{settings.superset_vendor_pythonpath}'; "
                f"& '{settings.superset_python}' '{settings.superset_demo_chart_script}' {dashboard_id}"
            )
            return [], f"Could not attach Superset charts automatically: {exc}. Run manually: {manual}"

        match = re.search(r"chart_ids=([0-9,]+)", completed.stdout)
        if not match:
            return [], f"Superset chart script ran but did not return chart ids: {completed.stdout.strip()}"
        return [int(value) for value in match.group(1).split(",") if value], None


def get_superset_client() -> SupersetClient:
    return SupersetClient()
