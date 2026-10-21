"""Load stage: upsert dimensions, insert facts, write rejects + audit log."""
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

logger = logging.getLogger("etl.load")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def load_orders(engine, clean_df: pd.DataFrame, rejects_df: pd.DataFrame,
                 batch_id: str, source_file: str, rows_extracted: int):
    """Load clean rows into the warehouse inside a single transaction.

    On any failure the whole batch rolls back and the audit log records
    the error -- partial loads should never happen.
    """
    started_at = _now_iso()

    with engine.begin() as conn:
        try:
            if not clean_df.empty:
                # Dimension: customers (first_seen/last_seen upsert-by-merge)
                customers = clean_df.groupby("customer_id")["order_date"].agg(["min", "max"]).reset_index()
                for _, r in customers.iterrows():
                    conn.execute(text("""
                        INSERT INTO dim_customer (customer_id, first_seen_date, last_seen_date)
                        VALUES (:cid, :first, :last)
                        ON CONFLICT(customer_id) DO UPDATE SET
                            first_seen_date = MIN(first_seen_date, excluded.first_seen_date),
                            last_seen_date  = MAX(last_seen_date, excluded.last_seen_date)
                    """), {"cid": r["customer_id"], "first": r["min"], "last": r["max"]})

                # Dimension: products
                products = clean_df[["product_id", "product_name", "unit_price"]].drop_duplicates("product_id")
                for _, r in products.iterrows():
                    conn.execute(text("""
                        INSERT INTO dim_product (product_id, product_name, unit_price)
                        VALUES (:pid, :name, :price)
                        ON CONFLICT(product_id) DO UPDATE SET
                            product_name = excluded.product_name,
                            unit_price   = excluded.unit_price
                    """), {"pid": r["product_id"], "name": r["product_name"], "price": r["unit_price"]})

                # Fact table -- idempotent on order_id so re-running a batch
                # is safe (upsert instead of plain insert).
                loaded_at = _now_iso()
                for _, r in clean_df.iterrows():
                    conn.execute(text("""
                        INSERT INTO fact_orders (
                            order_id, customer_id, product_id, quantity, unit_price,
                            total_amount, currency, order_timestamp, order_date,
                            load_batch_id, loaded_at
                        ) VALUES (
                            :order_id, :customer_id, :product_id, :quantity, :unit_price,
                            :total_amount, :currency, :order_timestamp, :order_date,
                            :batch_id, :loaded_at
                        )
                        ON CONFLICT(order_id) DO UPDATE SET
                            customer_id = excluded.customer_id,
                            product_id = excluded.product_id,
                            quantity = excluded.quantity,
                            unit_price = excluded.unit_price,
                            total_amount = excluded.total_amount,
                            currency = excluded.currency,
                            order_timestamp = excluded.order_timestamp,
                            order_date = excluded.order_date,
                            load_batch_id = excluded.load_batch_id,
                            loaded_at = excluded.loaded_at
                    """), {**r.to_dict(), "batch_id": batch_id, "loaded_at": loaded_at})

            if not rejects_df.empty:
                for _, r in rejects_df.iterrows():
                    conn.execute(text("""
                        INSERT INTO rejected_rows (batch_id, raw_order_id, reason, raw_row_json)
                        VALUES (:batch_id, :raw_order_id, :reason, :raw_row_json)
                    """), {"batch_id": batch_id, **r.to_dict()})

            conn.execute(text("""
                INSERT INTO etl_audit_log (
                    batch_id, source_file, started_at, finished_at,
                    rows_extracted, rows_rejected, rows_loaded, status, error_message
                ) VALUES (
                    :batch_id, :source_file, :started_at, :finished_at,
                    :rows_extracted, :rows_rejected, :rows_loaded, :status, NULL
                )
            """), {
                "batch_id": batch_id, "source_file": str(source_file),
                "started_at": started_at, "finished_at": _now_iso(),
                "rows_extracted": rows_extracted, "rows_rejected": len(rejects_df),
                "rows_loaded": len(clean_df), "status": "SUCCESS",
            })

        except Exception as exc:
            logger.exception("Load failed for batch %s", batch_id)
            conn.execute(text("""
                INSERT INTO etl_audit_log (
                    batch_id, source_file, started_at, finished_at,
                    rows_extracted, rows_rejected, rows_loaded, status, error_message
                ) VALUES (
                    :batch_id, :source_file, :started_at, :finished_at,
                    :rows_extracted, :rows_rejected, :rows_loaded, :status, :error
                )
            """), {
                "batch_id": batch_id, "source_file": str(source_file),
                "started_at": started_at, "finished_at": _now_iso(),
                "rows_extracted": rows_extracted, "rows_rejected": len(rejects_df),
                "rows_loaded": 0, "status": "FAILED", "error": str(exc),
            })
            raise

    logger.info("Loaded %d rows, rejected %d rows (batch %s)",
                len(clean_df), len(rejects_df), batch_id)
