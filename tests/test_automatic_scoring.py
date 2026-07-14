import json
import unittest
from decimal import Decimal

from src.evaluation.benchmark_async_hybrid import json_safe_default
from src.evaluation.automatic_scoring import AutomaticScorer, row_set_scores


class TestAutomaticScoring(unittest.TestCase):
    def test_async_fingerprint_serializer_supports_decimal(self) -> None:
        payload = json.dumps({"value": Decimal("12.30")}, default=json_safe_default)
        self.assertEqual(json.loads(payload), {"value": "12.30"})

    def test_row_equivalence_is_column_name_independent(self) -> None:
        precision, recall, f1 = row_set_scores(
            [{"product_name": "Chai", "total_quantity_sold": 828}],
            [{"name": "Chai", "quantity": 828}],
        )
        self.assertEqual((precision, recall, f1), (1.0, 1.0, 1.0))

    def test_sql_reference_score_uses_result_equivalence(self) -> None:
        scorer = AutomaticScorer()
        template = scorer.case_templates["str_001"]
        scorer._reference_rows[template] = [{"product_count": 77}]
        output = {
            "intent": "SQL",
            "sql_success": True,
            "raw": {"sql": {"rows": [{"count": 77}]}},
        }

        result = scorer.score(
            {
                "id": "str_001",
                "question": "How many products?",
                "ground_truth_intent": "SQL",
            },
            output,
        )

        self.assertEqual(result["sql"]["result_f1"], 1.0)
        self.assertEqual(result["automatic_score"], 1.0)

    def test_missing_sql_branch_does_not_match_empty_reference(self) -> None:
        scorer = AutomaticScorer()
        template = scorer.case_templates["str_010"]
        scorer._reference_rows[template] = []

        result = scorer.score(
            {
                "id": "str_010",
                "question": "Which products have never been ordered?",
                "ground_truth_intent": "SQL",
            },
            {"intent": "SQL", "answer": "I do not know.", "sources": []},
        )

        self.assertEqual(result["sql"]["result_f1"], 0.0)
        self.assertFalse(result["sql"]["execution_success"])
        self.assertFalse(result["automatic_pass"])

    def test_rag_score_rewards_expected_source_and_topic(self) -> None:
        scorer = AutomaticScorer()
        output = {
            "intent": "RAG",
            "rag_success": True,
            "answer": "FPT trình bày chiến lược phát triển và kế hoạch kinh doanh.",
            "sources": ["DOC:fpt_2024.pdf#p40"],
            "raw": {
                "hybrid": {
                    "rag_result": {
                        "citations": ["fpt_2024.pdf#p40"],
                        "context_passages": [
                            "FPT trình bày chiến lược phát triển và kế hoạch kinh doanh."
                        ],
                    }
                }
            },
        }

        result = scorer.score(
            {
                "id": "unstr_001",
                "question": "FPT có chiến lược phát triển nào?",
                "ground_truth_intent": "RAG",
                "ground_truth_answer": "Tìm trong báo cáo FPT - chiến lược kinh doanh, kế hoạch phát triển",
            },
            output,
        )

        self.assertEqual(result["rag"]["source_match"], 1.0)
        self.assertGreaterEqual(result["rag"]["topic_recall"], 0.8)
        self.assertTrue(result["automatic_pass"])


if __name__ == "__main__":
    unittest.main()
