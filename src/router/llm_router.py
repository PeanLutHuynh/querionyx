"""LLM-based Router V2 - Intent Classification using Ollama qwen2.5:3b.

Architecture:
- Prompt Type: Few-shot learning with 9 examples (3 per class: RAG, SQL, HYBRID)
- LLM: Ollama qwen2.5:3b (fast, accurate, Vietnamese-aware)
- Output Format: JSON {intent: RAG|SQL|HYBRID, confidence: 0.0-1.0, reasoning: str}
- Hybrid Execution Logic:
  - High confidence (rule-based): skip LLM call, use rule-based result
  - Ambiguous/Hybrid signals: call LLM for classification
  - Confidence thresholds: >=0.7 single module, 0.4-0.7 HYBRID, <0.4 HYBRID fallback
- Efficiency: Minimize LLM calls with rule-based pre-filtering
"""

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_ollama import OllamaLLM

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.router.rule_based_router import RuleBasedRouter, RouterResult

DEFAULT_LLM_MODEL = "qwen2.5:3b"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass
class RouterResultV2(RouterResult):
    """Extended result with V2-specific fields."""

    llm_called: bool = False
    rule_based_fallback: bool = False


# Few-shot examples for prompt engineering
FEW_SHOT_EXAMPLES = [
    # RAG Examples (qualitative, document-based)
    {
        "question": "FPT có chiến lược phát triển nào cho năm 2025?",
        "intent": "RAG",
        "reasoning": "Asking about strategy/plans - qualitative document question",
    },
    {
        "question": "What is the business strategy of Vinamilk in 2024?",
        "intent": "RAG",
        "reasoning": "Asking for qualitative business strategy information from documents",
    },
    {
        "question": "Masan mô tả quy trình sản xuất như thế nào?",
        "intent": "RAG",
        "reasoning": "Asking for process descriptions - requires document-based qualitative answer",
    },
    # SQL Examples (quantitative, structured data)
    {
        "question": "Bao nhiêu sản phẩm được bán trong tháng 1?",
        "intent": "SQL",
        "reasoning": "Asking for quantity/count - requires database query",
    },
    {
        "question": "What are the top 5 customers by revenue?",
        "intent": "SQL",
        "reasoning": "Requesting ranking/aggregation - requires structured database query",
    },
    {
        "question": "Tính tổng doanh thu theo danh mục sản phẩm",
        "intent": "SQL",
        "reasoning": "Asking for aggregated metrics - requires SQL calculation",
    },
    # HYBRID Examples (combining document context + structured data)
    {
        "question": "Chiến lược của FPT là gì và FPT đạt được bao nhiêu doanh thu?",
        "intent": "HYBRID",
        "reasoning": "Combines qualitative (strategy) from RAG and quantitative (revenue) from SQL",
    },
    {
        "question": "Masan's policy on sustainability and what is their total ESG spending?",
        "intent": "HYBRID",
        "reasoning": "Requires both document analysis (policy) and numerical data (spending)",
    },
    {
        "question": "Vinamilk mô tả rủi ro nào và rủi ro nào có tác động lớn nhất?",
        "intent": "HYBRID",
        "reasoning": "Combines document description (risks) with impact ranking (requires both RAG and SQL)",
    },
]


def format_few_shot_prompt() -> str:
    """Format few-shot examples into prompt text."""
    lines = []
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        lines.append(f"Example {i}:")
        lines.append(f"Question: {example['question']}")
        lines.append(
            f"Output: {json.dumps({'intent': example['intent'], 'confidence': 0.95, 'reasoning': example['reasoning']})}"
        )
        lines.append("")
    return "\n".join(lines)


SYSTEM_PROMPT = """You are a query intent classifier for an enterprise Q&A system serving FPT, Vinamilk, and Masan companies.

The system has two data sources:
1. **RAG Module**: Annual report PDFs (FPT, Vinamilk, Masan reports) - use for qualitative questions
   - Topics: Strategy, policy, risk, guidance, process, objectives, goals, plans
   - Example queries: "What is FPT's business strategy?", "Describe Masan's manufacturing process"

2. **SQL Module**: Northwind database with Orders, Products, Customers, Suppliers tables - use for quantitative queries
   - Topics: Count, sum, average, ranking, top-N, filtering, aggregations, metrics
   - Example queries: "How many products sold?", "Top 5 customers by revenue"

Your task: Classify each user query into one of three intents:
- **RAG**: Document-based qualitative question → use PDF search + RAG pipeline
- **SQL**: Database quantitative question → use SQL query against Northwind
- **HYBRID**: Question requiring both sources → execute RAG and SQL, merge results

Output MUST be valid JSON with exactly these fields:
{
  "intent": "RAG" | "SQL" | "HYBRID",
  "confidence": 0.0-1.0,  // 1.0 = very certain, 0.0 = very uncertain
  "reasoning": "brief explanation of intent classification"
}

Here are examples:

""" + format_few_shot_prompt()


def create_user_prompt(question: str) -> str:
    """Create user prompt for classification."""
    return f"""Question: {question}

Output: """


class LLMRouterV2:
    """LLM-based router using Ollama qwen2.5:3b with few-shot learning."""

    def __init__(
        self,
        llm_model: str = DEFAULT_LLM_MODEL,
        ollama_base_url: Optional[str] = None,
        llm_timeout_seconds: int = 90,
        rule_based_confidence_threshold: float = 0.8,
        hybrid_confidence_range: tuple = (0.4, 0.7),
    ):
        """
        Initialize LLM-based router.

        Args:
            llm_model: Ollama model name
            ollama_base_url: Base URL for Ollama endpoint
            llm_timeout_seconds: Timeout for LLM calls
            rule_based_confidence_threshold: Confidence for rule-based direct routing
            hybrid_confidence_range: (low, high) confidence for HYBRID routing
        """
        self.llm_model = llm_model
        self.rule_based_confidence_threshold = rule_based_confidence_threshold
        self.hybrid_confidence_range = hybrid_confidence_range
        self.llm_timeout_seconds = llm_timeout_seconds
        self.rule_based_router = RuleBasedRouter()

        load_dotenv(PROJECT_ROOT / ".env")
        raw_ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.ollama_base_url = raw_ollama_base_url.replace("http://localhost", "http://127.0.0.1")
        self.ollama_base_url = self.ollama_base_url.replace("https://localhost", "http://127.0.0.1")

        print("Initializing LLM Router V2...", flush=True)
        print(f"  - LLM Model: {llm_model}", flush=True)
        print(f"  - Ollama endpoint: {self.ollama_base_url}", flush=True)
        print(f"  - Rule-based confidence threshold: {rule_based_confidence_threshold}", flush=True)
        print(f"  - HYBRID confidence range: {hybrid_confidence_range}", flush=True)

        print("  Initializing Ollama LLM...", flush=True)
        self.llm = OllamaLLM(
            model=llm_model,
            base_url=self.ollama_base_url,
            temperature=0.1,
            num_predict=150,  # JSON output should be concise
            num_ctx=1024, 
            sync_client_kwargs={"timeout": llm_timeout_seconds},
        )
        print(f"     Ollama LLM initialized", flush=True)

        self.llm_call_count = 0
        self.rule_based_skip_count = 0

    def _parse_llm_output(self, output: str) -> Optional[dict]:
        """Parse JSON output from LLM."""
        try:
            # Try to extract JSON from output (LLM might include extra text)
            output_stripped = output.strip()

            # Look for JSON object in the output
            json_start = output_stripped.find("{")
            json_end = output_stripped.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = output_stripped[json_start:json_end]
                parsed = json.loads(json_str)

                # Validate required fields
                if "intent" in parsed and "confidence" in parsed and "reasoning" in parsed:
                    # Ensure intent is valid
                    if parsed["intent"] in ["RAG", "SQL", "HYBRID"]:
                        # Ensure confidence is in [0, 1]
                        parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
                        return parsed
        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            print(f"  Error parsing LLM output: {e}", flush=True)
            print(f"  Raw output: {output[:200]}", flush=True)

        return None

    def _call_llm_classifier(self, question: str) -> Optional[dict]:
        """Call LLM for classification with retry logic and exponential backoff."""
        max_retries = 2
        retry_delay = 2  # seconds
        output = None
        
        for attempt in range(max_retries + 1):
            try:
                user_prompt = create_user_prompt(question)
                # Combine system and user prompt into single input
                full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
                output = self.llm.invoke(full_prompt)
                self.llm_call_count += 1
                break  # Success, exit retry loop
            except Exception as e:
                if attempt < max_retries:
                    print(f"  LLM timeout attempt {attempt + 1}/{max_retries + 1}, retrying in {retry_delay}s...", flush=True)
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"  LLM timeout after {max_retries + 1} attempts: {e}", flush=True)
                    return None
        
        if output is None:
            return None

        parsed = self._parse_llm_output(output)
        return parsed

    def _should_use_rule_based(self, question: str) -> bool:
        """Determine if rule-based router is confident enough to skip LLM.
        
        Strategy: Call LLM more often to improve HYBRID detection.
        """
        # Get rule-based classification
        rule_result = self.rule_based_router.classify(question)

        # ALWAYS use LLM for HYBRID and potentially ambiguous queries
        if rule_result.intent == "HYBRID":
            return False
        
        # Also use LLM if question has mixed signals
        normalized = question.lower()
        has_rag_signal = any(kw in normalized for kw in ["báo cáo", "tường trình", "mô tả", "chiến lược"])
        has_sql_signal = any(kw in normalized for kw in ["bao nhiêu", "tổng", "top", "doanh thu"])
        
        if has_rag_signal and has_sql_signal:
            # Likely HYBRID - call LLM to verify
            return False

        # For clear single-intent, use rule-based only if very confident
        # Lowered threshold from 0.8 to 0.65 for more LLM coverage
        if rule_result.confidence >= 0.65:
            self.rule_based_skip_count += 1
            return True

        return False

    def classify(self, question: str) -> RouterResultV2:
        """
        Classify question intent using hybrid strategy:
        1. Check if rule-based router is highly confident → use it directly
        2. Otherwise, call LLM classifier

        Args:
            question: User's question

        Returns:
            RouterResultV2 with intent, confidence, reasoning, and flags
        """
        # Strategy: Try rule-based first for efficiency
        if self._should_use_rule_based(question):
            # Rule-based is confident; use its result
            rule_result = self.rule_based_router.classify(question)
            return RouterResultV2(
                intent=rule_result.intent,
                confidence=min(0.99, rule_result.confidence),  # Cap confidence
                reasoning=rule_result.reasoning,
                llm_called=False,
                rule_based_fallback=True,
            )

        # Otherwise, use LLM for better classification
        llm_output = self._call_llm_classifier(question)

        if llm_output:
            intent = llm_output.get("intent", "RAG")
            confidence = llm_output.get("confidence", 0.5)
            reasoning = llm_output.get("reasoning", "LLM classification")

            # Apply routing logic based on confidence
            if confidence < self.hybrid_confidence_range[0]:
                # Very low confidence → force HYBRID safe fallback
                intent = "HYBRID"
                confidence = 0.5
                reasoning = f"LLM confidence below threshold ({confidence:.2f}); routing to HYBRID (safe fallback)"

            elif self.hybrid_confidence_range[0] <= confidence < self.hybrid_confidence_range[1]:
                # Medium confidence → force HYBRID
                intent = "HYBRID"
                reasoning = f"Ambiguous intent (confidence {confidence:.2f}); routing to HYBRID"

            return RouterResultV2(
                intent=intent,
                confidence=confidence,
                reasoning=reasoning,
                llm_called=True,
                rule_based_fallback=False,
            )

        else:
            # LLM failed; fall back to rule-based
            rule_result = self.rule_based_router.classify(question)
            return RouterResultV2(
                intent=rule_result.intent,
                confidence=0.5,  # Lower confidence due to LLM failure
                reasoning=f"LLM failed; fallback to rule-based: {rule_result.reasoning}",
                llm_called=False,
                rule_based_fallback=True,
            )

    def batch_classify(self, questions: list[str]) -> list[RouterResultV2]:
        """Classify multiple questions."""
        return [self.classify(q) for q in questions]

    def get_stats(self) -> dict:
        """Get router statistics."""
        return {
            "llm_calls": self.llm_call_count,
            "rule_based_skips": self.rule_based_skip_count,
            "llm_call_rate": self.llm_call_count / (self.llm_call_count + self.rule_based_skip_count)
            if (self.llm_call_count + self.rule_based_skip_count) > 0
            else 0.0,
        }
