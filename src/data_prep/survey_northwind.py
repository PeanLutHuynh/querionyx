from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_REPORT_PATH = PROJECT_ROOT / "docs" / "data_prep" / "northwind_schema.md"
QUERY_DATA_PATH = PROJECT_ROOT / "data" / "test_queries" / "sql_queries.json"
SQL_DUMP_PATH = PROJECT_ROOT / ".tmp" / "northwind_psql" / "northwind.sql"
CORE_TABLES = [
    "categories",
    "products",
    "suppliers",
    "customers",
    "orders",
    "order_details",
    "employees",
    "shippers",
]


@dataclass(frozen=True)
class QuerySpec:
    identifier: str
    question: str
    expected_sql: str
    difficulty: str
    query_type: str


def connect() -> psycopg2.extensions.connection:
    load_dotenv(override=True)
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DB", "northwind"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )


def bootstrap_northwind(connection: psycopg2.extensions.connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.products')")
        has_products_table = cursor.fetchone()[0] is not None

    if has_products_table:
        return

    if not SQL_DUMP_PATH.exists():
        raise FileNotFoundError(
            f"Northwind SQL dump not found at {SQL_DUMP_PATH}. Clone pthom/northwind_psql first."
        )

    sql_text = SQL_DUMP_PATH.read_text(encoding="utf-8")
    connection.rollback()
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(sql_text)

    connection.autocommit = False


def fetch_tables(cursor) -> list[str]:
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
    )
    return [row[0] for row in cursor.fetchall()]


def fetch_columns(cursor) -> dict[str, list[dict[str, Any]]]:
    cursor.execute(
        """
        SELECT table_name, column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
        """
    )
    columns_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for table_name, column_name, data_type, is_nullable, ordinal_position in cursor.fetchall():
        columns_by_table[table_name].append(
            {
                "column_name": column_name,
                "data_type": data_type,
                "is_nullable": is_nullable,
                "ordinal_position": ordinal_position,
            }
        )
    return dict(columns_by_table)


def fetch_foreign_keys(cursor) -> list[dict[str, str]]:
    cursor.execute(
        """
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
           AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
           AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
        ORDER BY tc.table_name, kcu.column_name
        """
    )
    foreign_keys: list[dict[str, str]] = []
    for table_name, column_name, foreign_table_name, foreign_column_name, constraint_name in cursor.fetchall():
        foreign_keys.append(
            {
                "table_name": table_name,
                "column_name": column_name,
                "foreign_table_name": foreign_table_name,
                "foreign_column_name": foreign_column_name,
                "constraint_name": constraint_name,
            }
        )
    return foreign_keys


def fetch_row_counts(cursor) -> dict[str, int]:
    cursor.execute(
        """
        SELECT relname, n_live_tup::bigint
        FROM pg_stat_user_tables
        ORDER BY relname
        """
    )
    return {row[0]: int(row[1]) for row in cursor.fetchall()}


def json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        if value == value.to_integral():
            return int(value)
        return float(value)
    return value


def format_expected_answer(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    if not rows:
        return "No rows returned."

    if len(rows) == 1 and len(columns) == 1:
        return str(json_safe(rows[0][0]))

    if len(rows) == 1:
        payload = {columns[index]: json_safe(value) for index, value in enumerate(rows[0])}
        return json.dumps(payload, ensure_ascii=False, indent=2)

    payload = []
    for row in rows:
        payload.append({columns[index]: json_safe(value) for index, value in enumerate(row)})
    return json.dumps(payload, ensure_ascii=False, indent=2)


def execute_query(cursor, sql_text: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    cursor.execute(sql_text)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return columns, rows


def build_schema_markdown(tables: list[str], columns_by_table: dict[str, list[dict[str, Any]]], foreign_keys: list[dict[str, str]], row_counts: dict[str, int]) -> str:
    lines: list[str] = []
    lines.append("# Northwind Schema Survey")
    lines.append("")
    lines.append("Generated from the live PostgreSQL Northwind database used by Querionyx.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total tables: {len(tables)}")
    lines.append(f"- Core tables identified: {len(CORE_TABLES)}")
    lines.append("")
    lines.append("## Core Tables")
    lines.append("")
    for table_name in CORE_TABLES:
        status = "present" if table_name in tables else "missing"
        count_value = row_counts.get(table_name, 0)
        lines.append(f"- {table_name}: {status}, approx. {count_value} rows")
    lines.append("")
    lines.append("## Tables and Columns")
    lines.append("")
    for table_name in tables:
        core_flag = "core" if table_name in CORE_TABLES else "auxiliary"
        lines.append(f"### {table_name} ({core_flag})")
        lines.append("")
        lines.append("| Column | Data Type | Nullable |")
        lines.append("| --- | --- | --- |")
        for column in columns_by_table.get(table_name, []):
            nullable = "YES" if column["is_nullable"] == "YES" else "NO"
            lines.append(f"| {column['column_name']} | {column['data_type']} | {nullable} |")
        lines.append("")
    lines.append("## Foreign Keys")
    lines.append("")
    lines.append("| Table | Column | References | Reference Column | Constraint |")
    lines.append("| --- | --- | --- | --- | --- |")
    for fk in foreign_keys:
        lines.append(
            f"| {fk['table_name']} | {fk['column_name']} | {fk['foreign_table_name']} | {fk['foreign_column_name']} | {fk['constraint_name']} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- All columns were read directly from information_schema.")
    lines.append("- Row counts are approximate and come from pg_stat_user_tables.")
    lines.append("- The eight core tables are the main focus for schema linking and Text-to-SQL evaluation.")
    lines.append("")
    return "\n".join(lines)


def build_query_specs() -> list[QuerySpec]:
    return [
        QuerySpec("sql_001", "What are the first 10 product names in alphabetical order?", "SELECT product_name FROM products ORDER BY product_name LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_002", "What are the first 10 customer company names in alphabetical order?", "SELECT company_name FROM customers ORDER BY company_name LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_003", "What are the first 10 supplier company names in alphabetical order?", "SELECT company_name FROM suppliers ORDER BY company_name LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_004", "What are the first 10 category names in alphabetical order?", "SELECT category_name FROM categories ORDER BY category_name LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_005", "What are the first 10 shipper company names in alphabetical order?", "SELECT company_name FROM shippers ORDER BY company_name LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_006", "What are the first 10 employee names in alphabetical order by last name?", "SELECT first_name, last_name FROM employees ORDER BY last_name, first_name LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_007", "What are the first 10 order IDs in ascending order?", "SELECT order_id FROM orders ORDER BY order_id LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_008", "What are the first 10 territory descriptions in alphabetical order?", "SELECT territory_description FROM territories ORDER BY territory_description LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_009", "What are the first 10 region descriptions in alphabetical order?", "SELECT region_description FROM region ORDER BY region_description LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_010", "What are the first 10 distinct ship countries from orders?", "SELECT DISTINCT ship_country FROM orders ORDER BY ship_country LIMIT 10;", "easy", "simple_select"),
        QuerySpec("sql_011", "How many products are in each category?", "SELECT category_id, COUNT(*) AS product_count FROM products GROUP BY category_id ORDER BY product_count DESC, category_id;", "medium", "aggregate"),
        QuerySpec("sql_012", "What is the average unit price by category?", "SELECT category_id, ROUND(AVG(unit_price)::numeric, 2) AS avg_unit_price FROM products GROUP BY category_id ORDER BY avg_unit_price DESC, category_id;", "medium", "aggregate"),
        QuerySpec("sql_013", "What is the total units in stock by supplier?", "SELECT supplier_id, SUM(units_in_stock) AS total_units_in_stock FROM products GROUP BY supplier_id ORDER BY total_units_in_stock DESC, supplier_id;", "medium", "aggregate"),
        QuerySpec("sql_014", "How many orders are there per ship country?", "SELECT ship_country, COUNT(*) AS order_count FROM orders GROUP BY ship_country ORDER BY order_count DESC, ship_country;", "medium", "aggregate"),
        QuerySpec("sql_015", "What is the average freight by shipping method?", "SELECT ship_via, ROUND(AVG(freight)::numeric, 2) AS avg_freight FROM orders GROUP BY ship_via ORDER BY avg_freight DESC, ship_via;", "medium", "aggregate"),
        QuerySpec("sql_016", "How many employees are there per country?", "SELECT country, COUNT(*) AS employee_count FROM employees GROUP BY country ORDER BY employee_count DESC, country;", "medium", "aggregate"),
        QuerySpec("sql_017", "How many customers are there per country?", "SELECT country, COUNT(*) AS customer_count FROM customers GROUP BY country ORDER BY customer_count DESC, country;", "medium", "aggregate"),
        QuerySpec("sql_018", "What is the total units on order by category?", "SELECT category_id, SUM(units_on_order) AS total_units_on_order FROM products GROUP BY category_id ORDER BY total_units_on_order DESC, category_id;", "medium", "aggregate"),
        QuerySpec("sql_019", "How many products are discontinued versus active?", "SELECT discontinued, COUNT(*) AS product_count FROM products GROUP BY discontinued ORDER BY discontinued;", "medium", "aggregate"),
        QuerySpec("sql_020", "What is the average units in stock by discontinued status?", "SELECT discontinued, ROUND(AVG(units_in_stock)::numeric, 2) AS avg_units_in_stock FROM products GROUP BY discontinued ORDER BY discontinued;", "medium", "aggregate"),
        QuerySpec("sql_021", "List product names together with their category names.", "SELECT p.product_name, c.category_name FROM products p JOIN categories c ON p.category_id = c.category_id ORDER BY p.product_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_022", "List product names together with their supplier company names.", "SELECT p.product_name, s.company_name AS supplier_name FROM products p JOIN suppliers s ON p.supplier_id = s.supplier_id ORDER BY p.product_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_023", "List customer company names together with their order counts.", "SELECT c.company_name, COUNT(o.order_id) AS order_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.company_name ORDER BY order_count DESC, c.company_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_024", "List employee names together with their order counts.", "SELECT e.first_name || ' ' || e.last_name AS employee_name, COUNT(o.order_id) AS order_count FROM employees e JOIN orders o ON e.employee_id = o.employee_id GROUP BY employee_name ORDER BY order_count DESC, employee_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_025", "List shipper company names together with their shipment counts.", "SELECT s.company_name, COUNT(o.order_id) AS shipment_count FROM shippers s JOIN orders o ON s.shipper_id = o.ship_via GROUP BY s.company_name ORDER BY shipment_count DESC, s.company_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_026", "List product names together with sold quantity across all order details.", "SELECT p.product_name, SUM(od.quantity) AS total_quantity_sold FROM order_details od JOIN products p ON od.product_id = p.product_id GROUP BY p.product_name ORDER BY total_quantity_sold DESC, p.product_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_027", "List customer company names together with their latest order date.", "SELECT c.company_name, MAX(o.order_date) AS latest_order_date FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.company_name ORDER BY latest_order_date DESC, c.company_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_028", "List order IDs together with customer company names for the first 10 orders.", "SELECT o.order_id, c.company_name FROM orders o JOIN customers c ON o.customer_id = c.customer_id ORDER BY o.order_id LIMIT 10;", "medium", "join"),
        QuerySpec("sql_029", "List order IDs together with employee names for the first 10 orders.", "SELECT o.order_id, e.first_name || ' ' || e.last_name AS employee_name FROM orders o JOIN employees e ON o.employee_id = e.employee_id ORDER BY o.order_id LIMIT 10;", "medium", "join"),
        QuerySpec("sql_030", "List order IDs together with shipper company names for the first 10 orders.", "SELECT o.order_id, s.company_name AS shipper_name FROM orders o JOIN shippers s ON o.ship_via = s.shipper_id ORDER BY o.order_id LIMIT 10;", "medium", "join"),
        QuerySpec("sql_031", "List category names together with product counts.", "SELECT c.category_name, COUNT(p.product_id) AS product_count FROM categories c JOIN products p ON c.category_id = p.category_id GROUP BY c.category_name ORDER BY product_count DESC, c.category_name;", "medium", "join"),
        QuerySpec("sql_032", "List supplier company names together with average product unit price.", "SELECT s.company_name, ROUND(AVG(p.unit_price)::numeric, 2) AS avg_unit_price FROM suppliers s JOIN products p ON s.supplier_id = p.supplier_id GROUP BY s.company_name ORDER BY avg_unit_price DESC, s.company_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_033", "List product names together with revenue generated from order details.", "SELECT p.product_name, ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount))::numeric, 2) AS revenue FROM order_details od JOIN products p ON od.product_id = p.product_id GROUP BY p.product_name ORDER BY revenue DESC, p.product_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_034", "List order IDs together with the number of line items in each order.", "SELECT o.order_id, COUNT(od.product_id) AS line_item_count FROM orders o JOIN order_details od ON o.order_id = od.order_id GROUP BY o.order_id ORDER BY line_item_count DESC, o.order_id LIMIT 10;", "medium", "join"),
        QuerySpec("sql_035", "List customer company names together with the number of distinct ship countries in their orders.", "SELECT c.company_name, COUNT(DISTINCT o.ship_country) AS ship_country_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.company_name ORDER BY ship_country_count DESC, c.company_name LIMIT 10;", "medium", "join"),
        QuerySpec("sql_036", "What is the total revenue per order for the top 10 orders?", "SELECT o.order_id, c.company_name, ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount))::numeric, 2) AS order_revenue FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN order_details od ON o.order_id = od.order_id GROUP BY o.order_id, c.company_name ORDER BY order_revenue DESC, o.order_id LIMIT 10;", "hard", "complex"),
        QuerySpec("sql_037", "List product names with their category names and supplier names.", "SELECT p.product_name, c.category_name, s.company_name AS supplier_name FROM products p JOIN categories c ON p.category_id = c.category_id JOIN suppliers s ON p.supplier_id = s.supplier_id ORDER BY p.product_name LIMIT 10;", "hard", "complex"),
        QuerySpec("sql_038", "List employee names with the territories they cover.", "SELECT e.first_name || ' ' || e.last_name AS employee_name, t.territory_description FROM employees e JOIN employee_territories et ON e.employee_id = et.employee_id JOIN territories t ON et.territory_id = t.territory_id ORDER BY employee_name, territory_description LIMIT 10;", "hard", "complex"),
        QuerySpec("sql_039", "Which products are priced above the overall average product price?", "SELECT product_name, unit_price FROM products WHERE unit_price > (SELECT AVG(unit_price) FROM products) ORDER BY unit_price DESC LIMIT 10;", "hard", "complex"),
        QuerySpec("sql_040", "Which customers have placed more than five orders?", "SELECT company_name FROM customers WHERE customer_id IN (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 5) ORDER BY company_name LIMIT 10;", "hard", "complex"),
        QuerySpec("sql_041", "What are the top 5 most expensive products?", "SELECT product_name, unit_price FROM products ORDER BY unit_price DESC LIMIT 5;", "easy", "filter"),
        QuerySpec("sql_042", "What are the top 5 products with the highest stock?", "SELECT product_name, units_in_stock FROM products ORDER BY units_in_stock DESC LIMIT 5;", "easy", "filter"),
        QuerySpec("sql_043", "Which customers are located in the USA?", "SELECT company_name, city, country FROM customers WHERE country = 'USA' ORDER BY company_name LIMIT 10;", "easy", "filter"),
        QuerySpec("sql_044", "Which orders were placed in 1997 with the highest freight values?", "SELECT order_id, order_date, freight FROM orders WHERE order_date >= DATE '1997-01-01' AND order_date < DATE '1998-01-01' ORDER BY freight DESC LIMIT 10;", "easy", "filter"),
        QuerySpec("sql_045", "Which employees were hired after 1993?", "SELECT first_name, last_name, hire_date FROM employees WHERE hire_date > DATE '1993-12-31' ORDER BY hire_date LIMIT 10;", "easy", "filter"),
        QuerySpec("sql_046", "Which suppliers are based in the USA?", "SELECT company_name, city FROM suppliers WHERE country = 'USA' ORDER BY company_name LIMIT 10;", "easy", "filter"),
        QuerySpec("sql_047", "Which products have stock below their reorder level?", "SELECT product_name, units_in_stock, reorder_level FROM products WHERE units_in_stock < reorder_level ORDER BY (reorder_level - units_in_stock) DESC, product_name LIMIT 10;", "easy", "filter"),
        QuerySpec("sql_048", "Which orders have freight above 100?", "SELECT order_id, freight FROM orders WHERE freight > 100 ORDER BY freight DESC LIMIT 10;", "easy", "filter"),
        QuerySpec("sql_049", "Which active products are priced above 50?", "SELECT product_name, unit_price FROM products WHERE discontinued = 0 AND unit_price > 50 ORDER BY unit_price DESC LIMIT 10;", "easy", "filter"),
        QuerySpec("sql_050", "Which customers are located in Germany?", "SELECT company_name, city FROM customers WHERE country = 'Germany' ORDER BY company_name LIMIT 10;", "easy", "filter"),
    ]


def build_query_dataset(cursor) -> list[dict[str, Any]]:
    dataset: list[dict[str, Any]] = []
    for spec in build_query_specs():
        columns, rows = execute_query(cursor, spec.expected_sql)
        dataset.append(
            {
                "id": spec.identifier,
                "question": spec.question,
                "expected_sql": spec.expected_sql,
                "expected_answer": format_expected_answer(columns, rows),
                "difficulty": spec.difficulty,
                "query_type": spec.query_type,
            }
        )
    return dataset


def write_schema_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_query_dataset(path: Path, dataset: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"queries": dataset}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    connection = connect()
    try:
        bootstrap_northwind(connection)
        with connection.cursor() as cursor:
            tables = fetch_tables(cursor)
            columns_by_table = fetch_columns(cursor)
            foreign_keys = fetch_foreign_keys(cursor)
            row_counts = fetch_row_counts(cursor)
            schema_markdown = build_schema_markdown(tables, columns_by_table, foreign_keys, row_counts)
            query_dataset = build_query_dataset(cursor)

        write_schema_report(SCHEMA_REPORT_PATH, schema_markdown)
        write_query_dataset(QUERY_DATA_PATH, query_dataset)

        print(f"Schema report written to {SCHEMA_REPORT_PATH}")
        print(f"Query dataset written to {QUERY_DATA_PATH}")
        print(f"Tables surveyed: {len(tables)}")
        print(f"Queries generated: {len(query_dataset)}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
