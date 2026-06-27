# Querionyx CRC Revision Markdown

Use this file as a copy-edit guide for the `.docm` paper. It focuses on the remaining reviewer risks: language quality, editable algorithm text, metric validation, figure/table captions, and reference completeness.

## 0. Figure Structure Change

Delete the old standalone observability figure from the `.docm` file. Its content overlaps with Figure 1 and is now integrated into Figure 1 through dashed trace arrows.

Use only one workflow figure in Section 3:

```text
Fig. 1. Querionyx query-processing workflow. Solid arrows show answer-generation paths, while dashed arrows show trace logging as a side channel.
```

Important logic for Figure 1:

```text
USER QUERY -> ADAPTIVE ROUTER
RAG -> RAGPipeline(q) -> grounded_answer
SQL -> TextToSQL(q) -> grounded_answer
HYBRID -> async(RAGPipeline(q), TextToSQL(q))
    if both branches succeed -> FusionLayer(a_rag, a_sql) -> grounded_answer
    if one branch fails -> Fallback(available_branch) -> grounded_answer
All steps emit trace metadata through dashed side-channel arrows.
```

## 1. Title

Current title is acceptable and within 6 words:

**Querionyx: Hybrid RAG-SQL Enterprise QA**

## 2. Revised Abstract

Replace the current abstract with the following polished version:

```text
Enterprise question answering often requires evidence from both structured databases and unstructured documents. Document-only RAG systems can retrieve narrative evidence from reports and policies, but they cannot reliably perform relational operations such as aggregation, filtering, and ranking. Text-to-SQL systems address structured queries, but they cannot explain results using document-grounded evidence. This paper presents Querionyx, a hybrid enterprise question answering system that routes each query to RAG, Text-to-SQL, or a HYBRID execution path. For hybrid queries, Querionyx executes RAG and SQL branches asynchronously, fuses available evidence, and logs routing signals, branch status, fallback mode, generated SQL, retrieved context, and latency. On a 150-query enterprise benchmark, deterministic routing achieved 90.67% intent accuracy, compared with 30.00% for an LLM-based router baseline. Ablation results show that disabling hybrid execution produced the largest correctness drop (12.21%), confirming that coordinated RAG-SQL execution is central to system performance. On a 20-query mixed-intent baseline comparison, Querionyx achieved 0.85 correctness and 0.89 groundedness, outperforming plain RAG (0.54/0.65) and GPT-only answering (0.44/0.00), while maintaining latency close to plain RAG. These results suggest that observable hybrid orchestration improves reliability for enterprise questions that cross document and database boundaries.
```

## 3. Section 2.1 Replacement

Replace the first two paragraphs of Section 2.1 with:

```text
Retrieval-augmented generation (RAG) grounds language-model outputs in retrieved external evidence, which is useful in enterprise settings where reports, policies, and disclosures change faster than model retraining cycles [1, 2]. However, document retrieval alone cannot replace exact relational operations. A retrieved passage may mention a metric, but it cannot compute aggregations, rankings, filters, or joins over a database.

Hybrid search improves retrieval by combining semantic and lexical matching [5]. Dense retrieval captures paraphrased concepts, while BM25 preserves exact names, company phrases, and metric expressions. Querionyx uses ChromaDB for dense retrieval, BM25 for sparse retrieval, and reciprocal rank fusion with k = 60. In evaluation, later RAG variants improved precision more than recall, suggesting a saturation effect: retrieval refinements reduced irrelevant context rather than substantially expanding coverage [6].
```

## 4. Section 2.2 Replacement

Replace Section 2.2 with:

```text
Text-to-SQL systems translate natural language questions into executable SQL over relational schemas [3]. They are useful for queries involving counts, averages, rankings, filters, and joins. A major challenge is schema linking: user language often does not map directly to database table and column names [7, 8]. In enterprise settings, this problem is amplified by ambiguous terminology, incomplete metadata, and domain-specific naming conventions.

Querionyx addresses these issues through schema-aware prompting, read-only SQL validation, execution feedback, and limited retry. Remaining SQL failures in the final benchmark were mainly caused by schema ambiguity and syntax errors, which are consistent with known challenges in cross-domain Text-to-SQL evaluation [7, 8]. Despite these improvements, Text-to-SQL systems still struggle with questions that require narrative context from documents in addition to structured database results.
```

## 5. Section 2.3 Replacement

Replace the first paragraph of Section 2.3 with:

```text
Modular RAG advocates decomposing retrieval-augmented systems into smaller, reconfigurable components [4]. Routing is central to this design because the system must decide whether a query should use document retrieval, database querying, or both. However, a router that returns only a label provides limited observability. When a HYBRID query is misrouted to RAG, for example, it is difficult to determine whether the system missed a SQL signal or whether the query was genuinely ambiguous. Self-RAG [9] trains models to retrieve, generate, and critique outputs through self-reflection, improving document-grounded QA but not addressing structured database reasoning. RAGAS [10] measures faithfulness, context precision, and context recall, but it focuses on document retrieval rather than hybrid branch execution.
```

## 6. Add Editable Algorithm After Fig. 1

Add this immediately after Figure 1. This addresses Reviewer 2 comment #3 and #8 because the algorithm is editable text, not part of the figure.

```text
Algorithm 1 Querionyx Query Processing
Input: user query q
Output: grounded answer a
1. score <- AdaptiveRouter(q)
2. Extract intent, sql_score, and rag_score from score.
3. if intent = RAG then
4.     a <- RAGPipeline(q)
5. else if intent = SQL then
6.     a <- TextToSQL(q)
7. else
8.     a_rag, a_sql <- async(RAGPipeline(q), TextToSQL(q))
9.     if both branches succeed then
10.        a <- FusionLayer(a_rag, a_sql)
11.    else if one branch succeeds then
12.        a <- Fallback(available_branch)
13.    else
14.        a <- InsufficientEvidenceResponse(q)
15. Log trace(routing_signals, branch_status, fallback_mode, latency)
16. return a
```

## 7. Section 3.5 Fix

Add a period at the end and use this polished version:

```text
Of 50 HYBRID queries, 37 achieved full merge, 7 used RAG fallback, and 6 resulted in both-branch degradation. The 26.00% fallback or degradation rate reflects a conservative fusion policy: the system prefers grounded partial answers over unsupported merged responses.
```

## 8. Section 3.6 Replacement

Replace Section 3.6 with:

```text
Final answers alone were insufficient for diagnosing system failures. Incorrect answers could result from misrouting, weak retrieval, invalid SQL, empty SQL results, fusion failure, or branch timeout. Querionyx therefore exports per-query traces containing router signals, branch status, fallback mode, retrieved chunks, generated SQL, error type, and timing metadata. The evaluation pipeline exports results to Markdown, CSV, and JSON so that aggregate metrics can be checked against individual execution records.
```

## 9. Add Metric Validation Paragraph In Section 4

Place this after the hardware paragraph and before Section 4.1:

```text
Metric validation was performed at three levels. Routing accuracy was computed by comparing predicted intent labels against the annotated ground-truth intent for each query. SQL execution accuracy was measured by checking whether generated SQL executed successfully and returned results consistent with the expected answer or expected query behavior. RAG quality was evaluated using context precision and recall over retrieved evidence, with expected keywords and source hints used to verify whether the retrieved passages supported the answer. HYBRID correctness and groundedness were scored from the final answer and its trace, including retrieved document evidence, SQL output, branch status, and fallback mode. Latency was measured as wall-clock execution time from the exported runtime logs, and aggregate metrics were cross-checked against per-query CSV and JSON traces.
```

## 10. Table And Figure Captions

Use these captions:

```text
Fig. 1. Querionyx query-processing workflow. Solid arrows show answer-generation paths, while dashed arrows show trace logging as a side channel.
Fig. 2. Adaptive router confusion matrix.
Fig. 3. Ablation impact on HYBRID query correctness.
```

Use these table header fixes:

```text
Table 2 header: Latency (ms), not Latency.
Table 7 header: Latency (ms), not Latency.
Table 8: reduce text length or set font size to 8.5-9 pt to avoid broken words.
```

## 11. Section 4.4.3 Fix

Replace the first paragraph with:

```text
The hybrid handler obtains 81.50% correctness over 50 HYBRID queries. The 26.00% fallback rate reflects a conservative fusion policy: an unsupported merged answer is not preferred over a grounded partial answer. This behavior is consistent with robustness-oriented RAG findings that emphasize evidence support and failure transparency [9, 13].
```

## 12. Section 4.8 Fix

Replace the paragraph after Table 9 with:

```text
The GPT-only baseline often generated unsupported answers because it did not use retrieval or database execution. Plain RAG retrieved document evidence effectively, but it struggled with calculations, aggregations, and structured database queries. Querionyx combined database evidence and document evidence in a single response. It achieved 0.85 correctness and 0.89 groundedness while maintaining latency close to plain RAG (930 ms versus 928 ms).
```

## 13. Conclusion Replacement

Replace Section 5 with:

```text
This paper presented Querionyx, a hybrid enterprise question answering system that coordinates RAG, Text-to-SQL, adaptive routing, and observable branch execution. The results show that enterprise QA is not simply a choice between document retrieval and database querying. Many practical questions require both narrative evidence and structured computation. Across the experiments, hybrid execution contributed the most to performance: disabling it produced the largest correctness drop among all ablation settings. The deterministic router also provided stable intent classification without adding LLM latency, which is useful for constrained hardware and reproducible evaluation.

The system has several limitations. Although the 150-query benchmark is reproducible, it does not fully capture the diversity and noise of real enterprise language. The document corpus and Northwind database are smaller and cleaner than production enterprise environments. In addition, some HYBRID queries still required partial fallback, meaning that the system sometimes returned grounded but incomplete answers when one branch degraded.

Future work will extend the benchmark with noisier and Vietnamese-language HYBRID queries, improve query decomposition before execution, introduce provenance scoring, and evaluate lightweight models such as Phi-3 and Qwen2.5 for routing and SQL generation.
```

## 14. Reference Fixes

Fix these references:

```text
[8] X. Liu et al., "A Survey of Text-to-SQL in the Era of LLMs: Where Are We, and Where Are We Going?," IEEE Transactions on Knowledge and Data Engineering, 2025, doi: 10.1109/TKDE.2025.3592032.

[9] A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection," in The Twelfth International Conference on Learning Representations, 2024.

[13] C. Sharma, "Retrieval-Augmented Generation: A Comprehensive Survey of Architectures, Enhancements, and Robustness Frontiers," arXiv preprint arXiv:2506.00054, 2025.
```

## 15. Final Reviewer Checklist

- Keep final paper within 10-12 pages.
- Ensure Figure 1 is a workflow figure with trace logging as a dashed side channel.
- Delete the old standalone observability figure.
- Ensure Algorithm 1 is editable text.
- Ensure Figures 3 and 4 are inserted as high-resolution graph outputs, not screenshots.
- Ensure all table text is editable and not an image.
- Fix broken hyphenation in tables where possible.
- Check all references are cited in the text.
- Run one final proofread on Abstract, Section 2.2, Section 3.6, and Conclusion.
