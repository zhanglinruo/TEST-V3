from superset.app import create_app


def main() -> None:
    app = create_app()
    with app.app_context():
        from superset import db
        from superset.connectors.sqla.models import SqlaTable, SqlMetric, TableColumn
        from superset.models.core import Database

        uri = "sqlite:///D:/superset/ai_bi_demo.db"
        database = db.session.query(Database).filter_by(database_name="AI BI Demo SQLite").one_or_none()
        if database is None:
            database = Database(
                database_name="AI BI Demo SQLite",
                sqlalchemy_uri=uri,
                expose_in_sqllab=True,
                allow_ctas=False,
                allow_cvas=False,
                allow_dml=False,
            )
            db.session.add(database)
            db.session.flush()
        else:
            database.sqlalchemy_uri = uri
            database.expose_in_sqllab = True

        dataset = (
            db.session.query(SqlaTable)
            .filter_by(table_name="demo_sales", database_id=database.id)
            .one_or_none()
        )
        if dataset is None:
            dataset = SqlaTable(
                table_name="demo_sales",
                database=database,
                main_dttm_col="order_date",
                schema=None,
                is_sqllab_view=False,
            )
            db.session.add(dataset)
            db.session.flush()

        columns = [
            ("order_id", "INTEGER", False, False, False),
            ("order_date", "TEXT", True, True, True),
            ("month", "TEXT", True, True, False),
            ("region", "TEXT", True, True, False),
            ("channel", "TEXT", True, True, False),
            ("product_category", "TEXT", True, True, False),
            ("revenue", "REAL", False, False, False),
            ("cost", "REAL", False, False, False),
        ]
        existing_cols = {column.column_name: column for column in dataset.columns}
        for name, column_type, groupby, filterable, is_dttm in columns:
            column = existing_cols.get(name)
            if column is None:
                column = TableColumn(
                    column_name=name,
                    type=column_type,
                    groupby=groupby,
                    filterable=filterable,
                    is_dttm=is_dttm,
                    table=dataset,
                )
                db.session.add(column)
            else:
                column.type = column_type
                column.groupby = groupby
                column.filterable = filterable
                column.is_dttm = is_dttm

        metrics = [
            ("count", "COUNT(*)", "#,##0"),
            ("total_revenue", "SUM(revenue)", "$,.2f"),
            ("avg_order_value", "SUM(revenue) / COUNT(*)", "$,.2f"),
        ]
        existing_metrics = {metric.metric_name: metric for metric in dataset.metrics}
        for name, expression, d3format in metrics:
            metric = existing_metrics.get(name)
            if metric is None:
                metric = SqlMetric(metric_name=name, expression=expression, d3format=d3format, table=dataset)
                db.session.add(metric)
            else:
                metric.expression = expression
                metric.d3format = d3format

        db.session.commit()
        print(f"database_id={database.id}")
        print(f"dataset_id={dataset.id}")
        print(f"columns={len(dataset.columns)} metrics={len(dataset.metrics)}")


if __name__ == "__main__":
    main()
