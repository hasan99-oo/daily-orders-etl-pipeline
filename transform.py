"""Transform stage: clean, validate, dedupe, and enrich raw orders.

Every row that fails validation is routed to a rejects DataFrame with
a reason, instead of being dropped silently -- this is what gets
written to rejected_rows so failures are auditable rather than a
mystery row-count drop.
"""
import json
import logging
from datetime import datetime

import pandas as pd

from config import MIN_VALID_QUANTITY, TIMESTAMP_FORMATS

logger = logging.getLogger("etl.transform")


def _parse_timestamp(value: str):
    if not isinstance(value, str) or not value.strip():
        return None
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def transform_orders(raw_df: pd.DataFrame):
    """Returns (clean_df, rejects_df).

    clean_df columns: order_id, customer_id, product_id, product_name,
    quantity, unit_price, total_amount, currency, order_timestamp,
    order_date.
    """
    df = raw_df.copy()
    reject_records = []

    def reject(row, reason):
        reject_records.append({
            "raw_order_id": row.get("order_id"),
            "reason": reason,
            "raw_row_json": json.dumps(row.to_dict()),
        })

    # 1. Drop exact duplicate rows (keep first occurrence)
    before = len(df)
    dup_mask = df.duplicated(keep="first")
    for _, row in df[dup_mask].iterrows():
        reject(row, "duplicate_row")
    df = df[~dup_mask]
    logger.info("Dropped %d exact duplicate rows", before - len(df))

    valid_rows = []
    for _, row in df.iterrows():
        # customer_id required
        if not isinstance(row["customer_id"], str) or not row["customer_id"].strip():
            reject(row, "missing_customer_id")
            continue

        # quantity must parse and be >= MIN_VALID_QUANTITY
        try:
            qty = int(row["quantity"])
        except (ValueError, TypeError):
            reject(row, "unparseable_quantity")
            continue
        if qty < MIN_VALID_QUANTITY:
            reject(row, "invalid_quantity")
            continue

        # timestamp must parse in one of the accepted formats
        ts = _parse_timestamp(row["order_timestamp"])
        if ts is None:
            reject(row, "unparseable_timestamp")
            continue

        try:
            unit_price = float(row["unit_price"])
        except (ValueError, TypeError):
            reject(row, "unparseable_unit_price")
            continue

        valid_rows.append({
            "order_id": int(row["order_id"]),
            "customer_id": row["customer_id"].strip(),
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "quantity": qty,
            "unit_price": unit_price,
            "total_amount": round(qty * unit_price, 2),
            "currency": row["currency"],
            "order_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "order_date": ts.strftime("%Y-%m-%d"),
        })

    clean_df = pd.DataFrame(valid_rows)
    rejects_df = pd.DataFrame(reject_records)

    logger.info(
        "Transform complete: %d valid rows, %d rejected rows",
        len(clean_df), len(rejects_df),
    )
    return clean_df, rejects_df
