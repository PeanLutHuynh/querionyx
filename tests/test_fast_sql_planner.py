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


if __name__ == "__main__":
    unittest.main()
