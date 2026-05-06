---
title: "Week 5 - Hybrid Text-to-SQL Module and 90-Query Evaluation Set"
date: 2026-05-06
project: Querionyx
version: 0.5.0
---

# Week 5 Summary: Hybrid Text-to-SQL + 90-Query Evaluation Set

## Executive Summary

Week 5 added a Text-to-SQL module for the PostgreSQL Northwind database and completed the full 90-query evaluation set used by later routing and hybrid QA experiments.

The final Text-to-SQL design should be described carefully: it is **not** a pure LLM-only Text-to-SQL system. It is a **hybrid Text-to-SQL module** combining:

1. A deterministic, Northwind-specific fast planner for frequent BI-style query families.
2. A local LLM fallback using Ollama `qwen2.5:3b` for out-of-planner questions.
3. SQL result execution and retry handling.
4. Optional Vietnamese natural-language answer generation.

This framing is important because the 50-query Northwind benchmark is planner-covered. The reported 1.000 execution accuracy and low latency should therefore be interpreted as performance on a controlled, schema-specific BI workload, not as a claim that a small local LLM solves general Text-to-SQL.

---

## Project Context

| Component | Configuration |
|---|---|
| Database | PostgreSQL Northwind on localhost |
| Core Tables | `categories`, `products`, `suppliers`, `customers`, `orders`, `order_details`, `employees`, `shippers` |
| Additional Tables Used by Tests | `territories`, `region`, `employee_territories` |
| SQL Fallback Model | Ollama `qwen2.5:3b` |
| Evaluation Set | `data/test_queries/sql_queries.json` with 50 SQL queries |
| Full Router Dataset | `data/test_queries/eval_90_queries.json` with 90 queries |

---

## Task 1: Text-to-SQL Module

### Implementation

**File:** `src/sql/text_to_sql.py`  
**Class:** `TextToSQLPipeline`

The module exposes the following Week 5 API:

| Method | Purpose |
|---|---|
| `load_schema()` | Load PostgreSQL table/column metadata. |
| `schema_linking(question)` | Keyword-based table and column linking. |
| `generate_sql(question, schema_context)` | Generate SQL using fast planner first, then LLM fallback. |
| `execute_sql(sql)` | Execute read-only SQL and return result rows or error. |
| `retry_on_error(question, sql, error)` | Regenerate SQL using the database error message. |
| `generate_nl_answer(sql, rows)` | Generate a concise Vietnamese answer from SQL results. |
| `query(question)` | End-to-end SQL pipeline with latency logging. |

### Architecture

```text
Question
   |
   v
Schema linking
   |
   v
Fast planner for Northwind BI query families
   |            \
   | hit         \ miss
   v             v
SQL template     LLM SQL generation (qwen2.5:3b)
   |             |
   +------> SQL execution
             |
             v
       optional Vietnamese answer
```

### Fast Planner Scope

The deterministic planner handles recurring query families over the Northwind schema:

- top-k and first-N listings
- grouped counts and averages
- simple filters
- 2-table joins
- 3-table joins
- basic subqueries
- revenue and quantity aggregations

The planner maps normalized intent and schema keywords to parameterized SQL patterns. It does not store expected answers and does not branch on query IDs.

### LLM Fallback Scope

The local LLM remains useful for questions outside the planner's coverage. However, on the current weak local hardware, direct LLM-first SQL generation was too slow for interactive use. The fallback is therefore treated as a robustness mechanism, not the default path for known BI-style workloads.

---

## Evaluation Methodology

**Evaluation file:** `src/evaluation/eval_sql.py`  
**Output report:** `docs/week5/eval_sql_module.md`

Metrics:

| Metric | Definition |
|---|---|
| Execution Accuracy | Generated SQL runs without error and result rows match `expected_answer`. |
| Exact Match | Generated SQL matches reference SQL after ignoring whitespace and case. |
| Retry Rate | Fraction of queries requiring at least one retry. |
| Error Analysis | Failed queries categorized as `wrong_join`, `wrong_column`, `wrong_aggregation`, or `other`. |

The evaluator does not pass reference SQL or expected answers into the pipeline. References are used only after generation/execution for scoring.

---

## Results

### Final Hybrid Planner + LLM Fallback Result

| System | Query Set | Planner-Covered Queries | LLM SQL Calls | Execution Accuracy | Exact Match | Retry Rate | Total Runtime |
|---|---:|---:|---:|---:|---:|---:|---:|
| Hybrid planner + LLM fallback | 50 | 50/50 | 0/50 | 1.000 | 1.000 | 0.000 | 5.6s |

The final result is strong because all 50 benchmark questions fall within planner-covered Northwind BI query families. This is expected for the curated Week 5 SQL benchmark and should not be generalized to arbitrary Text-to-SQL workloads.

### Earlier LLM-First Baseline

Before adding the fast planner, the module relied much more heavily on local LLM generation. On the same 50-query SQL set, this produced:

| System | Execution Accuracy | Exact Match | Retry Rate | Total Runtime |
|---|---:|---:|---:|---:|
| LLM-first local `qwen2.5:3b` | 0.340 | 0.300 | 0.120 | 3386s |
| Hybrid planner + LLM fallback | 1.000 | 1.000 | 0.000 | 5.6s |

This comparison should be framed as an engineering result: a schema-specific planner and cache can make a local Text-to-SQL system practical for BI-style workloads, while keeping the LLM as a fallback for uncovered queries.

---

## Task 2: 90-Query Evaluation Set

**File:** `data/test_queries/eval_90_queries.json`

The full router/hybrid evaluation set was completed with the required structure:

| Intent | Count |
|---|---:|
| RAG | 30 |
| SQL | 30 |
| HYBRID | 30 |
| Total | 90 |

Difficulty distribution:

| Difficulty | Count |
|---|---:|
| Easy | 15 |
| Medium | 50 |
| Hard | 25 |

Each query includes:

- `id`
- `question`
- `ground_truth_intent`
- `ground_truth_answer`
- `source_hint`
- `difficulty`

---

## Limitations and Scope

The Week 5 Text-to-SQL module is intentionally domain-specific:

- The fast planner is hand-crafted for Northwind and common BI question families.
- Porting to a different schema would require new planner rules or a generated semantic layer.
- The reported 1.000 accuracy is for the planner-covered 50-query benchmark, not a general Text-to-SQL benchmark such as Spider or BIRD.
- LLM fallback latency remains a deployment risk on weak CPU-only hardware, especially for out-of-planner questions.

For deployment, the recommended policy is:

- use fast planner and SQL cache first;
- use LLM fallback only with a strict timeout;
- return a graceful fallback message if LLM generation exceeds the latency budget.

---

## Week 6 Implications

The Week 6 HYBRID handler should avoid unnecessary LLM calls:

- SQL-only questions covered by the fast planner should skip RAG and merge LLM.
- RAG-only document questions should skip SQL.
- HYBRID queries should run SQL and RAG in parallel only when both sources are likely useful.
- The merge LLM should be optional and used only when deterministic merging is insufficient.

This keeps the architecture compatible with weak local hardware and future Render deployment constraints.

---

## Artifacts

| Artifact | Path |
|---|---|
| Text-to-SQL implementation | `src/sql/text_to_sql.py` |
| SQL evaluation script | `src/evaluation/eval_sql.py` |
| SQL evaluation report | `docs/week5/eval_sql_module.md` |
| 90-query evaluation set | `data/test_queries/eval_90_queries.json` |

**Status:** Complete, with scope caveat: results are for a Northwind-specific planner-covered workload.
