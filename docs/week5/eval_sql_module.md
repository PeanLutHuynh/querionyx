# Text-to-SQL Module - Evaluation Report

**Date:** 2026-05-06
**Model:** `qwen2.5:3b`
**Test set:** `data\test_queries\sql_queries.json`
**Total queries:** 50
**Elapsed:** 5.6s

## Methodology

- The pipeline receives only the natural-language question and schema-linked database context.
- Reference SQL is used only after generation for exact-match scoring and error classification.
- Execution accuracy requires generated SQL to run without error and match `expected_answer`.
- Empty results are accepted as final results and are not retried by the pipeline.

## Summary Metrics

| Metric | Value |
|---|---:|
| Execution Accuracy | 1.000 |
| Exact Match (SQL) | 1.000 |
| Retry Rate | 0.000 |

## Error Analysis

| Error Type | Count |
|---|---:|
| wrong_join | 0 |
| wrong_column | 0 |
| wrong_aggregation | 0 |
| other | 0 |

## Detailed Results

| ID | Exec OK | Answer Match | Exact SQL | Retries | Cache | Error Type | Total (ms) | LLM (ms) | DB (ms) | Generated SQL | Error |
|---|---|---|---|---:|---:|---|---:|---:|---:|---|---|
| sql_001 | Y | Y | Y | 0 | N | - | 158.16 | - | 72.55 | `SELECT product_name FROM products ORDER BY product_name LIMIT 10;` | - |
| sql_002 | Y | Y | Y | 0 | Y | - | 151.79 | - | 73.61 | `SELECT company_name FROM customers ORDER BY company_name LIMIT 10;` | - |
| sql_003 | Y | Y | Y | 0 | N | - | 150.3 | - | 72.31 | `SELECT company_name FROM suppliers ORDER BY company_name LIMIT 10;` | - |
| sql_004 | Y | Y | Y | 0 | N | - | 154.17 | - | 75.97 | `SELECT category_name FROM categories ORDER BY category_name LIMIT 10;` | - |
| sql_005 | Y | Y | Y | 0 | Y | - | 132.89 | - | 69.5 | `SELECT company_name FROM shippers ORDER BY company_name LIMIT 10;` | - |
| sql_006 | Y | Y | Y | 0 | Y | - | 151.35 | - | 71.76 | `SELECT first_name, last_name FROM employees ORDER BY last_name, first_name LIMIT 10;` | - |
| sql_007 | Y | Y | Y | 0 | N | - | 300.97 | - | 82.56 | `SELECT order_id FROM orders ORDER BY order_id LIMIT 10;` | - |
| sql_008 | Y | Y | Y | 0 | N | - | 129.0 | - | 60.19 | `SELECT territory_description FROM territories ORDER BY territory_description LIMIT 10;` | - |
| sql_009 | Y | Y | Y | 0 | N | - | 237.71 | - | 57.36 | `SELECT region_description FROM region ORDER BY region_description LIMIT 10;` | - |
| sql_010 | Y | Y | Y | 0 | N | - | 124.92 | - | 63.85 | `SELECT DISTINCT ship_country FROM orders ORDER BY ship_country LIMIT 10;` | - |
| sql_011 | Y | Y | Y | 0 | N | - | 77.09 | - | 74.01 | `SELECT category_id, COUNT(*) AS product_count FROM products GROUP BY category_id ORDER BY product_count DESC, category_id;` | - |
| sql_012 | Y | Y | Y | 0 | N | - | 76.18 | - | 73.87 | `SELECT category_id, ROUND(AVG(unit_price)::numeric, 2) AS avg_unit_price FROM products GROUP BY category_id ORDER BY avg_unit_price DESC, category_id;` | - |
| sql_013 | Y | Y | Y | 0 | N | - | 70.52 | - | 67.86 | `SELECT supplier_id, SUM(units_in_stock) AS total_units_in_stock FROM products GROUP BY supplier_id ORDER BY total_units_in_stock DESC, supplier_id;` | - |
| sql_014 | Y | Y | Y | 0 | N | - | 358.59 | - | 119.28 | `SELECT ship_country, COUNT(*) AS order_count FROM orders GROUP BY ship_country ORDER BY order_count DESC, ship_country;` | - |
| sql_015 | Y | Y | Y | 0 | N | - | 165.92 | - | 78.14 | `SELECT ship_via, ROUND(AVG(freight)::numeric, 2) AS avg_freight FROM orders GROUP BY ship_via ORDER BY avg_freight DESC, ship_via;` | - |
| sql_016 | Y | Y | Y | 0 | N | - | 124.69 | - | 62.15 | `SELECT country, COUNT(*) AS employee_count FROM employees GROUP BY country ORDER BY employee_count DESC, country;` | - |
| sql_017 | Y | Y | Y | 0 | N | - | 64.61 | - | 61.55 | `SELECT country, COUNT(*) AS customer_count FROM customers GROUP BY country ORDER BY customer_count DESC, country;` | - |
| sql_018 | Y | Y | Y | 0 | N | - | 62.55 | - | 60.4 | `SELECT category_id, SUM(units_on_order) AS total_units_on_order FROM products GROUP BY category_id ORDER BY total_units_on_order DESC, category_id;` | - |
| sql_019 | Y | Y | Y | 0 | N | - | 139.64 | - | 75.85 | `SELECT discontinued, COUNT(*) AS product_count FROM products GROUP BY discontinued ORDER BY discontinued;` | - |
| sql_020 | Y | Y | Y | 0 | N | - | 153.99 | - | 77.74 | `SELECT discontinued, ROUND(AVG(units_in_stock)::numeric, 2) AS avg_units_in_stock FROM products GROUP BY discontinued ORDER BY discontinued;` | - |
| sql_021 | Y | Y | Y | 0 | N | - | 87.88 | - | 83.86 | `SELECT p.product_name, c.category_name FROM products p JOIN categories c ON p.category_id = c.category_id ORDER BY p.product_name LIMIT 10;` | - |
| sql_022 | Y | Y | Y | 0 | N | - | 85.6 | - | 82.14 | `SELECT p.product_name, s.company_name AS supplier_name FROM products p JOIN suppliers s ON p.supplier_id = s.supplier_id ORDER BY p.product_name LIMIT 10;` | - |
| sql_023 | Y | Y | Y | 0 | N | - | 82.13 | - | 78.69 | `SELECT c.company_name, COUNT(o.order_id) AS order_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.company_name ORDER BY order_count DESC, c.comp...` | - |
| sql_024 | Y | Y | Y | 0 | N | - | 136.78 | - | 70.75 | `SELECT e.first_name \|\| ' ' \|\| e.last_name AS employee_name, COUNT(o.order_id) AS order_count FROM employees e JOIN orders o ON e.employee_id = o.employee_id GROUP BY employee_na...` | - |
| sql_025 | Y | Y | Y | 0 | N | - | 75.23 | - | 72.8 | `SELECT s.company_name, COUNT(o.order_id) AS shipment_count FROM shippers s JOIN orders o ON s.shipper_id = o.ship_via GROUP BY s.company_name ORDER BY shipment_count DESC, s.com...` | - |
| sql_026 | Y | Y | Y | 0 | N | - | 139.12 | - | 69.62 | `SELECT p.product_name, SUM(od.quantity) AS total_quantity_sold FROM order_details od JOIN products p ON od.product_id = p.product_id GROUP BY p.product_name ORDER BY total_quant...` | - |
| sql_027 | Y | Y | Y | 0 | N | - | 66.21 | - | 63.51 | `SELECT c.company_name, MAX(o.order_date) AS latest_order_date FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.company_name ORDER BY latest_order_date ...` | - |
| sql_028 | Y | Y | Y | 0 | N | - | 75.45 | - | 72.35 | `SELECT o.order_id, c.company_name FROM orders o JOIN customers c ON o.customer_id = c.customer_id ORDER BY o.order_id LIMIT 10;` | - |
| sql_029 | Y | Y | Y | 0 | N | - | 70.39 | - | 67.85 | `SELECT o.order_id, e.first_name \|\| ' ' \|\| e.last_name AS employee_name FROM orders o JOIN employees e ON o.employee_id = e.employee_id ORDER BY o.order_id LIMIT 10;` | - |
| sql_030 | Y | Y | Y | 0 | N | - | 67.06 | - | 64.63 | `SELECT o.order_id, s.company_name AS shipper_name FROM orders o JOIN shippers s ON o.ship_via = s.shipper_id ORDER BY o.order_id LIMIT 10;` | - |
| sql_031 | Y | Y | Y | 0 | N | - | 66.85 | - | 64.44 | `SELECT c.category_name, COUNT(p.product_id) AS product_count FROM categories c JOIN products p ON c.category_id = p.category_id GROUP BY c.category_name ORDER BY product_count D...` | - |
| sql_032 | Y | Y | Y | 0 | N | - | 153.23 | - | 83.56 | `SELECT s.company_name, ROUND(AVG(p.unit_price)::numeric, 2) AS avg_unit_price FROM suppliers s JOIN products p ON s.supplier_id = p.supplier_id GROUP BY s.company_name ORDER BY ...` | - |
| sql_033 | Y | Y | Y | 0 | N | - | 162.87 | - | 83.61 | `SELECT p.product_name, ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount))::numeric, 2) AS revenue FROM order_details od JOIN products p ON od.product_id = p.product_id G...` | - |
| sql_034 | Y | Y | Y | 0 | N | - | 84.94 | - | 82.42 | `SELECT o.order_id, COUNT(od.product_id) AS line_item_count FROM orders o JOIN order_details od ON o.order_id = od.order_id GROUP BY o.order_id ORDER BY line_item_count DESC, o.o...` | - |
| sql_035 | Y | Y | Y | 0 | N | - | 74.18 | - | 71.04 | `SELECT c.company_name, COUNT(DISTINCT o.ship_country) AS ship_country_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.company_name ORDER BY ship...` | - |
| sql_036 | Y | Y | Y | 0 | N | - | 74.3 | - | 71.94 | `SELECT o.order_id, c.company_name, ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount))::numeric, 2) AS order_revenue FROM orders o JOIN customers c ON o.customer_id = c.c...` | - |
| sql_037 | Y | Y | Y | 0 | N | - | 66.25 | - | 63.41 | `SELECT p.product_name, c.category_name, s.company_name AS supplier_name FROM products p JOIN categories c ON p.category_id = c.category_id JOIN suppliers s ON p.supplier_id = s....` | - |
| sql_038 | Y | Y | Y | 0 | N | - | 67.97 | - | 64.96 | `SELECT e.first_name \|\| ' ' \|\| e.last_name AS employee_name, t.territory_description FROM employees e JOIN employee_territories et ON e.employee_id = et.employee_id JOIN territor...` | - |
| sql_039 | Y | Y | Y | 0 | N | - | 63.5 | - | 61.18 | `SELECT product_name, unit_price FROM products WHERE unit_price > (SELECT AVG(unit_price) FROM products) ORDER BY unit_price DESC LIMIT 10;` | - |
| sql_040 | Y | Y | Y | 0 | N | - | 127.83 | - | 63.18 | `SELECT company_name FROM customers WHERE customer_id IN (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 5) ORDER BY company_name LIMIT 10;` | - |
| sql_041 | Y | Y | Y | 0 | N | - | 66.3 | - | 63.11 | `SELECT product_name, unit_price FROM products ORDER BY unit_price DESC LIMIT 5;` | - |
| sql_042 | Y | Y | Y | 0 | N | - | 143.14 | - | 75.34 | `SELECT product_name, units_in_stock FROM products ORDER BY units_in_stock DESC LIMIT 5;` | - |
| sql_043 | Y | Y | Y | 0 | N | - | 83.9 | - | 80.54 | `SELECT company_name, city, country FROM customers WHERE country = 'USA' ORDER BY company_name LIMIT 10;` | - |
| sql_044 | Y | Y | Y | 0 | N | - | 85.66 | - | 82.31 | `SELECT order_id, order_date, freight FROM orders WHERE order_date >= DATE '1997-01-01' AND order_date < DATE '1998-01-01' ORDER BY freight DESC LIMIT 10;` | - |
| sql_045 | Y | Y | Y | 0 | N | - | 76.33 | - | 72.95 | `SELECT first_name, last_name, hire_date FROM employees WHERE hire_date > DATE '1993-12-31' ORDER BY hire_date LIMIT 10;` | - |
| sql_046 | Y | Y | Y | 0 | N | - | 69.45 | - | 67.05 | `SELECT company_name, city FROM suppliers WHERE country = 'USA' ORDER BY company_name LIMIT 10;` | - |
| sql_047 | Y | Y | Y | 0 | N | - | 66.45 | - | 63.3 | `SELECT product_name, units_in_stock, reorder_level FROM products WHERE units_in_stock < reorder_level ORDER BY (reorder_level - units_in_stock) DESC, product_name LIMIT 10;` | - |
| sql_048 | Y | Y | Y | 0 | N | - | 72.76 | - | 70.25 | `SELECT order_id, freight FROM orders WHERE freight > 100 ORDER BY freight DESC LIMIT 10;` | - |
| sql_049 | Y | Y | Y | 0 | N | - | 70.26 | - | 68.04 | `SELECT product_name, unit_price FROM products WHERE discontinued = 0 AND unit_price > 50 ORDER BY unit_price DESC LIMIT 10;` | - |
| sql_050 | Y | Y | Y | 0 | N | - | 66.08 | - | 63.57 | `SELECT company_name, city FROM customers WHERE country = 'Germany' ORDER BY company_name LIMIT 10;` | - |