from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    clickhouse_url: str = "http://localhost:8123"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    superset_base_url: str = "http://localhost:8088"
    superset_username: str = "admin"
    superset_password: str = "admin"
    superset_provider: str = "db"
    superset_python: str = "D:\\superset\\.venv\\Scripts\\python.exe"
    superset_config_path: str = "D:\\superset\\superset_config.py"
    superset_vendor_pythonpath: str = "E:\\dev_apps\\ai-bi-mvp\\vendor_py"
    superset_demo_chart_script: str = "E:\\dev_apps\\ai-bi-mvp\\tools\\create_superset_demo_charts.py"
    hermes_home: str = "E:\\dev_apps\\ai-bi-mvp\\.hermes-runtime"
    hermes_env_path: str = "C:\\Users\\Zhang Linruo\\.hermes\\.env"
    hermes_agent_root: str = "D:\\openclaw\\workspace\\hermes-agent\\hermes-agent-main"
    hermes_command: str = ""
    hermes_python: str = "D:\\openclaw\\workspace\\hermes-agent\\hermes-agent-main\\venv\\Scripts\\python.exe"
    hermes_timeout_seconds: int = 600
    use_hermes_for_dashboards: bool = True


settings = Settings()
