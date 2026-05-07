"""Standardized runtime schemas for query, failure, and ablation logs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class StandardResponse:
    answer: str
    sources: List[str]
    intent: str
    latency_ms: float
    confidence: Optional[float]
    reason: str
    router_type_used: str
    llm_call_count: int
    branches: List[str]
    fallback_used: bool
    timeout_triggered: bool
    sql_success: Optional[bool]
    rag_success: Optional[bool]
    merge_used: bool
    answer_nonempty: bool
    cache_hit: Optional[bool]
    timings: Dict[str, Optional[float]]
    raw: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryExecutionLog:
    query_id: str
    question: str
    intent: str
    branches_used: List[str]
    router_type: str
    llm_calls: int
    latency_ms: float
    router_latency_ms: Optional[float]
    sql_latency_ms: Optional[float]
    rag_latency_ms: Optional[float]
    merge_latency_ms: Optional[float]
    formatting_latency_ms: Optional[float]
    p50_latency: Optional[float]
    p95_latency: Optional[float]
    cpu_percent: Optional[float]
    ram_mb: Optional[float]
    cold_start: bool
    timeout_triggered: bool
    fallback_used: bool
    sql_success: Optional[bool]
    rag_success: Optional[bool]
    merge_used: bool
    confidence: Optional[float]
    answer_nonempty: bool
    cache_hit: Optional[bool]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FailureLog:
    failure_type: str
    stage: str
    query: str
    exception: str
    recovery_strategy: str
    latency_impact_ms: float
    resolved: bool
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AblationResultLog:
    config_name: str
    cache_enabled: bool
    parallel_enabled: bool
    lightweight_rag: bool
    merge_llm_enabled: bool
    avg_latency: float
    p95_latency: float
    avg_ram_mb: Optional[float]
    llm_calls_avg: float
    pass_rate: float
    sql_success_rate: float
    hybrid_success_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

