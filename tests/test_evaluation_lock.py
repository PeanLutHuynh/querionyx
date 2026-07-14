import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.evaluation.benchmark_runner import build_per_query_trace
from src.evaluation.evidence import build_experiment_manifest
from src.runtime.config import RuntimeConfig
from src.evaluation.scoring import score_case
from src.hybrid.hybrid_handler import HybridQueryHandler
from src.runtime.fallbacks import INSUFFICIENT_EVIDENCE


class TestEvaluationLock(unittest.TestCase):
    def test_runtime_mode_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            RuntimeConfig.from_dict({"execution_mode": "unknown"})
        config = RuntimeConfig.from_dict({"execution_mode": "evaluation_real"})
        self.assertEqual(config.execution_mode, "evaluation_real")
        with self.assertRaises(ValueError):
            RuntimeConfig.from_dict({"rag_retrieval_mode": "unknown"})

    def test_dirty_worktree_manifest_preserves_content_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            benchmark = Path(directory) / "benchmark.json"
            benchmark.write_text("{}", encoding="utf-8")
            with patch("src.evaluation.evidence.git_state", return_value=("abc123", True)):
                manifest = build_experiment_manifest(
                    run_id="test",
                    execution_mode="evaluation_real",
                    benchmark_path=benchmark,
                    config={"lightweight_rag": True},
                )
        self.assertEqual(manifest["evidence_type"], "measured")
        self.assertTrue(manifest["thesis_reporting_allowed"])
        self.assertTrue(manifest["git_dirty"])
        self.assertTrue(manifest["source_snapshot_sha256"])

    def test_clean_experiment_start_manifest_is_reportable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            benchmark = Path(directory) / "benchmark.json"
            benchmark.write_text("{}", encoding="utf-8")
            manifest = build_experiment_manifest(
                run_id="test",
                execution_mode="evaluation_real",
                benchmark_path=benchmark,
                config={"lightweight_rag": True},
                git_state_at_start=("abc123", False),
            )
        self.assertEqual(manifest["git_state_scope"], "experiment_start")
        self.assertTrue(manifest["thesis_reporting_allowed"])
        self.assertEqual(manifest["corpus_file"], "data/processed/chunks_recursive.json.gz")
        self.assertTrue(manifest["corpus_sha256"])
        self.assertTrue(manifest["configuration_payload_sha256"])
        self.assertTrue(manifest["source_snapshot_sha256"])

    def test_trace_contains_automatic_evaluation_schema(self) -> None:
        case = {"id": "q1", "question": "How many products?", "ground_truth_intent": "SQL"}
        output = {
            "answer": "77",
            "sources": [],
            "intent": "SQL",
            "confidence": 0.9,
            "latency_ms": 12.5,
            "branches": ["sql"],
            "raw": {"sql": {"sql_query": "SELECT COUNT(*) FROM products", "rows": [{"count": 77}]}},
            "timings": {},
        }
        score = {"passed": True}
        automatic_score = {
            "automatic_score": 1.0,
            "automatic_pass": True,
            "metric_scope": "reference_result_and_evidence_alignment",
        }
        trace = build_per_query_trace("q1", case, output, score, automatic_score=automatic_score)
        for field in [
            "query_text",
            "ground_truth_intent",
            "predicted_intent",
            "route_confidence",
            "retrieved_sources",
            "generated_sql",
            "sql_result",
            "answer",
            "latency_ms",
            "technical_pass",
            "automatic_evaluation",
        ]:
            self.assertIn(field, trace)
        self.assertEqual(trace["automatic_evaluation"]["automatic_score"], 1.0)


    def test_hybrid_technical_pass_requires_full_completion_or_valid_fallback(self) -> None:
        case = {"ground_truth_intent": "HYBRID"}
        rejected_partial = {
            "intent": "HYBRID",
            "answer": "insufficient evidence",
            "latency_ms": 10,
            "branches": ["sql", "rag"],
            "sql_success": True,
            "rag_success": False,
            "fallback_used": False,
        }
        valid_fallback = {**rejected_partial, "answer": "SQL result", "fallback_used": True}
        self.assertFalse(score_case(case, rejected_partial, 1000)["passed"])
        self.assertTrue(score_case(case, valid_fallback, 1000)["passed"])

    def test_no_fallback_variant_rejects_partial_hybrid_result(self) -> None:
        config = RuntimeConfig(allow_partial_hybrid_fallback=False)
        handler = HybridQueryHandler(runtime_config=config)

        async def fake_rag(_question: str):
            return {"context_passages": [], "error": "no document evidence", "timings": {}}

        async def fake_sql(_question: str):
            return {"rows": [{"count": 1}], "error": None, "timings": {}}

        handler._run_rag = fake_rag
        handler._run_sql = fake_sql
        result = asyncio.run(handler.aquery("Top products and risk", router_intent="HYBRID"))
        self.assertEqual(result["fallback_mode"], "PARTIAL_REJECTED")
        self.assertEqual(result["answer"], INSUFFICIENT_EVIDENCE)

    def test_dense_only_variant_uses_dense_retrieval(self) -> None:
        config = RuntimeConfig(lightweight_rag=False, rag_retrieval_mode="dense_only")
        handler = HybridQueryHandler(runtime_config=config)

        class FakeRag:
            called = False

            def retrieve_dense(self, _question: str, top_k: int):
                self.called = True
                return [{"text": "evidence", "source": "report.pdf", "page": 1, "distance": 0.1}]

        fake = FakeRag()
        handler._get_rag_pipeline = lambda: fake
        result = asyncio.run(handler._run_rag("strategy"))
        self.assertTrue(fake.called)
        self.assertEqual(result["citations"], ["report.pdf#p1"])


if __name__ == "__main__":
    unittest.main()
