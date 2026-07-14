import unittest

from scripts.audit_no_ollama_readiness import audit


class TestNoOllamaAudit(unittest.TestCase):
    def test_route_mismatch_is_not_counted_as_safe(self) -> None:
        report = audit(
            [
                {
                    "id": "mismatch",
                    "question": "Top 5 products by quantity sold",
                    "ground_truth_intent": "RAG",
                }
            ]
        )

        self.assertEqual(report["summary"]["route_accuracy"], 0.0)
        self.assertEqual(report["summary"]["no_ollama_safe_rate"], 0.0)
        self.assertEqual(report["summary"]["issues"], {"route_mismatch": 1})

    def test_report_question_without_company_signal_is_not_safe(self) -> None:
        report = audit(
            [
                {
                    "id": "missing-company",
                    "question": "Tóm tắt rủi ro trong báo cáo năm.",
                    "ground_truth_intent": "RAG",
                    "source_hint": "annual_reports",
                }
            ]
        )

        self.assertEqual(report["summary"]["route_accuracy"], 1.0)
        self.assertEqual(report["summary"]["no_ollama_safe_rate"], 0.0)
        self.assertEqual(
            report["summary"]["issues"],
            {"rag_missing_company_signal": 1},
        )


if __name__ == "__main__":
    unittest.main()
