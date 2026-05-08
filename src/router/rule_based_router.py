"""Rule-based Router - V1 Baseline for intent classification."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class RouterResult:
    """Result of router classification."""

    intent: str  # RAG | SQL | HYBRID
    confidence: float
    reasoning: str
    signals: Dict[str, float] = field(default_factory=dict)
    ambiguous: bool = False
    matched_sql_keywords: List[str] = field(default_factory=list)
    matched_rag_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "signals": self.signals,
            "ambiguous": self.ambiguous,
            "matched_sql_keywords": self.matched_sql_keywords,
            "matched_rag_keywords": self.matched_rag_keywords,
        }


class RuleBasedRouter:
    """
    Rule-based router for intent classification.
    Baseline V1 for comparison with LLM-based (V2) and Adaptive (V3) routers.
    """

    def __init__(self):
        """Initialize keyword lists for classification."""
        self.ambiguity_margin = 0.15
        self.sql_keywords = {
            "bao nhiêu",
            "tổng",
            "trung bình",
            "top",
            "theo tháng",
            "doanh thu",
            "đếm",
            "liệt kê",
            "xếp hạng",
            "nhiều nhất",
            "ít nhất",
            "lớn nhất",
            "nhỏ nhất",
            "cao nhất",
            "thấp nhất",
            "lọc",
            "sắp xếp",
            "có đơn giá",
            "giá trị",
            "cung cấp",
            "sum",
            "count",
            "avg",
            "average",
            "how many",
            "total",
            "rank",
            "list",
            "filter",
            "sort",
        }

        self.rag_keywords = {
            "quy trình",
            "chính sách",
            "hướng dẫn",
            "mô tả",
            "là gì",
            "như thế nào",
            "giải thích",
            "chiến lược",
            "mục tiêu",
            "rủi ro",
            "kế hoạch",
            "process",
            "policy",
            "guidance",
            "description",
            "what is",
            "how",
            "explain",
            "strategy",
            "objective",
            "goal",
            "plan",
            "risk",
        }

    def classify(self, question: str) -> RouterResult:
        """
        Classify question intent using keyword matching.

        Args:
            question: User's question in Vietnamese or English

        Returns:
            RouterResult with intent, confidence, reasoning
        """
        # Normalize question for matching
        normalized = question.lower().strip()

        matched_sql = sorted(keyword for keyword in self.sql_keywords if keyword in normalized)
        matched_rag = sorted(keyword for keyword in self.rag_keywords if keyword in normalized)
        sql_count = len(matched_sql)
        rag_count = len(matched_rag)
        sql_score = self._score(normalized, matched_sql, "sql")
        rag_score = self._score(normalized, matched_rag, "rag")
        ambiguous = abs(sql_score - rag_score) < self.ambiguity_margin and (sql_score > 0 or rag_score > 0)

        # Determine intent based on keyword presence
        if sql_score > 0 and rag_score > 0:
            intent = "HYBRID"
            reasoning = f"Found mixed SQL ({sql_count}) and RAG ({rag_count}) signals"
        elif sql_score > 0:
            intent = "SQL"
            reasoning = f"Found {sql_count} SQL keyword(s)"
        elif rag_score > 0:
            intent = "RAG"
            reasoning = f"Found {rag_count} RAG keyword(s)"
        else:
            intent = "RAG"  # Default fallback
            reasoning = "No keywords matched; defaulting to RAG (safe fallback)"

        confidence = self._confidence(intent, sql_score, rag_score, ambiguous)
        return RouterResult(
            intent=intent,
            confidence=confidence,
            reasoning=reasoning,
            signals={
                "sql_score": round(sql_score, 4),
                "rag_score": round(rag_score, 4),
                "score_margin": round(abs(sql_score - rag_score), 4),
            },
            ambiguous=ambiguous,
            matched_sql_keywords=matched_sql,
            matched_rag_keywords=matched_rag,
        )

    def _score(self, normalized_question: str, matched_keywords: list[str], family: str) -> float:
        """Return a normalized evidence score for one intent family."""
        if not matched_keywords:
            return 0.0
        weighted = 0.0
        for keyword in matched_keywords:
            if family == "sql" and keyword in {"sum", "count", "avg", "average", "total", "top"}:
                weighted += 1.25
            elif family == "rag" and keyword in {"strategy", "policy", "risk", "chiến lược", "chính sách", "rủi ro"}:
                weighted += 1.2
            else:
                weighted += 1.0
        conjunction_bonus = 0.15 if (" và " in normalized_question or " and " in normalized_question) else 0.0
        return min(1.0, (weighted / 4.0) + conjunction_bonus)

    def _confidence(self, intent: str, sql_score: float, rag_score: float, ambiguous: bool) -> float:
        if intent == "HYBRID":
            base = min(0.95, 0.55 + (sql_score + rag_score) / 2.0)
        else:
            base = 0.55 + max(sql_score, rag_score) * 0.4
        if ambiguous:
            base -= 0.12
        if sql_score == 0 and rag_score == 0:
            base = 0.45
        return round(max(0.0, min(0.99, base)), 4)

    def batch_classify(self, questions: list[str]) -> list[RouterResult]:
        """
        Classify multiple questions.

        Args:
            questions: List of questions

        Returns:
            List of RouterResult
        """
        return [self.classify(q) for q in questions]
