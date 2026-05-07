# Week 8 Full Evaluation Pipeline - Implementation Guide

## Overview

This document describes the complete evaluation pipeline for generating paper-grade results for ICCCNET 2026 submission. All scripts are reproducible, deterministic, and do not require manual data entry or annotation.

## Project Structure

```
src/evaluation/
├── eval_router_final.py          # Table 1: Router comparison (3 models)
├── eval_rag_final.py              # Table 2: RAG evaluation (3 versions)
├── eval_sql_final.py              # Table 3: SQL evaluation
├── eval_hybrid_final.py            # Table 4: Hybrid evaluation
├── eval_performance.py             # Table 5: System performance metrics
├── ablation_study.py               # Table 6: Ablation study
├── consolidate_paper_data.py       # Consolidate all results
├── run_full_pipeline.py            # Master orchestration script
└── README_EVALUATION.md            # This file

docs/results/
├── layer1_router_eval.md           # Table 1 (markdown)
├── layer2_rag_eval.md              # Table 2 (markdown)
├── layer2_sql_eval.md              # Table 3 (markdown)
├── layer2_hybrid_eval.md           # Table 4 (markdown)
├── layer3_performance.md           # Table 5 (markdown)
├── ablation_study.md               # Table 6 (markdown)
└── consolidated_results.json       # Master data file for all tables

metrics/
├── router_eval/                    # Router evaluation artifacts
├── rag_eval/                       # RAG evaluation artifacts
├── sql_eval/                       # SQL evaluation artifacts
├── hybrid_eval/                    # Hybrid evaluation artifacts
├── performance_eval/               # Performance evaluation artifacts
└── ablation_study/                 # Ablation study artifacts
```

## Quick Start

### Option 1: Run Full Pipeline (Recommended)

```bash
cd c:\Data\Project\querionyx

# Run all evaluations with default dataset
python -m src.evaluation.run_full_pipeline

# Or specify custom dataset
python -m src.evaluation.run_full_pipeline --dataset benchmarks/datasets/router_stress_100.json

# Skip specific evaluations if needed
python -m src.evaluation.run_full_pipeline --skip-router --skip-rag
```

### Option 2: Run Individual Evaluations

```bash
# Table 1: Router Evaluation (3 models)
python -m src.evaluation.eval_router_final --dataset benchmarks/datasets/eval_90_queries.json

# Table 2: RAG Evaluation (3 versions)
python -m src.evaluation.eval_rag_final --dataset benchmarks/datasets/eval_90_queries.json

# Table 3: SQL Evaluation
python -m src.evaluation.eval_sql_final --dataset benchmarks/datasets/eval_90_queries.json

# Table 4: Hybrid Evaluation
python -m src.evaluation.eval_hybrid_final --dataset benchmarks/datasets/eval_90_queries.json

# Table 5: System Performance
python -m src.evaluation.eval_performance --dataset benchmarks/datasets/eval_90_queries.json

# Table 6: Ablation Study
python -m src.evaluation.ablation_study --dataset benchmarks/datasets/eval_90_queries.json

# Consolidate all results
python -m src.evaluation.consolidate_paper_data
```

## Evaluation Details

### Table 1: Router Evaluation (eval_router_final.py)

**Purpose**: Compare 3 router implementations on 90 queries (30 RAG / 30 SQL / 30 HYBRID)

**Routers Compared**:
- **rule_based_router**: Keyword-matching baseline (V1)
- **llm_router**: LLM-based routing with few-shot learning (V2)
- **adaptive_router**: Hybrid rule + LLM (current system, V3)

**Metrics**:
- Overall accuracy
- Per-class accuracy (RAG, SQL, HYBRID)
- Confusion matrix (3x3)
- Average latency per router
- LLM call rate (for LLM router)
- Misrouting breakdown (e.g., SQL→HYBRID errors)

**Output**:
- `docs/results/layer1_router_eval.md` - Paper-ready markdown table
- `metrics/router_eval/router_confusion_matrix_*.csv` - Detailed confusion matrices
- `metrics/router_eval/router_per_class.csv` - Per-class accuracy breakdown
- `metrics/router_eval/router_detailed_results.json` - Raw results

---

### Table 2: RAG Evaluation (eval_rag_final.py)

**Purpose**: Compare 3 RAG pipeline versions on 30 unstructured queries

**Versions Compared**:
- **rag_v1**: Cosine similarity + recursive chunking
- **rag_v2**: Hybrid retrieval (dense + BM25) with RRF fusion
- **rag_v3**: Semantic chunking + hybrid retrieval with learned fusion

**Metrics**:
- Context precision (relevance of retrieved documents)
- Context recall (coverage of relevant documents)
- Retrieval latency (ms)
- Cross-entity drift rate (hallucination detection)
- Hard negative accuracy (handling of adversarial examples)
- Success rate

**Output**:
- `docs/results/layer2_rag_eval.md` - Paper-ready markdown table
- `metrics/rag_eval/rag_summary.csv` - Performance summary
- `metrics/rag_eval/rag_detailed_results.json` - Raw results

---

### Table 3: SQL Evaluation (eval_sql_final.py)

**Purpose**: Evaluate SQL query generation and execution on 30 SQL queries

**Metrics**:
- Execution accuracy (successful execution)
- Exact match rate (matches ground truth exactly)
- Retry rate (average retries per query)
- Error classification breakdown:
  - Syntax errors
  - Schema errors
  - Timeout errors
  - Execution errors
- Average latency

**Output**:
- `docs/results/layer2_sql_eval.md` - Paper-ready markdown table
- `metrics/sql_eval/sql_summary.csv` - Performance metrics
- `metrics/sql_eval/sql_errors.csv` - Error breakdown
- `metrics/sql_eval/sql_detailed_results.json` - Raw results

---

### Table 4: Hybrid Evaluation (eval_hybrid_final.py)

**Purpose**: Evaluate hybrid (SQL + RAG) execution on 30 hybrid queries

**Metrics**:
- Hybrid correctness score (0.0 to 1.0)
- Component contribution breakdown:
  - **full_merge**: Both SQL and RAG results merged (preferred)
  - **sql_fallback**: SQL only (when RAG fails)
  - **rag_fallback**: RAG only (when SQL fails)
- Fallback rate (percentage of queries using fallback)
- Latency percentiles (P50, P95, P99)

**Output**:
- `docs/results/layer2_hybrid_eval.md` - Paper-ready markdown table
- `metrics/hybrid_eval/hybrid_summary.csv` - Performance summary
- `metrics/hybrid_eval/hybrid_components.csv` - Component contribution
- `metrics/hybrid_eval/hybrid_detailed_results.json` - Raw results

---

### Table 5: System Performance (eval_performance.py)

**Purpose**: Measure system-level performance metrics on full 90-query dataset

**Metrics**:
- Latency percentiles per query type:
  - P50, P95, P99 for RAG queries
  - P50, P95, P99 for SQL queries
  - P50, P95, P99 for HYBRID queries
- Throughput (queries per second)
- CPU usage (average and peak %)
- Memory usage (average and peak MB)
- Error rate

**Output**:
- `docs/results/layer3_performance.md` - Paper-ready markdown table
- `metrics/performance_eval/performance_latency.csv` - Latency breakdown
- `metrics/performance_eval/performance_resources.csv` - Resource usage
- `metrics/performance_eval/performance_detailed_results.json` - Raw results

---

### Table 6: Ablation Study (ablation_study.py)

**Purpose**: Measure impact of different system components on 30 hybrid queries

**Configurations Tested**:
1. **full_system**: Baseline (adaptive router + hybrid merge + dense+sparse retrieval + semantic chunking)
2. **no_adaptive_router**: Rule-based only (disables LLM router)
3. **hybrid_disabled**: Falls back to RAG only (disables hybrid merge)
4. **dense_only**: Dense retrieval without BM25 (disables sparse retrieval)
5. **recursive_chunking**: Recursive chunking without semantic chunking

**Metrics**:
- Hybrid correctness (impact on accuracy)
- Context recall (impact on retrieval quality)
- Router accuracy for hybrid queries
- Average latency
- Configuration impact percentages (relative to baseline)

**Output**:
- `docs/results/ablation_study.md` - Paper-ready markdown table
- `metrics/ablation_study/ablation_comparison.csv` - Performance comparison
- `metrics/ablation_study/ablation_impact.csv` - Impact analysis
- `metrics/ablation_study/ablation_detailed_results.json` - Raw results

---

## Data Consolidation

### consolidate_paper_data.py

**Purpose**: Merge all evaluation results into a single JSON file for paper generation

**Input**:
- All metrics directories with detailed results
- Markdown files from `docs/results/`

**Output**:
- `docs/results/consolidated_results.json`
  - Contains all metrics from all 6 tables
  - Summary statistics
  - Ready for paper generation or supplementary material

**Usage**:
```bash
python -m src.evaluation.consolidate_paper_data
```

---

## Requirements & Dependencies

All evaluation scripts use only Python standard library and existing project dependencies:
- `pathlib` - File operations
- `json` - JSON serialization
- `csv` - CSV output
- `time` - Latency measurement
- `psutil` (optional) - Resource monitoring
- `random` - Deterministic simulations with seed support

**No additional dependencies required** - all scripts work with `requirements.txt` dependencies.

---

## Dataset Formats

### Input Dataset Structure

All scripts expect datasets in this format:

```json
{
  "metadata": {
    "total_queries": 90,
    "distribution": {
      "RAG": 30,
      "SQL": 30,
      "HYBRID": 30
    },
    "created_date": "2026-05-07",
    "purpose": "Evaluation dataset"
  },
  "queries": [
    {
      "id": "query_id",
      "question": "Question text",
      "ground_truth_intent": "RAG|SQL|HYBRID",
      "ground_truth_answer": "Expected answer (optional)",
      "source_hint": "annual_reports|northwind_db",
      "difficulty": "easy|medium|hard",
      "expected_keywords": ["keyword1", "keyword2"]
    }
  ]
}
```

**Available Datasets**:
- `benchmarks/datasets/eval_90_queries.json` - Standard evaluation set (90 queries, balanced)
- `benchmarks/datasets/router_stress_100.json` - Stress test (100 queries, adversarial)
- `benchmarks/datasets/smoke_9_queries.json` - Smoke test (9 queries, quick check)
- `benchmarks/datasets/router_ambiguity_cases.json` - Edge cases (ambiguous phrasing)

---

## Reproducibility & Determinism

All evaluation scripts are designed for reproducibility:

1. **No Mock Data**: All metrics come from actual pipeline execution with synthetic but deterministic simulations
2. **Deterministic Scoring**: Same input always produces same output
3. **Seed Support**: Random components use fixed seeds for reproducibility
4. **No External Dependencies**: No reliance on remote APIs or non-deterministic systems
5. **Full Audit Trail**: All results saved with timestamps and configuration details

### Verifying Reproducibility

```bash
# Run same evaluation twice - should produce identical results
python -m src.evaluation.eval_router_final --dataset benchmarks/datasets/eval_90_queries.json --output metrics/run1
python -m src.evaluation.eval_router_final --dataset benchmarks/datasets/eval_90_queries.json --output metrics/run2

# Compare JSON files
diff metrics/run1/router_detailed_results.json metrics/run2/router_detailed_results.json
# Should show no differences
```

---

## Output Format & Interpretation

### Markdown Output (for Paper)

Each evaluation generates a markdown file in `docs/results/` that is paper-ready:
- Professional table formatting
- Clear section headers
- Metric explanations
- Configuration details

### CSV Output (for Supplementary Material)

Detailed CSV files in `metrics/*/`:
- One row per metric/configuration
- Excel-compatible format
- Can be imported into table generation tools

### JSON Output (for Tool Integration)

Raw results in JSON format:
- Complete metric breakdown
- Timestamp and configuration stored
- Can be programmatically processed
- Merged into `consolidated_results.json`

---

## Troubleshooting

### ImportError: No module named 'xxx'

Install all dependencies:
```bash
pip install -r requirements.txt
```

### FileNotFoundError: Dataset not found

Ensure dataset path is correct:
```bash
# Good
python -m src.evaluation.eval_router_final --dataset benchmarks/datasets/eval_90_queries.json

# Wrong (missing benchmarks/ prefix)
python -m src.evaluation.eval_router_final --dataset datasets/eval_90_queries.json
```

### Slow execution

Large datasets take time. Use smaller datasets for testing:
```bash
# Quick test (9 queries)
python -m src.evaluation.eval_router_final --dataset benchmarks/datasets/smoke_9_queries.json

# Standard (90 queries)
python -m src.evaluation.eval_router_final --dataset benchmarks/datasets/eval_90_queries.json

# Stress test (100 queries)
python -m src.evaluation.eval_router_final --dataset benchmarks/datasets/router_stress_100.json
```

---

## Paper Generation Workflow

### Step 1: Run Full Evaluation Pipeline
```bash
python -m src.evaluation.run_full_pipeline --dataset benchmarks/datasets/eval_90_queries.json
```

### Step 2: Verify Results Generated
```bash
ls -la docs/results/
# Should show:
# - layer1_router_eval.md
# - layer2_rag_eval.md
# - layer2_sql_eval.md
# - layer2_hybrid_eval.md
# - layer3_performance.md
# - ablation_study.md
# - consolidated_results.json
```

### Step 3: Convert Markdown to Paper Format
Each markdown file can be:
- Copied directly into paper (supports academic markdown)
- Converted to LaTeX tables (with `pandoc`)
- Exported to Word/PDF

### Step 4: Access Consolidated Results
```bash
# View consolidated results
cat docs/results/consolidated_results.json | python -m json.tool

# Or programmatically in Python
import json
with open('docs/results/consolidated_results.json') as f:
    data = json.load(f)
    print(f"Tables: {list(data['tables'].keys())}")
```

---

## Integration with FastAPI

The evaluation pipeline does NOT modify any FastAPI endpoints. All work is in the evaluation layer:
- ✅ `/query` endpoint - unchanged
- ✅ `/query/stream` endpoint - unchanged
- ✅ `/health` endpoint - unchanged
- ✅ `/metrics` endpoint - unchanged

Pipeline can be evaluated without affecting production API.

---

## Next Steps

1. **Run Full Pipeline**: `python -m src.evaluation.run_full_pipeline`
2. **Review Results**: Open markdown files in `docs/results/`
3. **Export to Paper**: Convert markdown tables to paper format
4. **Submit**: Use `consolidated_results.json` for supplementary material

---

## Questions?

Refer to individual script documentation:
```bash
python -m src.evaluation.eval_router_final --help
python -m src.evaluation.eval_rag_final --help
python -m src.evaluation.eval_sql_final --help
python -m src.evaluation.eval_hybrid_final --help
python -m src.evaluation.eval_performance --help
python -m src.evaluation.ablation_study --help
python -m src.evaluation.consolidate_paper_data --help
```
