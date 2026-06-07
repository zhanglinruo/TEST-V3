import clickhouse_connect

from app.core.config import settings


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        url=settings.clickhouse_url,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
    )

