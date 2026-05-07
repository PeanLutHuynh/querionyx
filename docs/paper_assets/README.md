# Paper Assets

Generated from `docs/results/consolidated_results.json` using:

```bash
python -m src.evaluation.export_paper_assets
```

## Recommended 12-Page ICCCNET Set

### Tables

- `tables/table1_system_overview.md` / `.csv`: system overview across router, RAG, SQL, hybrid, and end-to-end performance.
- `tables/table2_rag_comparison.md` / `.csv`: RAG V1-V3 precision, recall, success rate, and latency.
- `tables/table3_sql_evaluation.md` / `.csv`: SQL execution accuracy, exact match, retry rate, and error breakdown.
- `tables/table4_hybrid_evaluation.md` / `.csv`: hybrid correctness, fallback rate, and latency.
- `tables/table5_ablation_study.md` / `.csv`: selected ablation study with full system, no adaptive router, dense only, and hybrid disabled.

### Figures

- `figures/figure1_system_architecture.svg`: system architecture.
- `figures/figure2_rag_comparison.svg`: RAG precision/recall/latency comparison.
- `figures/figure3_router_confusion_matrix.svg`: adaptive router confusion matrix.
- `figures/figure4_ablation_impact.svg`: correctness drop under ablations.

### Narrative

- `../research/paper_narrative_snippets.md`: compact wording for negative LLM router baseline, hybrid latency, RAG recall saturation, routing ambiguity, and SQL errors.
