"""Unit tests for etl.transform. Run with: pytest tests/"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.transform import transform_orders  # noqa: E402


def _base_row(**overrides):
    row = {
        "order_id": "1", "customer_id": "CUST0001", "product_id": "PROD001",
        "product_name": "Wireless Mouse", "quantity": "2", "unit_price": "19.99",
        "order_timestamp": "2026-08-03 10:00:00", "currency": "USD",
    }
    row.update(overrides)
    return row


def test_valid_row_passes():
    df = pd.DataFrame([_base_row()])
    clean, rejects = transform_orders(df)
    assert len(clean) == 1
    assert len(rejects) == 0
    assert clean.iloc[0]["total_amount"] == 39.98


def test_missing_customer_id_is_rejected():
    df = pd.DataFrame([_base_row(customer_id="")])
    clean, rejects = transform_orders(df)
    assert len(clean) == 0
    assert rejects.iloc[0]["reason"] == "missing_customer_id"


def test_negative_quantity_is_rejected():
    df = pd.DataFrame([_base_row(quantity="-1")])
    clean, rejects = transform_orders(df)
    assert len(clean) == 0
    assert rejects.iloc[0]["reason"] == "invalid_quantity"


def test_bad_timestamp_is_rejected():
    df = pd.DataFrame([_base_row(order_timestamp="not-a-date")])
    clean, rejects = transform_orders(df)
    assert len(clean) == 0
    assert rejects.iloc[0]["reason"] == "unparseable_timestamp"


def test_alternate_timestamp_format_is_accepted():
    df = pd.DataFrame([_base_row(order_timestamp="08/03/2026")])
    clean, rejects = transform_orders(df)
    assert len(clean) == 1
    assert clean.iloc[0]["order_date"] == "2026-08-03"


def test_exact_duplicate_rows_are_deduped():
    row = _base_row()
    df = pd.DataFrame([row, row])
    clean, rejects = transform_orders(df)
    assert len(clean) == 1
    assert len(rejects) == 1
    assert rejects.iloc[0]["reason"] == "duplicate_row"
