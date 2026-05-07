"""HYBRID query handler for Querionyx V3.

The handler is optimized for weak local hardware:
- cheap routing/planning before launching expensive branches;
- SQL planner/cache first;
- retrieval-focused RAG branch with short context;
- optional LLM merge only when both branches contribute useful information.
"""

from __future__ import annotations

import asyncio
import json
import os
import pickle
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from src.runtime.config import RuntimeConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class HybridResult:
    question: str
    answer: str
    sources: List[str]
    contribution: str
    rag_result: Dict[str, Any] = field(default_factory=dict)
    sql_result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timings: Dict[str, float] = field(default_factory=dict)
    llm_calls: int = 0


class HybridQueryHandler:
    def __init__(
        self,
        rag_pipeline: Any = None,
        sql_pipeline: Any = None,
        merge_model: str = "qwen2.5:3b",
        timeout_per_module_ms: int = 8000,
        merge_timeout_ms: int = 8000,
        rag_passages: int = 2,
        rag_chars_per_passage: int = 500,
        sql_rows: int = 5,
        sql_columns: int = 8,
        runtime_config: Optional[RuntimeConfig] = None,
    ):
        load_dotenv(PROJECT_ROOT / ".env")
        self.runtime_config = runtime_config or RuntimeConfig.from_env()
        self.rag_pipeline = rag_pipeline
        self.sql_pipeline = sql_pipeline
        self.merge_model = os.getenv("OLLAMA_MERGE_MODEL", merge_model)
        self.timeout_per_module_ms = min(timeout_per_module_ms, self.runtime_config.timeouts.hybrid_total_ms)
        self.merge_timeout_ms = min(merge_timeout_ms, self.runtime_config.timeouts.merge_llm_ms)
        self.rag_passages = rag_passages
        self.rag_chars_per_passage = rag_chars_per_passage
        self.sql_rows = sql_rows
        self.sql_columns = sql_columns
        self._merge_llm = None
        self.enable_heavy_rag = (os.getenv("ENABLE_HEAVY_RAG", "0") == "1") or not self.runtime_config.lightweight_rag
        self._lightweight_chunks: Optional[List[Dict[str, Any]]] = None

    @staticmethod
    def _normalize(question: str) -> str:
        return question.lower().strip()

    @staticmethod
    def _is_doc_question(question: str) -> bool:
        q = question.lower()
        doc_terms = [
            "báo cáo",
            "báo cáo năm",
            "annual report",
            "file pdf",
            "pdf",
            "chiến lược",
            "chính sách",
            "rủi ro",
            "kế hoạch",
            "mục tiêu",
            "sustainability",
            "strategy",
            "policy",
            "risk",
        ]
        sql_terms = ["top", "count", "average", "sum", "list", "bao nhiêu", "tổng", "trung bình"]
        return any(term in q for term in doc_terms) and not any(term in q for term in sql_terms)

    @staticmethod
    def _is_numeric_or_tabular(question: str) -> bool:
        q = question.lower()
        return any(
            term in q
            for term in [
                "top",
                "count",
                "how many",
                "average",
                "sum",
                "total",
                "list",
                "bao nhiêu",
                "trung bình",
                "tổng",
                "liệt kê",
                "doanh thu",
            ]
        )

    def _get_sql_pipeline(self) -> Any:
        if self.sql_pipeline is None:
            from src.sql.text_to_sql import TextToSQLPipeline

            self.sql_pipeline = TextToSQLPipeline(max_result_rows=self.sql_rows)
        return self.sql_pipeline

    def _get_rag_pipeline(self) -> Any:
        if self.rag_pipeline is None:
            from src.rag.rag_v2 import RAGPipelineV2

            self.rag_pipeline = RAGPipelineV2(
                final_top_k=self.rag_passages,
                max_generation_chunks=self.rag_passages,
                max_context_chars_per_chunk=self.rag_chars_per_passage,
                llm_timeout_seconds=max(5, self.timeout_per_module_ms // 1000),
            )
            self.rag_pipeline.load_chunks(verbose=False)
        return self.rag_pipeline

    def _load_lightweight_chunks(self) -> List[Dict[str, Any]]:
        if self._lightweight_chunks is not None:
            return self._lightweight_chunks
        chunks_file = PROJECT_ROOT / "data" / "processed" / "chunks_recursive.pkl"
        if not chunks_file.exists():
            self._lightweight_chunks = []
            return self._lightweight_chunks
        with chunks_file.open("rb") as f:
            chunks = pickle.load(f)
        self._lightweight_chunks = chunks if isinstance(chunks, list) else []
        return self._lightweight_chunks

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [token for token in re.split(r"\W+", text.lower()) if len(token) >= 3]

    def _run_lightweight_rag(self, question: str) -> Dict[str, Any]:
        chunks = self._load_lightweight_chunks()
        if not chunks:
            return {
                "context_passages": [],
                "citations": [],
                "answer": "",
                "score": None,
                "error": "No local document chunks are available.",
            }

        query_tokens = set(self._tokenize(question))
        company_terms = [term for term in ["fpt", "vinamilk", "masan"] if term in question.lower()]
        scored = []
        for chunk in chunks:
            text = chunk.get("text", "")
            text_lower = text.lower()
            tokens = set(self._tokenize(text))
            overlap = len(query_tokens & tokens)
            company_bonus = 3 if any(company in text_lower or company in chunk.get("source", "").lower() for company in company_terms) else 0
            score = overlap + company_bonus
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [chunk for _, chunk in scored[: self.rag_passages]]
        passages = [chunk.get("text", "")[: self.rag_chars_per_passage] for chunk in selected]
        citations = [
            f"{Path(chunk.get('source', 'unknown')).name}#p{chunk.get('page', -1)}"
            for chunk in selected
        ]
        best_score = scored[0][0] / max(1, len(query_tokens)) if scored else None
        return {
            "context_passages": passages,
            "citations": citations,
            "answer": passages[0] if passages else "",
            "score": best_score,
            "error": None if passages else "No relevant document context found.",
        }

    def _get_merge_llm(self) -> Any:
        if self._merge_llm is None:
            from langchain_ollama import OllamaLLM

            base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
            self._merge_llm = OllamaLLM(
                model=self.merge_model,
                base_url=base_url,
                temperature=0.1,
                num_predict=180,
                num_ctx=1024,
                keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
                sync_client_kwargs={"timeout": max(1, self.merge_timeout_ms / 1000)},
            )
        return self._merge_llm

    def _sql_fast_planner_can_handle(self, question: str) -> bool:
        try:
            return self._get_sql_pipeline()._generate_fast_sql(question) is not None
        except Exception:
            return False

    async def _run_sql(self, question: str) -> Dict[str, Any]:
        def call() -> Dict[str, Any]:
            return self._get_sql_pipeline().query(question, include_nl_answer=False)

        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(call),
                timeout=self.timeout_per_module_ms / 1000,
            )
            result.setdefault("timings", {})["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
            return result
        except Exception as exc:
            return {"sql_query": "", "rows": [], "error": str(exc), "timings": {"total_ms": round((time.perf_counter() - started) * 1000, 2)}}

    async def _run_rag(self, question: str) -> Dict[str, Any]:
        def call() -> Dict[str, Any]:
            try:
                if not self.enable_heavy_rag:
                    return self._run_lightweight_rag(question)
                rag = self._get_rag_pipeline()
                chunks = rag.retrieve_hybrid(question, final_top_k=self.rag_passages)
                passages = []
                citations = []
                scores = []
                for chunk in chunks[: self.rag_passages]:
                    text = chunk.get("text", "")[: self.rag_chars_per_passage]
                    source = Path(chunk.get("source", "unknown")).name
                    page = chunk.get("page", -1)
                    passages.append(text)
                    citations.append(f"{source}#p{page}")
                    scores.append(float(chunk.get("rrf_score") or (1.0 - chunk.get("distance", 1.0))))

                score = max(scores) if scores else None
                answer = passages[0] if passages else ""
                return {
                    "context_passages": passages,
                    "citations": citations,
                    "answer": answer,
                    "score": score,
                    "error": None,
                }
            except Exception as exc:
                return {
                    "context_passages": [],
                    "citations": [],
                    "answer": "",
                    "score": None,
                    "error": str(exc),
                }

        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(call),
                timeout=self.timeout_per_module_ms / 1000,
            )
            result.setdefault("timings", {})["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
            return result
        except Exception as exc:
            return {"context_passages": [], "citations": [], "answer": "", "score": None, "error": str(exc), "timings": {"total_ms": round((time.perf_counter() - started) * 1000, 2)}}

    def _trim_sql_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        trimmed = []
        for row in rows[: self.sql_rows]:
            limited = {}
            for idx, (key, value) in enumerate(row.items()):
                if idx >= self.sql_columns:
                    break
                limited[key] = value
            trimmed.append(limited)
        return trimmed

    @staticmethod
    def _format_sql_table(rows: List[Dict[str, Any]]) -> str:
        if not rows:
            return ""
        columns = list(rows[0].keys())
        lines = [
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
        return "\n".join(lines)

    def _deterministic_sql_answer(self, question: str, sql_result: Dict[str, Any]) -> str:
        rows = self._trim_sql_rows(sql_result.get("rows", []))
        if not rows:
            return "Không có kết quả phù hợp từ cơ sở dữ liệu."
        table = self._format_sql_table(rows)
        return f"Kết quả từ cơ sở dữ liệu cho câu hỏi này:\n\n{table}"

    def _deterministic_rag_answer(self, rag_result: Dict[str, Any], note: Optional[str] = None) -> str:
        answer = rag_result.get("answer") or "Tôi tìm thấy một số ngữ cảnh liên quan trong tài liệu, nhưng chưa đủ để kết luận chắc chắn."
        citations = rag_result.get("citations") or []
        suffix = f"\n\nNguồn: {', '.join(citations[: self.rag_passages])}" if citations else ""
        note_text = f"{note}\n\n" if note else ""
        return f"{note_text}{answer}{suffix}"

    def _should_merge_with_llm(self, question: str, rag_result: Dict[str, Any], sql_result: Dict[str, Any]) -> bool:
        if not self.runtime_config.merge_llm_enabled and not self.runtime_config.force_merge_llm:
            return False
        if self.runtime_config.force_merge_llm:
            return bool(rag_result.get("context_passages") and sql_result.get("rows"))
        if not rag_result.get("context_passages") or not sql_result.get("rows"):
            return False
        sql_timings = sql_result.get("timings") or {}
        if (sql_timings.get("fast_path") == 1.0 or sql_timings.get("sql_cache_hit") == 1.0) and self._is_numeric_or_tabular(question):
            return False
        return True

    async def _merge_with_llm(self, question: str, rag_result: Dict[str, Any], sql_result: Dict[str, Any]) -> str:
        rows = self._trim_sql_rows(sql_result.get("rows", []))
        passages = (rag_result.get("context_passages") or [])[: self.rag_passages]
        prompt = (
            "Trả lời bằng tiếng Việt, ngắn gọn và có căn cứ.\n"
            "Dùng [SQL] cho dữ liệu bảng/số, [DOC] cho ngữ cảnh tài liệu.\n"
            "Nếu mâu thuẫn, ưu tiên SQL cho số liệu và DOC cho diễn giải.\n\n"
            f"Câu hỏi: {question}\n"
            f"SQL data: {json.dumps(rows, ensure_ascii=False, default=str)}\n"
            f"DOC context: {json.dumps(passages, ensure_ascii=False)}\n"
            "Trả lời:"
        )

        def call() -> str:
            return self._get_merge_llm().invoke(prompt).strip()

        return await asyncio.wait_for(asyncio.to_thread(call), timeout=self.merge_timeout_ms / 1000)

    async def aquery(self, question: str, router_intent: Optional[str] = None) -> Dict[str, Any]:
        started = time.perf_counter()
        router_intent = (router_intent or "HYBRID").upper()

        if router_intent == "SQL" and self._sql_fast_planner_can_handle(question):
            sql_result = await self._run_sql(question)
            answer = self._deterministic_sql_answer(question, sql_result)
            return HybridResult(
                question=question,
                answer=answer,
                sources=["SQL"],
                contribution="sql_only",
                sql_result=sql_result,
                timings={"total_ms": round((time.perf_counter() - started) * 1000, 2)},
            ).__dict__

        if router_intent == "RAG" or self._is_doc_question(question):
            rag_result = await self._run_rag(question)
            answer = self._deterministic_rag_answer(rag_result)
            return HybridResult(
                question=question,
                answer=answer,
                sources=[f"DOC:{c}" for c in rag_result.get("citations", [])],
                contribution="rag_only",
                rag_result=rag_result,
                error=rag_result.get("error"),
                timings={"total_ms": round((time.perf_counter() - started) * 1000, 2)},
            ).__dict__

        if self.runtime_config.parallel_enabled:
            rag_result, sql_result = await asyncio.gather(self._run_rag(question), self._run_sql(question))
        else:
            rag_result = await self._run_rag(question)
            sql_result = await self._run_sql(question)
        sql_ok = not sql_result.get("error") and bool(sql_result.get("rows"))
        rag_ok = not rag_result.get("error") and bool(rag_result.get("context_passages"))
        rag_low = rag_result.get("score") is not None and float(rag_result["score"]) < 0.4

        llm_calls = 0
        contribution = "both_fail"
        if sql_ok and (not rag_ok or rag_low):
            answer = self._deterministic_sql_answer(question, sql_result)
            sources = ["SQL"]
            contribution = "sql_only"
        elif rag_ok and not sql_ok:
            answer = self._deterministic_rag_answer(
                rag_result,
                note="Không truy vấn được cơ sở dữ liệu cho câu hỏi này.",
            )
            sources = [f"DOC:{c}" for c in rag_result.get("citations", [])]
            contribution = "rag_only"
        elif sql_ok and rag_ok:
            sources = ["SQL"] + [f"DOC:{c}" for c in rag_result.get("citations", [])]
            if self._should_merge_with_llm(question, rag_result, sql_result):
                try:
                    merge_started = time.perf_counter()
                    answer = await self._merge_with_llm(question, rag_result, sql_result)
                    merge_ms = round((time.perf_counter() - merge_started) * 1000, 2)
                    llm_calls = 1
                    contribution = "merged_llm"
                except Exception:
                    merge_ms = round((time.perf_counter() - merge_started) * 1000, 2) if "merge_started" in locals() else 0.0
                    answer = (
                        self._deterministic_sql_answer(question, sql_result)
                        + "\n\n"
                        + self._deterministic_rag_answer(rag_result)
                    )
                    contribution = "merge_timeout"
            else:
                answer = self._deterministic_sql_answer(question, sql_result)
                contribution = "sql_only"
        else:
            answer = "Tôi không có đủ thông tin để trả lời câu hỏi này."
            sources = []

        return HybridResult(
            question=question,
            answer=answer,
            sources=sources,
            contribution=contribution,
            rag_result=rag_result,
            sql_result=sql_result,
            timings={
                "total_ms": round((time.perf_counter() - started) * 1000, 2),
                "merge_ms": locals().get("merge_ms"),
            },
            llm_calls=llm_calls,
        ).__dict__

    def query(self, question: str, router_intent: Optional[str] = None) -> Dict[str, Any]:
        return asyncio.run(self.aquery(question, router_intent=router_intent))
