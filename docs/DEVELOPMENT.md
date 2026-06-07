# Development Setup

This document describes how to run the local AI+BI MVP stack.

## Local Services

| Service | URL | Purpose |
| --- | --- | --- |
| Frontend | `http://127.0.0.1:5173` / `http://localhost:5173` | Product workspace |
| Backend | `http://127.0.0.1:8000` | FastAPI API |
| Superset | `http://127.0.0.1:8088` / `http://localhost:8088` | BI engine |

## Environment Variables

Copy `.env.example` to `.env` when local overrides are needed.

Important groups:

- `SUPERSET_*`: Superset REST and MCP connection details.
- `HERMES_*`: Hermes source path, Python executable, isolated product runtime path.
- `OPENAI_*`: placeholder model variables. For the current local Hermes setup, model credentials are read from `HERMES_ENV_PATH`.
- `CLICKHOUSE_*`: placeholder for future query execution/semantic work.

## Hermes Runtime Isolation

The backend runs Hermes with:

```text
HERMES_HOME=E:\dev_apps\ai-bi-mvp\.hermes-runtime
```

This prevents product-driven Hermes runs from inheriting unrelated global MCP servers such as PowerBI. The runtime config should only include product-approved tools.

The committed `.hermes-runtime/config.yaml` uses environment placeholders for secrets:

```yaml
SUPERSET_PASSWORD: "${SUPERSET_PASSWORD}"
api_key: ${OPENAI_API_KEY}
```

Runtime logs, sessions, skills, and state under `.hermes-runtime/` are ignored by git.

## Superset Setup

Superset is expected at:

```text
D:\superset
```

Start Superset:

```powershell
$env:SUPERSET_CONFIG_PATH='D:\superset\superset_config.py'
$env:PYTHONPATH='E:\dev_apps\ai-bi-mvp\vendor_py'
& 'D:\superset\.venv\Scripts\superset.exe' run -h 127.0.0.1 -p 8088 --with-threads
```

Register demo database/dataset:

```powershell
$env:SUPERSET_CONFIG_PATH='D:\superset\superset_config.py'
& 'D:\superset\.venv\Scripts\python.exe' 'E:\dev_apps\ai-bi-mvp\tools\register_superset_demo.py'
```

Create demo charts/dashboard:

```powershell
$env:SUPERSET_CONFIG_PATH='D:\superset\superset_config.py'
& 'D:\superset\.venv\Scripts\python.exe' 'E:\dev_apps\ai-bi-mvp\tools\create_superset_demo_charts.py'
```

## Superset Local Embedding

Local iframe embedding requires Superset to allow the product frontend as a frame ancestor.

Development-only settings in `D:\superset\superset_config.py`:

```python
TALISMAN_CONFIG = {
    "force_https": False,
    "frame_options": None,
    "content_security_policy": {
        "frame-ancestors": [
            "'self'",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
    },
}
```

Production should use Superset embedded dashboards and guest tokens.

## Backend

Install and run:

```powershell
cd E:\dev_apps\ai-bi-mvp\backend
python -m pip install -e .
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Useful URLs:

- `http://127.0.0.1:8000/api/status`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/openapi.json`

## Frontend

Install and run:

```powershell
cd E:\dev_apps\ai-bi-mvp\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Build:

```powershell
npm run build
```

## Troubleshooting

### Frontend Refuses Connection

Check whether Vite is listening:

```powershell
netstat -ano | Select-String ':5173'
```

Restart:

```powershell
cd E:\dev_apps\ai-bi-mvp\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

### Backend Refuses Connection

Check:

```powershell
netstat -ano | Select-String ':8000'
```

Restart:

```powershell
cd E:\dev_apps\ai-bi-mvp\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Superset MCP Connects But API Calls Fail

Check Superset health:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8088/health'
```

Check REST login:

```powershell
@'
import requests
base='http://127.0.0.1:8088'
s=requests.Session()
r=s.post(base+'/api/v1/security/login', json={'username':'admin','password':'admin','provider':'db','refresh':True})
print(r.status_code, r.text[:200])
'@ | python -
```

### PowerBI MCP Appears In Logs

The product backend should use `.hermes-runtime/config.yaml`, not global `~/.hermes/config.yaml`. Check `HERMES_HOME` and backend config.
