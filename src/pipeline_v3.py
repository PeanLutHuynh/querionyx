"""Full Querionyx Pipeline V3.

Routes a user question to RAG, SQL, or HYBRID handling while keeping LLM calls
under a strict budget for weak local hardware and future Render deployment.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.hybrid.hybrid_handler import HybridQueryHandler
from src.router.rule_based_router import RuleBasedRouter
from src.sql.text_to_sql import TextToSQLPipeline


@dataclass
class PipelineV3Result:
    answer: str
    sources: List[str]
    intent: str
    latency_ms: float
    confidence: float
    reason: str
    router_type_used: str
    llm_call_count: int
    branches: List[str]
    raw: Dict[str, Any]


class AdaptiveRouter:
    """Lightweight adaptive router.

    The rule-based router is used first. LLM routing is reserved for obvious
    ambiguous/mixed questions to keep latency predictable.
    """

    def __init__(self, use_llm_for_ambiguous: bool = False, llm_timeout_seconds: int = 8):
        self.rule_router = RuleBasedRouter()
        self.use_llm_for_ambiguous = use_llm_for_ambiguous
        self.llm_timeout_seconds = llm_timeout_seconds
        self._llm_router = None

    @staticmethod
    def _signals(question: str) -> Dict[str, bool]:
        q = question.lower()
        rag_terms = [
            "báo cáo",
            "annual report",
            "pdf",
            "chiến lược",
            "chính sách",
            "rủi ro",
            "kế hoạch",
            "mục tiêu",
            "strategy",
            "policy",
            "risk",
        ]
        sql_terms = [
            "top",
            "count",
            "average",
            "sum",
            "total",
            "list",
            "bao nhiêu",
            "tổng",
            "trung bình",
            "liệt kê",
            "doanh thu",
            "orders",
            "products",
            "customers",
        ]
        return {
            "rag": any(term in q for term in rag_terms),
            "sql": any(term in q for term in sql_terms),
            "conjunction": " và " in q or " and " in q,
        }

    def _get_llm_router(self) -> Any:
        if self._llm_router is None:
            from src.router.llm_router import LLMRouterV2

            self._llm_router = LLMRouterV2(llm_timeout_seconds=self.llm_timeout_seconds)
        return self._llm_router

    def classify(self, question: str) -> Dict[str, Any]:
        signals = self._signals(question)
        rule_result = self.rule_router.classify(question)

        if signals["rag"] and signals["sql"]:
            return {
                "intent": "HYBRID",
                "confidence": 0.8,
                "reason": "Both document and structured-data signals detected.",
                "router_type_used": "adaptive_rule",
                "llm_called": False,
            }

        if self.use_llm_for_ambiguous and signals["conjunction"]:
            try:
                llm_result = self._get_llm_router().classify(question)
                return {
                    "intent": llm_result.intent,
                    "confidence": llm_result.confidence,
                    "reason": llm_result.reasoning,
                    "router_type_used": "llm_router",
                    "llm_called": llm_result.llm_called,
                }
            except Exception as exc:
                return {
                    "intent": rule_result.intent,
                    "confidence": 0.5,
                    "reason": f"LLM router unavailable; fallback to rule router: {exc}",
                    "router_type_used": "rule_fallback",
                    "llm_called": False,
                }

        return {
            "intent": rule_result.intent,
            "confidence": rule_result.confidence,
            "reason": rule_result.reasoning,
            "router_type_used": "rule_router",
            "llm_called": False,
        }


class QueryonixPipelineV3:
    def __init__(
        self,
        router: Optional[AdaptiveRouter] = None,
        rag_pipeline: Any = None,
        sql_pipeline: Optional[TextToSQLPipeline] = None,
        hybrid_handler: Optional[HybridQueryHandler] = None,
        max_total_latency_ms: int = 15000,
    ):
        self.router = router or AdaptiveRouter(use_llm_for_ambiguous=False)
        self.sql_pipeline = sql_pipeline or TextToSQLPipeline(max_result_rows=5)
        self.hybrid_handler = hybrid_handler or HybridQueryHandler(
            rag_pipeline=rag_pipeline,
            sql_pipeline=self.sql_pipeline,
        )
        self.max_total_latency_ms = max_total_latency_ms

    @staticmethod
    def _format_sql_answer(sql_output: Dict[str, Any]) -> str:
        rows = sql_output.get("rows") or []
        if sql_output.get("error"):
            return f"Không truy vấn được cơ sở dữ liệu: {sql_output['error']}"
        if not rows:
            return "Không có kết quả phù hợp từ cơ sở dữ liệu."
        columns = list(rows[0].keys())
        lines = [
            "Kết quả từ cơ sở dữ liệu:",
            "",
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
        ]
        for row in rows[:5]:
            lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
        return "\n".join(lines)

    def _run_sql(self, question: str) -> Dict[str, Any]:
        return self.sql_pipeline.query(question, include_nl_answer=False)

    def _run_rag(self, question: str) -> Dict[str, Any]:
        return self.hybrid_handler.query(question, router_intent="RAG")

    def query(self, question: str) -> Dict[str, Any]:
        started = time.perf_counter()
        route = self.router.classify(question)
        intent = route["intent"]
        llm_call_count = 1 if route.get("llm_called") else 0
        branches: List[str] = []

        if intent == "SQL":
            sql_output = self._run_sql(question)
            branches.append("sql")
            answer = self._format_sql_answer(sql_output)
            sources = ["SQL:" + ",".join(sql_output.get("relevant_tables", []))]
            raw = {"sql": sql_output}
        elif intent == "RAG":
            rag_output = self._run_rag(question)
            branches.append("rag")
            answer = rag_output.get("answer") or "Tôi không có đủ thông tin để trả lời câu hỏi này."
            sources = rag_output.get("sources", [])
            raw = {"rag": rag_output}
            llm_call_count += rag_output.get("llm_calls", 0)
        else:
            hybrid_output = self.hybrid_handler.query(question, router_intent="HYBRID")
            branches.extend(
                branch
                for branch in ["rag", "sql", "merge_llm"]
                if (
                    (branch == "rag" and hybrid_output.get("rag_result"))
                    or (branch == "sql" and hybrid_output.get("sql_result"))
                    or (branch == "merge_llm" and hybrid_output.get("llm_calls", 0) > 0)
                )
            )
            answer = hybrid_output.get("answer") or "Tôi không có đủ thông tin để trả lời câu hỏi này."
            sources = hybrid_output.get("sources", [])
            raw = {"hybrid": hybrid_output}
            llm_call_count += hybrid_output.get("llm_calls", 0)

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        result = PipelineV3Result(
            answer=answer,
            sources=sources,
            intent=intent,
            latency_ms=latency_ms,
            confidence=route["confidence"],
            reason=route["reason"],
            router_type_used=route["router_type_used"],
            llm_call_count=llm_call_count,
            branches=branches,
            raw=raw,
        )
        return result.__dict__
