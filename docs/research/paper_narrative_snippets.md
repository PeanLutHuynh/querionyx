# Paper Narrative Snippets

Use these paragraphs to keep the paper narrative aligned with the final experiments.

## LLM Router as Negative Baseline

We include an LLM-based router as a strong negative baseline to demonstrate that naive LLM routing is inefficient in both accuracy and latency. In our setting, deterministic routing achieves comparable or better routing accuracy while avoiding an additional inference call in the runtime path.

## Hybrid Latency

Hybrid latency is dominated by multi-stage retrieval, SQL execution, and evidence fusion rather than a single model inference call. The system therefore prioritizes grounded correctness and failure transparency over strict real-time constraints.

## RAG V3 Recall Saturation

RAG V3 improves context precision through semantic chunking and hybrid retrieval, while recall remains stable due to retrieval coverage saturation on the benchmark corpus. This suggests that later improvements primarily reduce irrelevant context rather than uncovering substantially more relevant evidence.

## Ambiguous HYBRID Routing

Misrouting cases, especially HYBRID to RAG, reflect inherent ambiguity between structured and unstructured enterprise queries rather than a pure model deficiency. This motivates the hybrid handler and conservative fallback design.

## SQL Error Interpretation

Remaining SQL errors are attributable to schema ambiguity and dataset noise rather than unstable runtime behavior. The error breakdown is therefore reported separately from end-to-end system failures.
