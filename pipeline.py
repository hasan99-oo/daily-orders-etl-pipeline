#!/usr/bin/env python3
"""
Daily orders ETL pipeline entry point.

Usage:
    python pipeline.py --source data/raw_orders_2026-08-03.csv

Designed to be run by cron / Airflow / Task Scheduler once a day. Every
run gets a unique batch_id and writes a row to etl_audit_log so runs
are traceable and idempotent (safe to re-run the same source file).
"""
import argparse
import logging
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine

import config
from etl.extract import extract_orders
from etl.transform import transform_orders
from etl.load import load_orders


def setup_logging():
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.LOG_DIR / "pipeline.log"
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


def ensure_schema(engine):
    ddl = config.SCHEMA_FILE.read_text()
    with engine.begin() as conn:
        for statement in ddl.split(";"):
            statement = statement.strip()
            if statement:
                conn.exec_driver_sql(statement)


def run(source_path: str):
    logger = logging.getLogger("etl.pipeline")
    batch_id = str(uuid.uuid4())
    logger.info("Starting batch %s for source %s", batch_id, source_path)

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(config.DATABASE_URL)
    ensure_schema(engine)

    raw_df = extract_orders(source_path)
    clean_df, rejects_df = transform_orders(raw_df)
    load_orders(
        engine=engine,
        clean_df=clean_df,
        rejects_df=rejects_df,
        batch_id=batch_id,
        source_file=source_path,
        rows_extracted=len(raw_df),
    )

    logger.info("Batch %s complete: extracted=%d rejected=%d loaded=%d",
                batch_id, len(raw_df), len(rejects_df), len(clean_df))
    return batch_id


def main():
    parser = argparse.ArgumentParser(description="Run the daily orders ETL pipeline")
    parser.add_argument(
        "--source", default=str(config.DATA_DIR / "raw_orders_2026-08-03.csv"),
        help="Path to the raw orders CSV to process",
    )
    args = parser.parse_args()

    setup_logging()
    try:
        batch_id = run(args.source)
    except Exception:
        logging.getLogger("etl.pipeline").exception("Pipeline run failed")
        sys.exit(1)
    print(f"Done. batch_id={batch_id}")


if __name__ == "__main__":
    main()
