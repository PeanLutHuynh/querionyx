"""Production orchestration wrapper for the frozen Querionyx V3 pipeline."""

from __future__ import annotations

import asyncio
import copy
import difflib
import hashlib
import json
import os
import pickle
import re
import time
import uuid
from collections import Counter, OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

from src.pipeline_v3 import QueryonixPipelineV3
from src.runtime.config import RuntimeConfig
from src.runtime.fallbacks import INSUFFICIENT_EVIDENCE
from src.runtime.logging import append_jsonl
from src.runtime.metrics import latency_summary, process_resource_snapshot
from src.runtime.schemas import now_iso


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUERY_LOG_DIR = PROJECT_ROOT / "metrics" / "query_logs"
FAILURE_LOG_DIR = PROJECT_ROOT / "metrics" / "failure_logs"
UPLOAD_DIR = PROJECT_ROOT / "data" / "raw" / "uploads"
CHUNKS_FILE = PROJECT_ROOT / "data" / "processed" / "chunks_recursive.pkl"
CHROMA_DB_PATH = PROJECT_ROOT / "data" / "chroma_db"


@dataclass
class CacheEntry:
    value: Dict[str, Any]
    created_at: float
    normalized_question: str
    intent: str
    router_type: str
    tokens: Set[str]


@dataclass
class CacheLookupResult:
    value: Dict[str, Any]
    matched_by: str
    score: float


class TTLResponseCache:
    """Small LRU + TTL cache for repeat-query speedups."""

    def __init__(self, max_size: int = 256, ttl_seconds: int = 1800, fuzzy_threshold: float = 0.92, semantic_threshold: float = 0.82):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.fuzzy_threshold = fuzzy_threshold
        self.semantic_threshold = semantic_threshold
        self._items: OrderedDict[str, CacheEntry] = OrderedDict()
        self._aliases: Dict[str, str] = {}
        self._lock = Lock()
        self.hits = 0
        self.misses = 0
        self.hit_by_intent: Counter[str] = Counter()
        self.miss_by_intent: Counter[str] = Counter()
        self.hit_by_matcher: Counter[str] = Counter()

    @staticmethod
    def normalize(question: str) -> str:
        return re.sub(r"\s+", " ", question.strip().lower())

    @classmethod
    def tokens(cls, question: str) -> Set[str]:
        return {token for token in re.split(r"\W+", cls.normalize(question)) if len(token) >= 2}

    @classmethod
    def alias_key(cls, question: str, intent: Optional[str] = None) -> str:
        payload = cls.normalize(question)
        if intent:
            payload = f"{payload}|{intent}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def cache_key(cls, question: str, intent: str, router_type: str) -> str:
        normalized = cls.normalize(question)
        payload = f"{normalized}|{intent}|{router_type}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_by_question(self, question: str, intent: Optional[str] = None) -> Optional[CacheLookupResult]:
        normalized = self.normalize(question)
        alias = self.alias_key(question, intent=intent)
        generic_alias = self.alias_key(question)
        requested_tokens = self.tokens(question)
        with self._lock:
            exact = self._lookup_alias(alias) or self._lookup_alias(generic_alias)
            if exact is not None:
                self._record_hit(exact.intent, "exact")
                return CacheLookupResult(value=copy.deepcopy(exact.value), matched_by="exact", score=1.0)

            best_entry: Optional[CacheEntry] = None
            best_mode = ""
            best_score = 0.0
            for key, entry in list(self._items.items()):
                if self._expired(entry):
                    self._items.pop(key, None)
                    continue
                if intent and entry.intent != intent:
                    continue
                if entry.normalized_question == normalized:
                    best_entry = entry
                    best_mode = "normalized"
                    best_score = 1.0
                    break
                fuzzy = difflib.SequenceMatcher(None, normalized, entry.normalized_question).ratio()
                semantic = _jaccard(requested_tokens, entry.tokens)
                if fuzzy >= self.fuzzy_threshold and fuzzy > best_score:
                    best_entry = entry
                    best_mode = "fuzzy"
                    best_score = fuzzy
                if semantic >= self.semantic_threshold and semantic > best_score:
                    best_entry = entry
                    best_mode = "semantic"
                    best_score = semantic

            if best_entry is None:
                self.misses += 1
                self.miss_by_intent[str(intent or "UNKNOWN")] += 1
                return None
            self.hits += 1
            self.hit_by_intent[best_entry.intent] += 1
            self.hit_by_matcher[best_mode] += 1
            return CacheLookupResult(value=copy.deepcopy(best_entry.value), matched_by=best_mode, score=round(best_score, 4))

    def set(self, question: str, intent: str, router_type: str, value: Dict[str, Any]) -> str:
        key = self.cache_key(question, intent, router_type)
        alias = self.alias_key(question, intent=intent)
        generic_alias = self.alias_key(question)
        normalized = self.normalize(question)
        with self._lock:
            self._items[key] = CacheEntry(
                value=copy.deepcopy(value),
                created_at=time.time(),
                normalized_question=normalized,
                intent=intent,
                router_type=router_type,
                tokens=self.tokens(question),
            )
            self._items.move_to_end(key)
            self._aliases[alias] = key
            self._aliases[generic_alias] = key
            while len(self._items) > self.max_size:
                old_key, _ = self._items.popitem(last=False)
                stale_aliases = [alias_key for alias_key, item_key in self._aliases.items() if item_key == old_key]
                for alias_key in stale_aliases:
                    self._aliases.pop(alias_key, None)
        return key

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        intents = sorted(set(self.hit_by_intent) | set(self.miss_by_intent))
        hit_rate_by_intent = {}
        for intent in intents:
            hits = self.hit_by_intent.get(intent, 0)
            misses = self.miss_by_intent.get(intent, 0)
            denom = hits + misses
            hit_rate_by_intent[intent] = round(hits / denom, 4) if denom else 0.0
        return {
            "size": len(self._items),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
            "hit_by_intent": dict(self.hit_by_intent),
            "miss_by_intent": dict(self.miss_by_intent),
            "hit_rate_by_intent": hit_rate_by_intent,
            "hit_by_matcher": dict(self.hit_by_matcher),
        }

    def _expired(self, entry: CacheEntry) -> bool:
        return (time.time() - entry.created_at) > self.ttl_seconds

    def _lookup_alias(self, alias: str) -> Optional[CacheEntry]:
        key = self._aliases.get(alias)
        if not key:
            return None
        entry = self._items.get(key)
        if entry is None or self._expired(entry):
            self._items.pop(key, None)
            self._aliases.pop(alias, None)
            return None
        self._items.move_to_end(key)
        return entry

    def _record_hit(self, intent: str, mode: str) -> None:
        self.hits += 1
        self.hit_by_intent[intent] += 1
        self.hit_by_matcher[mode] += 1


class ServiceMetrics:
    def __init__(self) -> None:
        self.latencies: List[float] = []
        self.timeout_count = 0
        self.fallback_count = 0
        self.request_count = 0
        self.intent_counts: Counter[str] = Counter()
        self.branch_counts: Counter[str] = Counter()
        self.router_accuracy: Optional[float] = None
        self.misrouting_rate: Optional[float] = None
        self.confidence_calibration_error: Optional[float] = None
        self.router_confusion_matrix: Dict[str, Dict[str, int]] = {}
        self.router_per_class: Dict[str, Dict[str, float]] = {}
        self.router_error_breakdown: Dict[str, int] = {}
        self.hybrid_modes: Counter[str] = Counter()
        self.hybrid_parallel_efficiencies: List[float] = []
        self.hybrid_parallel_gains: List[float] = []
        self.hybrid_bottlenecks: Counter[str] = Counter()
        self.failure_taxonomy: Counter[str] = Counter()
        self._lock = Lock()

    def record(self, response: Dict[str, Any]) -> None:
        with self._lock:
            self.request_count += 1
            if response.get("latency_ms") is not None:
                self.latencies.append(float(response["latency_ms"]))
            if response.get("timeout_triggered"):
                self.timeout_count += 1
            if response.get("fallback_used"):
                self.fallback_count += 1
            self.intent_counts[str(response.get("intent") or "UNKNOWN")] += 1
            for branch in response.get("branches") or []:
                self.branch_counts[str(branch)] += 1
            hybrid_mode = (response.get("raw") or {}).get("hybrid", {}).get("contribution")
            if hybrid_mode:
                self.hybrid_modes[str(hybrid_mode)] += 1
            hybrid_metrics = (response.get("raw") or {}).get("hybrid_metrics") or {}
            if hybrid_metrics.get("parallel_efficiency") is not None:
                self.hybrid_parallel_efficiencies.append(float(hybrid_metrics["parallel_efficiency"]))
            if hybrid_metrics.get("parallel_gain_ms") is not None:
                self.hybrid_parallel_gains.append(float(hybrid_metrics["parallel_gain_ms"]))
            if hybrid_metrics.get("bottleneck"):
                self.hybrid_bottlenecks[str(hybrid_metrics["bottleneck"])] += 1
            for failure in ((response.get("raw") or {}).get("failures") or []):
                if failure.get("failure_type"):
                    self.failure_taxonomy[str(failure["failure_type"])] += 1

    def update_router_stress(self, summary: Dict[str, Any]) -> None:
        self.router_accuracy = summary.get("router_accuracy")
        self.misrouting_rate = summary.get("misrouting_rate")
        self.confidence_calibration_error = summary.get("confidence_calibration_error")
        self.router_confusion_matrix = summary.get("confusion_matrix") or {}
        self.router_per_class = summary.get("per_class") or {}
        self.router_error_breakdown = summary.get("misrouting_breakdown") or {}

    def snapshot(self, cache_stats: Dict[str, Any]) -> Dict[str, Any]:
        latency = latency_summary(self.latencies)
        return {
            "request_count": self.request_count,
            "latency": {
                "p50_ms": latency["p50"],
                "p95_ms": latency["p95"],
                "p99_ms": latency["p99"],
                "avg_ms": latency["avg"],
            },
            "cache": cache_stats,
            "cache_hit_rate": cache_stats["hit_rate"],
            "timeout_rate": round(self.timeout_count / self.request_count, 4) if self.request_count else 0.0,
            "fallback_rate": round(self.fallback_count / self.request_count, 4) if self.request_count else 0.0,
            "intent_counts": dict(self.intent_counts),
            "hybrid_breakdown": dict(self.branch_counts),
            "hybrid_modes": dict(self.hybrid_modes),
            "hybrid_parallel_efficiency": _avg(self.hybrid_parallel_efficiencies),
            "hybrid_parallel_gain_ms": _avg(self.hybrid_parallel_gains),
            "hybrid_bottlenecks": dict(self.hybrid_bottlenecks),
            "router_accuracy": self.router_accuracy,
            "misrouting_rate": self.misrouting_rate,
            "confidence_calibration_error": self.confidence_calibration_error,
            "router_confusion_matrix": self.router_confusion_matrix,
            "router_per_class": self.router_per_class,
            "router_error_breakdown": self.router_error_breakdown,
            "failure_taxonomy": dict(self.failure_taxonomy),
            "resource_snapshot": process_resource_snapshot(),
        }


class QueryService:
    """External production wrapper. Does not modify or bypass pipeline logic."""

    def __init__(self, runtime_config: Optional[RuntimeConfig] = None):
        load_dotenv(PROJECT_ROOT / ".env")
        self.runtime_config = runtime_config or RuntimeConfig.from_env()
        self.pipeline = QueryonixPipelineV3(runtime_config=self.runtime_config)
        self.cache = TTLResponseCache(
            max_size=int(os.getenv("QUERIONYX_RESPONSE_CACHE_SIZE", "256")),
            ttl_seconds=int(os.getenv("QUERIONYX_RESPONSE_CACHE_TTL", "1800")),
            fuzzy_threshold=float(os.getenv("QUERIONYX_CACHE_FUZZY_THRESHOLD", "0.92")),
            semantic_threshold=float(os.getenv("QUERIONYX_CACHE_SEMANTIC_THRESHOLD", "0.82")),
        )
        self.metrics = ServiceMetrics()
        self.pipeline_version = "querionyx-v3-week7"
        self._warm_cache()

    async def query(self, question: str, debug: bool = False) -> Dict[str, Any]:
        trace_id = str(uuid.uuid4())
        started = time.perf_counter()
        route_started = time.perf_counter()
        route_hint = await asyncio.to_thread(self.pipeline.router.classify, question)
        route_hint_ms = round((time.perf_counter() - route_started) * 1000, 2)
        cached = self.cache.get_by_question(question, intent=str(route_hint.get("intent") or "UNKNOWN"))
        if cached is not None:
            response = self._prepare_cached_response(cached, trace_id, started, debug, route_hint_ms=route_hint_ms)
            self.metrics.record(response)
            self._log_request(question, response)
            return response

        output = await self._execute(question, route_hint=route_hint, route_hint_ms=route_hint_ms)
        response = self._serialize_response(output, trace_id, cache_hit=False, debug=debug)
        self.cache.set(question, str(response.get("intent") or "UNKNOWN"), str(response.get("router_type_used") or "unknown"), response)
        self.metrics.record(response)
        self._log_request(question, response)
        return response

    async def stream_query(self, question: str, debug: bool = False):
        started = time.perf_counter()
        trace_id = str(uuid.uuid4())
        route_started = time.perf_counter()
        route_hint = await asyncio.to_thread(self.pipeline.router.classify, question)
        route_hint_ms = round((time.perf_counter() - route_started) * 1000, 2)
        cached = self.cache.get_by_question(question, intent=str(route_hint.get("intent") or "UNKNOWN"))
        if cached is not None:
            response = self._prepare_cached_response(cached, trace_id, started, debug, route_hint_ms=route_hint_ms)
            self.metrics.record(response)
            self._log_request(question, response)
            yield self._sse("meta", {"trace_id": trace_id, "cache_hit": True, "cache_match": cached.matched_by, "cache_score": cached.score})
            yield self._sse("result", response)
            return

        yield self._sse("meta", {"trace_id": trace_id, "cache_hit": False})
        output = await self._execute(question, route_hint=route_hint, route_hint_ms=route_hint_ms)
        response = self._serialize_response(output, trace_id, cache_hit=False, debug=debug)
        self.cache.set(question, str(response.get("intent") or "UNKNOWN"), str(response.get("router_type_used") or "unknown"), response)
        self.metrics.record(response)
        self._log_request(question, response)
        yield self._sse("result", response)

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "pipeline_version": self.pipeline_version,
            "cache": self.cache.stats(),
            "avg_latency": self.metrics.snapshot(self.cache.stats())["latency"]["avg_ms"],
            "db_status": self._db_status(),
            "timestamp": now_iso(),
        }

    def metrics_snapshot(self) -> Dict[str, Any]:
        self._load_router_summary_if_available()
        return self.metrics.snapshot(self.cache.stats())

    async def upload_pdf(self, filename: str, content: bytes, embed: bool = False) -> Dict[str, Any]:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = Path(filename).name
        output_path = UPLOAD_DIR / safe_name
        output_path.write_bytes(content)
        chunks = await asyncio.to_thread(self._parse_pdf_to_chunks, output_path)
        await asyncio.to_thread(self._append_chunks, chunks)
        chroma_inserted = 0
        if embed or os.getenv("ENABLE_UPLOAD_EMBEDDING", "0") == "1":
            chroma_inserted = await asyncio.to_thread(self._insert_chroma, chunks)
        return {
            "filename": safe_name,
            "saved_to": str(output_path),
            "chunks_created": len(chunks),
            "chroma_inserted": chroma_inserted,
            "embedding_enabled": bool(chroma_inserted),
        }

    def _prepare_cached_response(self, cached: CacheLookupResult, trace_id: str, started: float, debug: bool, route_hint_ms: float) -> Dict[str, Any]:
        response = copy.deepcopy(cached.value)
        response["cache_hit"] = True
        response["trace_id"] = trace_id
        response["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        response.setdefault("timings", {})
        response["timings"]["router_ms"] = route_hint_ms
        response["timings"]["cache_ms"] = response["latency_ms"]
        response["timings"]["cache_match_score"] = cached.score
        response["timings"]["cache_match_type"] = cached.matched_by
        if not debug:
            response.pop("raw", None)
        return response

    async def _execute(self, question: str, route_hint: Optional[Dict[str, Any]] = None, route_hint_ms: Optional[float] = None) -> Dict[str, Any]:
        route_started = time.perf_counter()
        route = route_hint or await asyncio.to_thread(self.pipeline.router.classify, question)
        route_ms = round((time.perf_counter() - route_started) * 1000, 2) if route_hint is None else (route_hint_ms or 0.0)
        intent = str(route.get("intent") or "RAG").upper()
        forced_mode = (self.runtime_config.force_mode or "").upper()
        if forced_mode in {"SQL", "RAG", "HYBRID"}:
            intent = forced_mode

        if intent == "SQL":
            output = await asyncio.to_thread(self.pipeline.query, question)
            output.setdefault("timings", {})["router_latency_ms"] = route_ms
            return output

        if intent == "RAG":
            output = await asyncio.to_thread(self.pipeline.query, question)
            output.setdefault("timings", {})["router_latency_ms"] = route_ms
            return output

        output = await self._execute_hybrid(question, route, route_ms)
        return output

    async def _execute_hybrid(self, question: str, route: Dict[str, Any], route_ms: float) -> Dict[str, Any]:
        handler = self.pipeline.hybrid_handler
        total_started = time.perf_counter()
        rag_task = asyncio.create_task(handler._run_rag(question))
        sql_task = asyncio.create_task(handler._run_sql(question))

        sql_result: Dict[str, Any] = {}
        rag_result: Dict[str, Any] = {}
        merge_ms: Optional[float] = None
        merge_used = False
        llm_calls = 0

        if float(route.get("confidence") or 0.0) > 0.9 and handler._sql_fast_planner_can_handle(question):
            done, pending = await asyncio.wait({sql_task, rag_task}, return_when=asyncio.FIRST_COMPLETED)
            if sql_task in done:
                sql_result = sql_task.result()
                sql_ok = not sql_result.get("error") and bool(sql_result.get("rows"))
                if sql_ok:
                    rag_task.cancel()
                    try:
                        await rag_task
                    except BaseException:
                        pass
                    rag_result = {"context_passages": [], "citations": [], "answer": "", "error": "cancelled_due_to_sql_fast_path", "timings": {}}
                else:
                    if not rag_task.done():
                        rag_result = await rag_task
            else:
                rag_result = rag_task.result()
                sql_result = await sql_task
        else:
            rag_result, sql_result = await asyncio.gather(rag_task, sql_task)

        sql_ok = not sql_result.get("error") and bool(sql_result.get("rows"))
        rag_ok = not rag_result.get("error") and bool(rag_result.get("context_passages"))
        rag_low = rag_result.get("score") is not None and float(rag_result["score"]) < 0.4

        sources: List[str] = []
        contribution = "both_fail"
        if sql_ok and (not rag_ok or rag_low):
            answer = handler._deterministic_sql_answer(question, sql_result)
            sources = ["SQL"]
            contribution = "sql_only"
        elif rag_ok and not sql_ok:
            answer = handler._deterministic_rag_answer(
                rag_result,
                note="Khong truy van duoc co so du lieu cho cau hoi nay.",
            )
            sources = [f"DOC:{c}" for c in rag_result.get("citations", [])]
            contribution = "rag_only"
        elif sql_ok and rag_ok:
            sources = ["SQL"] + [f"DOC:{c}" for c in rag_result.get("citations", [])]
            if handler._should_merge_with_llm(question, rag_result, sql_result):
                merge_started = time.perf_counter()
                try:
                    answer = await handler._merge_with_llm(question, rag_result, sql_result)
                    merge_ms = round((time.perf_counter() - merge_started) * 1000, 2)
                    merge_used = True
                    llm_calls = 1
                    contribution = "merged_llm"
                except Exception:
                    merge_ms = round((time.perf_counter() - merge_started) * 1000, 2)
                    answer = handler._deterministic_sql_answer(question, sql_result) + "\n\n" + handler._deterministic_rag_answer(rag_result)
                    contribution = "merge_timeout"
            else:
                answer = handler._deterministic_sql_answer(question, sql_result)
                contribution = "sql_only"
        else:
            answer = INSUFFICIENT_EVIDENCE

        branches = []
        if rag_result:
            branches.append("rag")
        if sql_result:
            branches.append("sql")
        if merge_used:
            branches.append("merge_llm")

        latency_ms = round((time.perf_counter() - total_started) * 1000, 2)
        fallback_used = contribution in {"rag_only", "merge_timeout", "both_fail"}
        fallback_used = fallback_used or (sql_ok and not rag_ok)
        sql_ms = _timing(sql_result, "total_ms")
        rag_ms = _timing(rag_result, "total_ms")
        parallel_efficiency = _parallel_efficiency(sql_ms, rag_ms)
        parallel_gain_ms = _parallel_gain(sql_ms, rag_ms, latency_ms)
        bottleneck = _hybrid_bottleneck(sql_ms, rag_ms)
        timeout_triggered = False
        return {
            "answer": answer,
            "sources": sources,
            "intent": "HYBRID",
            "latency_ms": latency_ms,
            "confidence": route.get("confidence"),
            "reason": route.get("reason", ""),
            "router_type_used": route.get("router_type_used", "adaptive_rule"),
            "llm_call_count": llm_calls,
            "branches": branches,
            "fallback_used": fallback_used,
            "timeout_triggered": timeout_triggered,
            "sql_success": sql_ok if sql_result else None,
            "rag_success": rag_ok if rag_result else None,
            "merge_used": merge_used,
            "answer_nonempty": bool(str(answer).strip()),
            "cache_hit": False,
            "timings": {
                "router_latency_ms": route_ms,
                "sql_latency_ms": sql_ms,
                "rag_latency_ms": rag_ms,
                "merge_latency_ms": merge_ms,
                "formatting_latency_ms": 0.0,
            },
            "raw": {
                "hybrid": {
                    "answer": answer,
                    "sources": sources,
                    "rag_result": rag_result,
                    "sql_result": sql_result,
                    "contribution": contribution,
                    "llm_calls": llm_calls,
                    "timings": {
                        "total_ms": latency_ms,
                        "merge_ms": merge_ms,
                    },
                },
                "hybrid_metrics": {
                    "sql_ms": sql_ms,
                    "rag_ms": rag_ms,
                    "merge_ms": merge_ms,
                    "parallel_gain_ms": parallel_gain_ms,
                    "parallel_efficiency": parallel_efficiency,
                    "bottleneck": bottleneck,
                    "hybrid_mode": contribution,
                },
            },
        }

    def _serialize_response(self, output: Dict[str, Any], trace_id: str, cache_hit: bool, debug: bool) -> Dict[str, Any]:
        timings = output.get("timings") or {}
        response = {
            "answer": output.get("answer") or "",
            "sources": output.get("sources") or [],
            "intent": output.get("intent"),
            "latency_ms": output.get("latency_ms"),
            "confidence": output.get("confidence"),
            "router_type_used": output.get("router_type_used"),
            "llm_call_count": int(output.get("llm_call_count") or 0),
            "branches": output.get("branches") or [],
            "fallback_used": bool(output.get("fallback_used")),
            "timeout_triggered": bool(output.get("timeout_triggered")),
            "sql_success": output.get("sql_success"),
            "rag_success": output.get("rag_success"),
            "merge_used": bool(output.get("merge_used")),
            "answer_nonempty": bool(output.get("answer_nonempty")),
            "cache_hit": cache_hit,
            "timings": {
                "router_ms": timings.get("router_latency_ms"),
                "sql_ms": timings.get("sql_latency_ms"),
                "rag_ms": timings.get("rag_latency_ms"),
                "merge_ms": timings.get("merge_latency_ms"),
                "formatting_ms": timings.get("formatting_latency_ms"),
                "cache_ms": 0.0,
            },
            "trace_id": trace_id,
        }
        if debug:
            response["raw"] = output.get("raw") or {}
        return response

    def _log_request(self, question: str, response: Dict[str, Any]) -> None:
        QUERY_LOG_DIR.mkdir(parents=True, exist_ok=True)
        row = {
            "timestamp": now_iso(),
            "trace_id": response["trace_id"],
            "question": question,
            "intent": response.get("intent"),
            "latency_ms": response.get("latency_ms"),
            "cache_hit": response.get("cache_hit"),
            "router_type": response.get("router_type_used"),
            "branches": response.get("branches"),
            "timeout_triggered": response.get("timeout_triggered"),
            "fallback_used": response.get("fallback_used"),
            "llm_calls": response.get("llm_call_count"),
            "hybrid_mode": ((response.get("raw") or {}).get("hybrid") or {}).get("contribution"),
            "failure_types": [failure.get("failure_type") for failure in ((response.get("raw") or {}).get("failures") or []) if failure.get("failure_type")],
        }
        append_jsonl(QUERY_LOG_DIR / "api_requests.jsonl", row)
        for failure in ((response.get("raw") or {}).get("failures") or []):
            append_jsonl(FAILURE_LOG_DIR / "api_failures.jsonl", failure)

    def _db_status(self) -> str:
        try:
            import psycopg2

            with psycopg2.connect(
                host=os.getenv("PGHOST") or os.getenv("PG_HOST") or "localhost",
                port=int(os.getenv("PGPORT") or os.getenv("PG_PORT") or "5432"),
                dbname=os.getenv("PGDATABASE") or os.getenv("PG_DB") or "northwind",
                user=os.getenv("PGUSER") or os.getenv("PG_USER") or "postgres",
                password=os.getenv("PGPASSWORD") or os.getenv("PG_PASSWORD") or "",
                connect_timeout=2,
            ):
                return "ok"
        except Exception as exc:
            return f"unavailable: {str(exc)[:120]}"

    def _load_router_summary_if_available(self) -> None:
        path = PROJECT_ROOT / "metrics" / "latency" / "router_stress_summary.json"
        if not path.exists():
            return
        try:
            self.metrics.update_router_stress(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return

    def _warm_cache(self) -> None:
        warm_count = int(os.getenv("QUERIONYX_CACHE_WARM_COUNT", "0"))
        if warm_count <= 0:
            return
        dataset_path = PROJECT_ROOT / "benchmarks" / "datasets" / "eval_90_queries.json"
        if not dataset_path.exists():
            return
        try:
            payload = json.loads(dataset_path.read_text(encoding="utf-8-sig"))
            queries = payload.get("queries", payload)[:warm_count]
            for item in queries:
                question = str(item.get("question") or "").strip()
                if not question:
                    continue
                output = self.pipeline.query(question)
                response = self._serialize_response(output, "warm-cache", cache_hit=False, debug=False)
                self.cache.set(question, str(response.get("intent") or "UNKNOWN"), str(response.get("router_type_used") or "warm_cache"), response)
        except Exception:
            return

    @staticmethod
    def _sse(event: str, payload: Dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _parse_pdf_to_chunks(self, path: Path) -> List[Dict[str, Any]]:
        import fitz

        chunks: List[Dict[str, Any]] = []
        with fitz.open(path) as doc:
            for page_idx, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                for chunk_idx, chunk_text in enumerate(_chunk_text(text), start=1):
                    chunks.append(
                        {
                            "text": chunk_text,
                            "source": str(path),
                            "page": page_idx,
                            "chunk_id": f"{path.stem}_p{page_idx}_{chunk_idx}",
                        }
                    )
        return chunks

    def _append_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing: List[Dict[str, Any]] = []
        if CHUNKS_FILE.exists():
            with CHUNKS_FILE.open("rb") as f:
                payload = pickle.load(f)
            if isinstance(payload, list):
                existing = payload
        existing.extend(chunks)
        with CHUNKS_FILE.open("wb") as f:
            pickle.dump(existing, f)

    def _insert_chroma(self, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        import chromadb
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("UPLOAD_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        model = SentenceTransformer(model_name, cache_folder=str(PROJECT_ROOT / "data" / "models" / "sentence_transformers"))
        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collection = client.get_or_create_collection("querionyx_uploads")
        texts = [chunk["text"] for chunk in chunks]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()
        ids = [str(chunk.get("chunk_id") or uuid.uuid4()) for chunk in chunks]
        metadatas = [{"source": chunk["source"], "page": chunk["page"]} for chunk in chunks]
        collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        return len(chunks)


def _chunk_text(text: str, max_chars: int = 1000, overlap: int = 120) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def save_router_summary(summary: Dict[str, Any]) -> None:
    path = PROJECT_ROOT / "metrics" / "latency" / "router_stress_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def _timing(payload: Dict[str, Any], key: str) -> Optional[float]:
    timings = payload.get("timings") if isinstance(payload, dict) else None
    if isinstance(timings, dict):
        return timings.get(key)
    return None


def _jaccard(left: Set[str], right: Set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _avg(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _parallel_efficiency(sql_ms: Optional[float], rag_ms: Optional[float]) -> Optional[float]:
    if sql_ms is None or rag_ms is None or (sql_ms + rag_ms) <= 0:
        return None
    return round(max(sql_ms, rag_ms) / (sql_ms + rag_ms), 4)


def _parallel_gain(sql_ms: Optional[float], rag_ms: Optional[float], actual_ms: float) -> Optional[float]:
    if sql_ms is None or rag_ms is None:
        return None
    return round((sql_ms + rag_ms) - actual_ms, 2)


def _hybrid_bottleneck(sql_ms: Optional[float], rag_ms: Optional[float]) -> Optional[str]:
    if sql_ms is None or rag_ms is None:
        return None
    total = sql_ms + rag_ms
    if total <= 0:
        return None
    if rag_ms / total >= 0.8:
        return "rag_dominant"
    if sql_ms / total >= 0.8:
        return "sql_dominant"
    return "balanced"
