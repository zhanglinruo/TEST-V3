import json
import sys

from superset.app import create_app


def metric(label: str, column: str = "revenue", aggregate: str = "SUM") -> dict:
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": column, "type": "REAL"},
        "aggregate": aggregate,
        "label": label,
    }


def chart_params(viz_type: str, groupby: list[str] | None = None) -> str:
    params = {
        "datasource": "1__table",
        "datasource_id": 1,
        "datasource_type": "table",
        "viz_type": viz_type,
        "time_range": "No filter",
        "adhoc_filters": [],
        "row_limit": 1000,
        "metrics": [metric("Total Revenue")],
        "groupby": groupby or [],
        "y_axis_format": "$,.2f",
        "x_axis_time_format": "%Y-%m",
        "show_value": True,
    }
    if viz_type == "echarts_timeseries_line":
        params.update({"granularity_sqla": "order_date", "time_grain_sqla": "P1M", "x_axis": "order_date"})
    if viz_type == "big_number_total":
        params.update({"metric": metric("Average Order Value"), "subheader": "Average order value"})
    return json.dumps(params)


def layout_for(chart_ids: list[int]) -> str:
    root_id = "ROOT_ID"
    grid_id = "GRID_ID"
    row_id = "ROW-AI-BI"
    layout = {
        root_id: {"type": "ROOT", "id": root_id, "children": [grid_id]},
        grid_id: {"type": "GRID", "id": grid_id, "parents": [root_id], "children": [row_id]},
        row_id: {
            "type": "ROW",
            "id": row_id,
            "parents": [root_id, grid_id],
            "children": [],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        },
    }
    for index, chart_id in enumerate(chart_ids):
        column_id = f"COLUMN-{chart_id}"
        node_id = f"CHART-{chart_id}"
        layout[row_id]["children"].append(column_id)
        layout[column_id] = {
            "type": "COLUMN",
            "id": column_id,
            "parents": [root_id, grid_id, row_id],
            "children": [node_id],
            "meta": {"width": 4, "background": "BACKGROUND_TRANSPARENT"},
        }
        layout[node_id] = {
            "type": "CHART",
            "id": node_id,
            "parents": [root_id, grid_id, row_id, column_id],
            "children": [],
            "meta": {"chartId": chart_id, "width": 4, "height": 50},
        }
    return json.dumps(layout)


def main() -> None:
    dashboard_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    app = create_app()
    with app.app_context():
        from superset import db
        from superset.connectors.sqla.models import SqlaTable
        from superset.models.dashboard import Dashboard
        from superset.models.slice import Slice

        dataset = db.session.query(SqlaTable).filter_by(id=1).one()
        dashboard = db.session.query(Dashboard).filter_by(id=dashboard_id).one()
        specs = [
            ("AI BI Revenue Trend", "echarts_timeseries_line", chart_params("echarts_timeseries_line")),
            ("AI BI Revenue by Region", "echarts_timeseries_bar", chart_params("echarts_timeseries_bar", ["region"])),
            ("AI BI Average Order Value", "big_number_total", chart_params("big_number_total")),
        ]
        charts = []
        for name, viz_type, params in specs:
            chart = db.session.query(Slice).filter_by(slice_name=name, datasource_id=dataset.id).one_or_none()
            if chart is None:
                chart = Slice(
                    slice_name=name,
                    datasource_id=dataset.id,
                    datasource_type="table",
                    datasource_name=dataset.table_name,
                    viz_type=viz_type,
                    params=params,
                )
                db.session.add(chart)
                db.session.flush()
            else:
                chart.viz_type = viz_type
                chart.params = params
            if chart not in dashboard.slices:
                dashboard.slices.append(chart)
            charts.append(chart)
        dashboard.position_json = layout_for([chart.id for chart in charts])
        dashboard.published = True
        db.session.commit()
        print(f"dashboard_id={dashboard.id}")
        print("chart_ids=" + ",".join(str(chart.id) for chart in charts))


if __name__ == "__main__":
    main()
