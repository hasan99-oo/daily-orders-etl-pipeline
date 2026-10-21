-- Target warehouse schema for the daily orders ETL pipeline
-- Designed for SQLite by default (see config.py) but written in
-- portable ANSI SQL that maps cleanly onto Postgres/MySQL as well.

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id     TEXT PRIMARY KEY,
    first_seen_date TEXT NOT NULL,
    last_seen_date  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id      TEXT PRIMARY KEY,
    product_name    TEXT NOT NULL,
    unit_price      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_orders (
    order_id         INTEGER PRIMARY KEY,
    customer_id      TEXT NOT NULL,
    product_id       TEXT NOT NULL,
    quantity         INTEGER NOT NULL,
    unit_price       REAL NOT NULL,
    total_amount     REAL NOT NULL,
    currency         TEXT NOT NULL,
    order_timestamp  TEXT NOT NULL,
    order_date       TEXT NOT NULL,
    load_batch_id    TEXT NOT NULL,
    loaded_at        TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
    FOREIGN KEY (product_id)  REFERENCES dim_product(product_id)
);

CREATE TABLE IF NOT EXISTS etl_audit_log (
    batch_id            TEXT PRIMARY KEY,
    source_file         TEXT NOT NULL,
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    rows_extracted      INTEGER,
    rows_rejected       INTEGER,
    rows_loaded         INTEGER,
    status              TEXT NOT NULL,
    error_message       TEXT
);

CREATE TABLE IF NOT EXISTS rejected_rows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL,
    raw_order_id    TEXT,
    reason          TEXT NOT NULL,
    raw_row_json    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_orders_date ON fact_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_fact_orders_customer ON fact_orders(customer_id);
