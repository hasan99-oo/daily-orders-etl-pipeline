-- Handy queries once fact_orders / dim_customer / dim_product are populated

-- 1. Daily revenue
SELECT order_date, ROUND(SUM(total_amount), 2) AS revenue, COUNT(*) AS order_count
FROM fact_orders
GROUP BY order_date
ORDER BY order_date DESC;

-- 2. Top products by revenue
SELECT p.product_name, ROUND(SUM(f.total_amount), 2) AS revenue, SUM(f.quantity) AS units_sold
FROM fact_orders f
JOIN dim_product p ON p.product_id = f.product_id
GROUP BY p.product_name
ORDER BY revenue DESC
LIMIT 10;

-- 3. Repeat customers (more than 1 order)
SELECT customer_id, COUNT(*) AS order_count, ROUND(SUM(total_amount), 2) AS lifetime_value
FROM fact_orders
GROUP BY customer_id
HAVING COUNT(*) > 1
ORDER BY lifetime_value DESC;

-- 4. Latest ETL run health
SELECT batch_id, source_file, rows_extracted, rows_rejected, rows_loaded, status, started_at, finished_at
FROM etl_audit_log
ORDER BY started_at DESC
LIMIT 5;

-- 5. Why rows were rejected in the most recent batch
SELECT reason, COUNT(*) AS cnt
FROM rejected_rows
WHERE batch_id = (SELECT batch_id FROM etl_audit_log ORDER BY started_at DESC LIMIT 1)
GROUP BY reason
ORDER BY cnt DESC;
