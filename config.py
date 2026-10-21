"""
Central configuration for the orders ETL pipeline.

Values here can be overridden with environment variables so the same
code runs unchanged in dev / staging / prod (e.g. swap SQLite for
Postgres by setting DATABASE_URL).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# --- Paths -------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
SCHEMA_FILE = BASE_DIR / "sql" / "schema.sql"

# --- Database ------------------------------------------------------------
# Swap this for a real warehouse in prod, e.g.:
#   postgresql+psycopg2://user:pass@host:5432/warehouse
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{OUTPUT_DIR / 'warehouse.db'}")

# --- Pipeline behavior ---------------------------------------------------
# Rows with quantity <= 0, missing customer_id, or unparseable timestamps
# are rejected rather than silently dropped or guessed at.
MIN_VALID_QUANTITY = 1
REQUIRED_COLUMNS = [
    "order_id", "customer_id", "product_id", "product_name",
    "quantity", "unit_price", "order_timestamp", "currency",
]

# Accepted incoming timestamp formats, tried in order.
TIMESTAMP_FORMATS = ["%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]

LOG_LEVEL = os.environ.get("ETL_LOG_LEVEL", "INFO")
