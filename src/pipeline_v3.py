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
from src.runtime.config import RuntimeConfig
from src.runtime.fallbacks import INSUFFICIENT_EVIDENCE, standardized_failure_response
from src.runtime.schemas import FailureLog, StandardResponse, now_iso
from src.runtime.timeouts import StageTimeoutError, run_with_timeout
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
            rule_trace = rule_result.to_dict()
            return {
                "intent": "HYBRID",
                "confidence": max(0.8, rule_result.confidence),
                "reason": "Both document and structured-data signals detected.",
                "router_type_used": "adaptive_rule",
                "llm_called": False,
                "signals": rule_trace.get("signals", {}),
                "ambiguous": rule_trace.get("ambiguous", False),
                "matched_sql_keywords": rule_trace.get("matched_sql_keywords", []),
                "matched_rag_keywords": rule_trace.get("matched_rag_keywords", []),
                "router_trace": rule_trace,
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
                    "signals": rule_result.signals,
                    "ambiguous": rule_result.ambiguous,
                    "matched_sql_keywords": rule_result.matched_sql_keywords,
                    "matched_rag_keywords": rule_result.matched_rag_keywords,
                    "router_trace": rule_result.to_dict(),
                }
            except Exception as exc:
                return {
                    "intent": rule_result.intent,
                    "confidence": 0.5,
                    "reason": f"LLM router unavailable; fallback to rule router: {exc}",
                    "router_type_used": "rule_fallback",
                    "llm_called": False,
                    "signals": rule_result.signals,
                    "ambiguous": rule_result.ambiguous,
                    "matched_sql_keywords": rule_result.matched_sql_keywords,
                    "matched_rag_keywords": rule_result.matched_rag_keywords,
                    "router_trace": rule_result.to_dict(),
                }

        return {
            "intent": rule_result.intent,
            "confidence": rule_result.confidence,
            "reason": rule_result.reasoning,
            "router_type_used": "rule_router",
            "llm_called": False,
            "signals": rule_result.signals,
            "ambiguous": rule_result.ambiguous,
            "matched_sql_keywords": rule_result.matched_sql_keywords,
            "matched_rag_keywords": rule_result.matched_rag_keywords,
            "router_trace": rule_result.to_dict(),
        }


class QueryonixPipelineV3:
    def __init__(
        self,
        router: Optional[AdaptiveRouter] = None,
        rag_pipeline: Any = None,
        sql_pipeline: Optional[TextToSQLPipeline] = None,
        hybrid_handler: Optional[HybridQueryHandler] = None,
        max_total_latency_ms: int = 15000,
        runtime_config: Optional[RuntimeConfig] = None,
    ):
        self.runtime_config = runtime_config or RuntimeConfig.from_env()
        self.router = router or AdaptiveRouter(
            use_llm_for_ambiguous=self.runtime_config.use_llm_router,
            llm_timeout_seconds=max(1, self.runtime_config.timeouts.router_llm_ms // 1000),
        )
        self.sql_pipeline = sql_pipeline or LazyTextToSQLPipeline(max_result_rows=5)
        if not self.runtime_config.cache_enabled:
            if hasattr(self.sql_pipeline, "disable_cache"):
                self.sql_pipeline.disable_cache()
            else:
                self.sql_pipeline._sql_cache = {}
                self.sql_pipeline._save_sql_cache = lambda: None  # type: ignore[method-assign]
        self.hybrid_handler = hybrid_handler or HybridQueryHandler(
            rag_pipeline=rag_pipeline,
            sql_pipeline=self.sql_pipeline,
            timeout_per_module_ms=self.runtime_config.timeouts.hybrid_total_ms,
            merge_timeout_ms=self.runtime_config.timeouts.merge_llm_ms,
            runtime_config=self.runtime_config,
        )
        self.max_total_latency_ms = min(max_total_latency_ms, self.runtime_config.timeouts.end_to_end_ms)

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
        timings: Dict[str, Optional[float]] = {
            "router_latency_ms": None,
            "sql_latency_ms": None,
            "rag_latency_ms": None,
            "merge_latency_ms": None,
            "formatting_latency_ms": None,
        }
        failures: List[Dict[str, Any]] = []
        timeout_triggered = False
        fallback_used = False
        sql_success: Optional[bool] = None
        rag_success: Optional[bool] = None
        merge_used = False
        cache_hit: Optional[bool] = None

        def record_failure(
            failure_type: str,
            stage: str,
            exc: Exception | str,
            recovery_strategy: str,
            latency_impact_ms: float,
            resolved: bool = True,
        ) -> None:
            failures.append(
                FailureLog(
                    failure_type=failure_type,
                    stage=stage,
                    query=question,
                    exception=str(exc)[:500],
                    recovery_strategy=recovery_strategy,
                    latency_impact_ms=round(latency_impact_ms, 2),
                    resolved=resolved,
                    timestamp=now_iso(),
                ).to_dict()
            )

        router_started = time.perf_counter()
        try:
            route = run_with_timeout(
                lambda: self.router.classify(question),
                self.runtime_config.timeouts.router_llm_ms if self.runtime_config.use_llm_router else self.runtime_config.timeouts.deterministic_router_ms,
                "router",
            )
        except StageTimeoutError as exc:
            timeout_triggered = True
            fallback_used = True
            timings["router_latency_ms"] = round((time.perf_counter() - router_started) * 1000, 2)
            record_failure("timeout", "router", exc, "standardized_failure_response", timings["router_latency_ms"] or 0.0)
            response = standardized_failure_response(question, str(exc))
            response["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            response["timeout_triggered"] = True
            response["raw"]["failures"] = failures
            return response
        except Exception as exc:
            fallback_used = True
            timings["router_latency_ms"] = round((time.perf_counter() - router_started) * 1000, 2)
            record_failure("unexpected_exception", "router", exc, "standardized_failure_response", timings["router_latency_ms"] or 0.0)
            response = standardized_failure_response(question, str(exc))
            response["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            response["raw"]["failures"] = failures
            return response
        timings["router_latency_ms"] = round((time.perf_counter() - router_started) * 1000, 2)

        intent = route["intent"]
        forced_mode = (self.runtime_config.force_mode or "").upper()
        if forced_mode in {"SQL", "RAG", "HYBRID"}:
            intent = forced_mode
        if intent == "HYBRID" and not self.runtime_config.hybrid_enabled:
            intent = "SQL" if HybridQueryHandler._is_numeric_or_tabular(question) else "RAG"
            fallback_used = True
        confidence_threshold = self._confidence_threshold(intent)
        if float(route.get("confidence") or 0.0) < confidence_threshold:
            record_failure(
                "router_ambiguous",
                "router",
                f"low router confidence for {intent}: threshold={confidence_threshold}",
                "used_selected_or_forced_route",
                timings["router_latency_ms"] or 0.0,
            )

        llm_call_count = 1 if route.get("llm_called") else 0
        branches: List[str] = []

        if intent == "SQL":
            branch_started = time.perf_counter()
            try:
                sql_output = run_with_timeout(
                    lambda: self._run_sql(question),
                    self.runtime_config.timeouts.sql_execution_ms,
                    "sql_execution",
                )
            except StageTimeoutError as exc:
                timeout_triggered = True
                fallback_used = True
                sql_output = {"rows": [], "error": str(exc), "timings": {}}
                record_failure("timeout", "sql_execution", exc, "insufficient_evidence_response", self.runtime_config.timeouts.sql_execution_ms)
            except Exception as exc:
                fallback_used = True
                sql_output = {"rows": [], "error": str(exc), "timings": {}}
                record_failure("sql_execution_error", "sql_execution", exc, "insufficient_evidence_response", 0.0)
            timings["sql_latency_ms"] = round((time.perf_counter() - branch_started) * 1000, 2)
            branches.append("sql")
            sql_success = sql_output.get("error") is None
            cache_hit = (sql_output.get("timings") or {}).get("sql_cache_hit") == 1.0
            formatting_started = time.perf_counter()
            answer = self._format_sql_answer(sql_output) if sql_success else INSUFFICIENT_EVIDENCE
            timings["formatting_latency_ms"] = round((time.perf_counter() - formatting_started) * 1000, 2)
            sources = ["SQL:" + ",".join(sql_output.get("relevant_tables", []))] if sql_success else []
            raw = {"sql": sql_output, "router_trace": route}
        elif intent == "RAG":
            branch_started = time.perf_counter()
            try:
                rag_output = run_with_timeout(
                    lambda: self._run_rag(question),
                    self.runtime_config.timeouts.lightweight_rag_ms if self.runtime_config.lightweight_rag else self.runtime_config.timeouts.full_rag_ms,
                    "rag_retrieval",
                )
            except StageTimeoutError as exc:
                timeout_triggered = True
                fallback_used = True
                rag_output = {"answer": "", "sources": [], "error": str(exc)}
                record_failure("timeout", "rag_retrieval", exc, "insufficient_evidence_response", exc.timeout_ms)
            except Exception as exc:
                fallback_used = True
                rag_output = {"answer": "", "sources": [], "error": str(exc)}
                record_failure("unexpected_exception", "rag_retrieval", exc, "insufficient_evidence_response", 0.0)
            timings["rag_latency_ms"] = round((time.perf_counter() - branch_started) * 1000, 2)
            branches.append("rag")
            answer = rag_output.get("answer") or INSUFFICIENT_EVIDENCE
            sources = rag_output.get("sources", [])
            rag_success = bool(rag_output.get("answer")) and not rag_output.get("error")
            if not rag_success and not timeout_triggered:
                fallback_used = True
                record_failure("empty_retrieval", "rag_retrieval", rag_output.get("error") or "empty answer", "insufficient_evidence_response", timings["rag_latency_ms"] or 0.0)
            raw = {"rag": rag_output, "router_trace": route}
            llm_call_count += rag_output.get("llm_calls", 0)
        else:
            branch_started = time.perf_counter()
            try:
                hybrid_output = run_with_timeout(
                    lambda: self.hybrid_handler.query(question, router_intent="HYBRID"),
                    self.runtime_config.timeouts.hybrid_total_ms,
                    "hybrid_total",
                )
            except StageTimeoutError as exc:
                timeout_triggered = True
                fallback_used = True
                hybrid_output = {
                    "answer": INSUFFICIENT_EVIDENCE,
                    "sources": [],
                    "rag_result": {},
                    "sql_result": {},
                    "contribution": "both_fail",
                    "llm_calls": 0,
                    "error": str(exc),
                }
                record_failure("timeout", "hybrid_total", exc, "standardized_failure_response", exc.timeout_ms)
            except Exception as exc:
                fallback_used = True
                hybrid_output = {
                    "answer": INSUFFICIENT_EVIDENCE,
                    "sources": [],
                    "rag_result": {},
                    "sql_result": {},
                    "contribution": "both_fail",
                    "llm_calls": 0,
                    "error": str(exc),
                }
                record_failure("unexpected_exception", "hybrid_total", exc, "standardized_failure_response", 0.0)
            hybrid_latency = round((time.perf_counter() - branch_started) * 1000, 2)
            hybrid_timings = hybrid_output.get("timings") or {}
            timings["sql_latency_ms"] = _nested_timing(hybrid_output.get("sql_result"), "total_ms")
            timings["rag_latency_ms"] = _nested_timing(hybrid_output.get("rag_result"), "total_ms")
            timings["merge_latency_ms"] = hybrid_timings.get("merge_ms")
            if timings["sql_latency_ms"] is None and timings["rag_latency_ms"] is None:
                timings["sql_latency_ms"] = hybrid_latency if hybrid_output.get("sql_result") else None
                timings["rag_latency_ms"] = hybrid_latency if hybrid_output.get("rag_result") else None
            branches.extend(
                branch
                for branch in ["rag", "sql", "merge_llm"]
                if (
                    (branch == "rag" and hybrid_output.get("rag_result"))
                    or (branch == "sql" and hybrid_output.get("sql_result"))
                    or (branch == "merge_llm" and hybrid_output.get("llm_calls", 0) > 0)
                )
            )
            answer = hybrid_output.get("answer") or INSUFFICIENT_EVIDENCE
            sources = hybrid_output.get("sources", [])
            raw = {"hybrid": hybrid_output, "router_trace": route}
            llm_call_count += hybrid_output.get("llm_calls", 0)
            sql_result = hybrid_output.get("sql_result") or {}
            rag_result = hybrid_output.get("rag_result") or {}
            sql_success = None if not sql_result else sql_result.get("error") is None
            rag_success = None if not rag_result else bool(rag_result.get("context_passages") or rag_result.get("answer")) and not rag_result.get("error")
            cache_hit = (sql_result.get("timings") or {}).get("sql_cache_hit") == 1.0 if sql_result else None
            merge_used = hybrid_output.get("llm_calls", 0) > 0
            contribution = hybrid_output.get("contribution")
            fallback_used = fallback_used or contribution in {"merge_timeout", "both_fail"}
            if contribution == "merge_timeout":
                record_failure("merge_error", "hybrid_merge", "merge timed out or failed", "deterministic_merge_template", timings["merge_latency_ms"] or 0.0)
            if contribution in {"sql_only", "rag_only"}:
                fallback_used = True
                record_failure("hybrid_fallback", "hybrid_merge", f"contribution={contribution}", "returned_best_available_branch", hybrid_latency)
            if sql_result.get("error"):
                record_failure("sql_execution_error", "sql_execution", sql_result.get("error"), "branch_degraded", timings["sql_latency_ms"] or 0.0)
            if rag_result.get("error"):
                failure_type = "empty_retrieval" if not rag_result.get("context_passages") else "unexpected_exception"
                record_failure(failure_type, "rag_retrieval", rag_result.get("error"), "branch_degraded", timings["rag_latency_ms"] or 0.0)

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        if latency_ms > self.max_total_latency_ms:
            timeout_triggered = True
            fallback_used = True
            record_failure("timeout", "response_formatting", "end-to-end latency budget exceeded", "returned_best_available_answer", latency_ms)
        raw["failures"] = failures
        result = StandardResponse(
            answer=answer,
            sources=sources,
            intent=intent,
            latency_ms=latency_ms,
            confidence=route.get("confidence"),
            reason=route.get("reason", ""),
            router_type_used=route.get("router_type_used", "unknown"),
            llm_call_count=llm_call_count,
            branches=branches,
            fallback_used=fallback_used,
            timeout_triggered=timeout_triggered,
            sql_success=sql_success,
            rag_success=rag_success,
            merge_used=merge_used,
            answer_nonempty=bool(str(answer).strip()),
            cache_hit=cache_hit,
            timings=timings,
            raw=raw,
        )
        return result.to_dict()

    def _confidence_threshold(self, intent: str) -> float:
        if intent == "HYBRID":
            return self.runtime_config.hybrid_low_confidence_threshold
        if intent == "SQL":
            return self.runtime_config.sql_low_confidence_threshold
        if intent == "RAG":
            return self.runtime_config.routing_low_confidence_threshold
        return self.runtime_config.routing_low_confidence_threshold


def _nested_timing(payload: Any, key: str) -> Optional[float]:
    if not isinstance(payload, dict):
        return None
    timings = payload.get("timings")
    if isinstance(timings, dict) and timings.get(key) is not None:
        return timings.get(key)
    return None


class LazyTextToSQLPipeline:
    """Lazy proxy to avoid database/schema initialization during app startup."""

    def __init__(self, **kwargs: Any):
        self.kwargs = kwargs
        self._pipeline: Optional[TextToSQLPipeline] = None
        self._cache_enabled = True

    def _get(self) -> TextToSQLPipeline:
        if self._pipeline is None:
            self._pipeline = TextToSQLPipeline(**self.kwargs)
            if not self._cache_enabled:
                self._pipeline._sql_cache = {}
                self._pipeline._save_sql_cache = lambda: None  # type: ignore[method-assign]
        return self._pipeline

    def disable_cache(self) -> None:
        self._cache_enabled = False
        if self._pipeline is not None:
            self._pipeline._sql_cache = {}
            self._pipeline._save_sql_cache = lambda: None  # type: ignore[method-assign]

    def query(self, question: str, include_nl_answer: bool = True) -> Dict[str, Any]:
        return self._get().query(question, include_nl_answer=include_nl_answer)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)
