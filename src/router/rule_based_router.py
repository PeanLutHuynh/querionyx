"""Rule-based Router - V1 Baseline for intent classification."""

from dataclasses import dataclass


@dataclass
class RouterResult:
    """Result of router classification."""

    intent: str  # RAG | SQL | HYBRID
    confidence: float  # 1.0 for rule-based (deterministic)
    reasoning: str


class RuleBasedRouter:
    """
    Rule-based router for intent classification.
    Baseline V1 for comparison with LLM-based (V2) and Adaptive (V3) routers.
    """

    def __init__(self):
        """Initialize keyword lists for classification."""
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

        # Count keyword occurrences
        sql_count = sum(1 for keyword in self.sql_keywords if keyword in normalized)
        rag_count = sum(1 for keyword in self.rag_keywords if keyword in normalized)

        # Determine intent based on keyword presence
        if sql_count > 0 and rag_count > 0:
            intent = "HYBRID"
            reasoning = f"Found both SQL keywords ({sql_count}) and RAG keywords ({rag_count})"
        elif sql_count > 0:
            intent = "SQL"
            reasoning = f"Found {sql_count} SQL keyword(s)"
        elif rag_count > 0:
            intent = "RAG"
            reasoning = f"Found {rag_count} RAG keyword(s)"
        else:
            intent = "RAG"  # Default fallback
            reasoning = "No keywords matched; defaulting to RAG (safe fallback)"

        return RouterResult(
            intent=intent,
            confidence=1.0,  # Rule-based is deterministic
            reasoning=reasoning,
        )

    def batch_classify(self, questions: list[str]) -> list[RouterResult]:
        """
        Classify multiple questions.

        Args:
            questions: List of questions

        Returns:
            List of RouterResult
        """
        return [self.classify(q) for q in questions]
