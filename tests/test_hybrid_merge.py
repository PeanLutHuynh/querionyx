import asyncio
import unittest

from src.hybrid.hybrid_handler import HybridQueryHandler
from src.runtime.config import RuntimeConfig


class TestHybridTemplateMerge(unittest.TestCase):
    def test_no_ollama_hybrid_keeps_both_successful_branches(self) -> None:
        config = RuntimeConfig(
            execution_mode="demo_no_ollama",
            lightweight_rag=True,
            merge_llm_enabled=False,
        )
        handler = HybridQueryHandler(runtime_config=config)

        async def fake_rag(question: str):
            return {
                "context_passages": ["Masan describes an integrated supply chain."],
                "citations": ["masan_2024.pdf#page=42"],
                "answer": "Masan describes an integrated supply chain.",
                "score": 0.9,
                "error": None,
                "timings": {"total_ms": 12.0},
            }

        async def fake_sql(question: str):
            return {
                "sql_query": "SELECT product_name FROM products LIMIT 1;",
                "rows": [{"product_name": "Camembert Pierrot"}],
                "error": None,
                "timings": {"total_ms": 8.0},
            }

        handler._run_rag = fake_rag  # type: ignore[method-assign]
        handler._run_sql = fake_sql  # type: ignore[method-assign]

        result = asyncio.run(
            handler.aquery(
                "Kế hoạch tăng trưởng của FPT là gì và nhân viên nào xử lý nhiều đơn hàng nhất?",
                router_intent="HYBRID",
            )
        )

        self.assertEqual(result["contribution"], "merged_template")
        self.assertEqual(result["fallback_mode"], "NONE")
        self.assertEqual(result["llm_calls"], 0)
        self.assertIn("Camembert Pierrot", result["answer"])
        self.assertIn("integrated supply chain", result["answer"])
        self.assertEqual(
            result["sources"],
            ["SQL", "DOC:masan_2024.pdf#page=42"],
        )

    def test_heavy_hybrid_rrf_score_is_normalized_to_confidence(self) -> None:
        class FakeRag:
            rrf_k = 60.0

            @staticmethod
            def retrieve_hybrid(_question: str, final_top_k: int):
                return [
                    {
                        "text": "FPT strategy evidence",
                        "source": "fpt_2024.pdf",
                        "page": 10,
                        "rrf_score": 2.0 / 61.0,
                    }
                ][:final_top_k]

        config = RuntimeConfig(lightweight_rag=False, rag_retrieval_mode="hybrid")
        handler = HybridQueryHandler(rag_pipeline=FakeRag(), runtime_config=config)
        result = asyncio.run(handler._run_rag("FPT strategy"))

        self.assertAlmostEqual(result["score"], 1.0)
        self.assertIsNone(result["error"])


if __name__ == "__main__":
    unittest.main()
