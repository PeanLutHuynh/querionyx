import unittest

from src.sql.text_to_sql import TextToSQLPipeline


class TestFastSqlPlanner(unittest.TestCase):
    def test_top_five_customers_by_number_of_orders_uses_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Top 5 customers by number of orders.")

        self.assertEqual(
            sql,
            "SELECT c.company_name, COUNT(o.order_id) AS order_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.company_name ORDER BY order_count DESC, c.company_name LIMIT 5;",
        )

    def test_top_five_products_by_number_of_orders_uses_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Top 5 products by number of orders.")

        self.assertEqual(
            sql,
            "SELECT p.product_name, COUNT(DISTINCT od.order_id) AS order_count FROM products p JOIN order_details od ON p.product_id = od.product_id GROUP BY p.product_name ORDER BY order_count DESC, p.product_name LIMIT 5;",
        )

    def test_top_one_product_by_count_uses_quantity_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Top 1 product by count")

        self.assertEqual(
            sql,
            "SELECT p.product_name, SUM(od.quantity) AS total_quantity_sold FROM products p JOIN order_details od ON p.product_id = od.product_id GROUP BY p.product_name ORDER BY total_quantity_sold DESC, p.product_name LIMIT 1;",
        )

    def test_best_product_by_count_uses_quantity_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("The best product by count")

        self.assertEqual(
            sql,
            "SELECT p.product_name, SUM(od.quantity) AS total_quantity_sold FROM products p JOIN order_details od ON p.product_id = od.product_id GROUP BY p.product_name ORDER BY total_quantity_sold DESC, p.product_name LIMIT 10;",
        )

    def test_product_sold_the_most_uses_quantity_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Which product sold the most?")

        self.assertEqual(
            sql,
            "SELECT p.product_name, SUM(od.quantity) AS total_quantity_sold FROM products p JOIN order_details od ON p.product_id = od.product_id GROUP BY p.product_name ORDER BY total_quantity_sold DESC, p.product_name LIMIT 1;",
        )

    def test_vietnamese_best_selling_product_uses_quantity_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Sản phẩm bán chạy nhất theo số lượng là gì?")

        self.assertEqual(
            sql,
            "SELECT p.product_name, SUM(od.quantity) AS total_quantity_sold FROM products p JOIN order_details od ON p.product_id = od.product_id GROUP BY p.product_name ORDER BY total_quantity_sold DESC, p.product_name LIMIT 1;",
        )

    def test_vietnamese_short_best_selling_product_uses_quantity_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Sản phẩm bán chạy nhất")

        self.assertEqual(
            sql,
            "SELECT p.product_name, SUM(od.quantity) AS total_quantity_sold FROM products p JOIN order_details od ON p.product_id = od.product_id GROUP BY p.product_name ORDER BY total_quantity_sold DESC, p.product_name LIMIT 1;",
        )

    def test_vietnamese_most_sold_product_uses_quantity_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Sản phẩm bán nhiều nhất")

        self.assertEqual(
            sql,
            "SELECT p.product_name, SUM(od.quantity) AS total_quantity_sold FROM products p JOIN order_details od ON p.product_id = od.product_id GROUP BY p.product_name ORDER BY total_quantity_sold DESC, p.product_name LIMIT 1;",
        )

    def test_vietnamese_order_count_uses_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Hiện có bao nhiêu đơn hàng trong hệ thống?")

        self.assertEqual(sql, "SELECT COUNT(*) AS order_count FROM orders;")

    def test_vietnamese_top_customer_spending_uses_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Top khách hàng theo tổng chi tiêu (top N) là ai?")

        self.assertEqual(
            sql,
            "SELECT c.company_name, ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount))::numeric, 2) AS total_spent FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_details od ON o.order_id = od.order_id GROUP BY c.company_name ORDER BY total_spent DESC, c.company_name LIMIT 5;",
        )

    def test_vietnamese_generic_grouped_orders_uses_year_fast_path(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Truy vấn doanh thu/đơn hàng/phân nhóm theo yêu cầu")

        self.assertEqual(
            sql,
            "SELECT EXTRACT(YEAR FROM order_date) AS year, COUNT(*) AS order_count FROM orders GROUP BY year ORDER BY year;",
        )

    def test_supplier_with_most_products_uses_fast_path_without_product_word(self) -> None:
        pipeline = TextToSQLPipeline.__new__(TextToSQLPipeline)

        sql = pipeline._generate_fast_sql("Nhà cung cấp nào cung cấp nhiều nhất?")

        self.assertEqual(
            sql,
            "SELECT s.company_name, COUNT(p.product_id) AS product_count FROM suppliers s JOIN products p ON s.supplier_id = p.supplier_id GROUP BY s.company_name ORDER BY product_count DESC, s.company_name LIMIT 5;",
        )


if __name__ == "__main__":
    unittest.main()
