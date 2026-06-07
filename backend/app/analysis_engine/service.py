from app.core.clickhouse import get_clickhouse_client


def run_analysis(sql: str) -> list[dict]:
    # Minimal ClickHouse execution wrapper for MVP.
    client = get_clickhouse_client()
    result = client.query(sql)
    return [dict(zip(result.column_names, row)) for row in result.result_rows]

