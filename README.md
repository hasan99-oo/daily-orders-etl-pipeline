# Daily Orders ETL Pipeline

A batch ETL pipeline that ingests a daily orders CSV drop, cleans and
validates it, and loads it into a small star-schema warehouse
(`fact_orders` + `dim_customer` + `dim_product`), with a full audit
trail of what was rejected and why.

Runs against SQLite out of the box for zero-setup local development;
swap in Postgres/MySQL/Snowflake in production by changing one
environment variable.

## Project layout

```
etl_project/
├── config.py              # paths, DB connection, validation rules
├── pipeline.py             # orchestrator / CLI entry point
├── run.sh                  # sets up venv, runs pipeline + tests
├── requirements.txt
├── etl/
│   ├── extract.py          # reads the raw CSV
│   ├── transform.py        # cleans, validates, dedupes, enriches
│   └── load.py              # upserts into the warehouse, writes audit log
├── sql/
│   ├── schema.sql           # target table DDL
│   └── sample_queries.sql   # example analyst queries
├── data/
│   └── raw_orders_2026-08-03.csv   # sample input (506 rows, some dirty)
├── tests/
│   └── test_transform.py    # unit tests for the transform stage
├── logs/                    # pipeline.log written here at runtime
└── output/                  # warehouse.db (SQLite) written here at runtime
```

## Quick start

```bash
cd etl_project
./run.sh
```

That creates a virtualenv, installs dependencies, runs the pipeline
against the sample data, and runs the test suite. Or do it manually:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py --source data/raw_orders_2026-08-03.csv
pytest tests/
```

Then inspect the result:

```bash
sqlite3 output/warehouse.db < sql/sample_queries.sql
```

## What the pipeline does

1. **Extract** (`etl/extract.py`) — reads the raw CSV as strings and
   fails fast if expected columns are missing. No row-level judgment
   calls here on purpose.
2. **Transform** (`etl/transform.py`) — for every row:
   - Drops exact duplicates
   - Requires a non-empty `customer_id`
   - Requires quantity to parse as an integer ≥ 1
   - Parses `order_timestamp` against a list of accepted formats
   - Computes `total_amount = quantity * unit_price`
   - Anything that fails a check is routed to a **rejects** set with a
     specific reason — never silently dropped.
3. **Load** (`etl/load.py`) — inside a single DB transaction:
   - Upserts `dim_customer` / `dim_product`
   - Upserts `fact_orders`, keyed on `order_id` so re-running the same
     source file is idempotent (safe to retry)
   - Writes every rejected row to `rejected_rows` with its reason
   - Writes one row to `etl_audit_log` per run, including failures

## Data quality handling

The sample source file has deliberately injected issues so the
pipeline actually exercises its validation logic:
- ~2% missing `customer_id`
- ~2% invalid (negative) `quantity`
- ~4.5% missing or inconsistently formatted `order_timestamp`
- a handful of exact duplicate rows

Check `sql/sample_queries.sql` (query 5) to see rejection reasons for
the most recent run.

## Scheduling this in production

`pipeline.py` is a plain CLI script, so it drops into:
- **cron**: `0 6 * * * /path/to/.venv/bin/python /path/to/pipeline.py --source /path/to/todays_file.csv`
- **Airflow**: wrap `run()` from `pipeline.py` in a `PythonOperator`, or
  shell out to the script via `BashOperator`
- **Task Scheduler / systemd timer**: point at `run.sh` or the venv's
  python directly

## Extending this project

- Point `DATABASE_URL` in `config.py` (or the env var of the same
  name) at Postgres/Snowflake/etc. — the SQL is written to be portable,
  though the `ON CONFLICT` upsert syntax is SQLite/Postgres style and
  would need adjusting for MySQL.
- Add a new source: write a new `extract_*` function, keep `transform`
  and `load` as-is if the target schema matches.
- Add data quality metrics/alerting by querying `etl_audit_log` after
  each run and pushing to your monitoring stack.
