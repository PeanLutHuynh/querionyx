"""Central runtime configuration for Querionyx V3 stabilization."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class TimeoutConfig:
    deterministic_router_ms: int = 100
    router_llm_ms: int = 2000
    sql_planning_cache_ms: int = 500
    sql_execution_ms: int = 3000
    lightweight_rag_ms: int = 1500
    full_rag_ms: int = 5000
    merge_llm_ms: int = 2500
    hybrid_total_ms: int = 6000
    end_to_end_ms: int = 8000


@dataclass
class RuntimeConfig:
    config_name: str = "full_v3"
    cache_enabled: bool = True
    parallel_enabled: bool = True
    hybrid_enabled: bool = True
    lightweight_rag: bool = True
    merge_llm_enabled: bool = False
    force_merge_llm: bool = False
    force_mode: Optional[str] = None
    use_llm_router: bool = False
    max_concurrency: int = 2
    low_resource_mode: bool = True
    log_queries: bool = False
    rag_final_top_k: int = 3
    rag_low_confidence_threshold: float = 0.6
    hybrid_low_confidence_threshold: float = 0.65
    sql_low_confidence_threshold: float = 0.75
    routing_low_confidence_threshold: float = 0.7
    query_log_dir: str = "metrics/query_logs"
    failure_log_dir: str = "metrics/failure_logs"
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        cfg = cls()
        cfg.config_name = os.getenv("QUERIONYX_CONFIG_NAME", cfg.config_name)
        cfg.cache_enabled = _env_bool("QUERIONYX_CACHE_ENABLED", cfg.cache_enabled)
        cfg.parallel_enabled = _env_bool("QUERIONYX_PARALLEL_ENABLED", cfg.parallel_enabled)
        cfg.hybrid_enabled = _env_bool("QUERIONYX_HYBRID_ENABLED", cfg.hybrid_enabled)
        cfg.lightweight_rag = _env_bool("QUERIONYX_LIGHTWEIGHT_RAG", cfg.lightweight_rag)
        cfg.merge_llm_enabled = _env_bool("QUERIONYX_MERGE_LLM_ENABLED", cfg.merge_llm_enabled)
        cfg.force_merge_llm = _env_bool("QUERIONYX_FORCE_MERGE_LLM", cfg.force_merge_llm)
        cfg.force_mode = os.getenv("QUERIONYX_FORCE_MODE") or cfg.force_mode
        cfg.use_llm_router = _env_bool("QUERIONYX_USE_LLM_ROUTER", cfg.use_llm_router)
        cfg.max_concurrency = int(os.getenv("QUERIONYX_MAX_CONCURRENCY", str(cfg.max_concurrency)))
        cfg.low_resource_mode = _env_bool("QUERIONYX_LOW_RESOURCE_MODE", cfg.low_resource_mode)
        cfg.log_queries = _env_bool("QUERIONYX_LOG_QUERIES", cfg.log_queries)
        cfg.rag_final_top_k = int(os.getenv("QUERIONYX_RAG_FINAL_TOP_K", str(cfg.rag_final_top_k)))
        cfg.rag_low_confidence_threshold = float(
            os.getenv("QUERIONYX_RAG_LOW_CONFIDENCE_THRESHOLD", str(cfg.rag_low_confidence_threshold))
        )
        cfg.hybrid_low_confidence_threshold = float(
            os.getenv("QUERIONYX_HYBRID_LOW_CONFIDENCE_THRESHOLD", str(cfg.hybrid_low_confidence_threshold))
        )
        cfg.sql_low_confidence_threshold = float(
            os.getenv("QUERIONYX_SQL_LOW_CONFIDENCE_THRESHOLD", str(cfg.sql_low_confidence_threshold))
        )
        cfg.routing_low_confidence_threshold = float(
            os.getenv("QUERIONYX_ROUTING_LOW_CONFIDENCE_THRESHOLD", str(cfg.routing_low_confidence_threshold))
        )
        return cfg

    @classmethod
    def from_file(cls, path: Path) -> "RuntimeConfig":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RuntimeConfig":
        timeout_payload = payload.get("timeouts") or {}
        known_timeout_keys = set(TimeoutConfig.__dataclass_fields__.keys())
        timeouts = TimeoutConfig(**{k: v for k, v in timeout_payload.items() if k in known_timeout_keys})
        known_keys = set(cls.__dataclass_fields__.keys()) - {"timeouts"}
        values = {k: v for k, v in payload.items() if k in known_keys}
        return cls(**values, timeouts=timeouts)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
