"""Generate thesis figures and tables from current, non-simulated sources."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib.pyplot as plt
from matplotlib.figure import Figure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_no_ollama_readiness import audit as audit_no_ollama
from scripts.audit_no_ollama_readiness import load_queries as load_audit_queries
from src.evaluation.evidence import source_snapshot
from src.router.rule_based_router import RuleBasedRouter
from src.runtime.chunk_store import CHUNKS_FILE, load_chunks


OUTPUT_DIR = PROJECT_ROOT / "docs" / "thesis_assets"
FIGURE_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"
EVAL_150 = PROJECT_ROOT / "benchmarks" / "datasets" / "eval_150_queries.json"
EVAL_90 = PROJECT_ROOT / "benchmarks" / "datasets" / "eval_90_queries.json"
STRESS_100 = PROJECT_ROOT / "benchmarks" / "datasets" / "router_stress_100.json"
FULL_CONFIG = PROJECT_ROOT / "benchmarks" / "configs" / "full_v3.json"
CLAIM_MATRIX = PROJECT_ROOT / "docs" / "thesis_claim_evidence_matrix.md"
API_ENTRYPOINT = PROJECT_ROOT / "backend" / "main.py"
FINAL_SUMMARY_PATHS = {
    "answer_quality": PROJECT_ROOT / "reports" / "experiment_runs" / "final_90_full_v3" / "automatic_summary.json",
    "baseline": PROJECT_ROOT / "reports" / "experiment_runs" / "final_baseline_20" / "baseline_automatic_summary.json",
    "components": PROJECT_ROOT / "reports" / "experiment_runs" / "final_component_hybrid_30" / "component_automatic_summary.json",
    "async": PROJECT_ROOT / "reports" / "experiment_runs" / "final_async_hybrid" / "async_automatic_summary.json",
}

INTENTS = ["RAG", "SQL", "HYBRID"]
COLORS = {"RAG": "#2563eb", "SQL": "#0f766e", "HYBRID": "#d97706"}
TEXT = "#172033"
GRID = "#cbd5e1"


def main() -> int:
    prepare_output()
    configure_matplotlib()

    datasets = {
        "Curated 150": load_dataset(EVAL_150),
        "Answer quality 90": load_dataset(EVAL_90),
        "Stress 100": load_dataset(STRESS_100),
    }
    router_metrics = {
        name: evaluate_router(rows)
        for name, rows in datasets.items()
        if name != "Answer quality 90"
    }
    readiness = audit_no_ollama(load_audit_queries(EVAL_150))["summary"]
    corpus = summarize_corpus()
    config = json.loads(FULL_CONFIG.read_text(encoding="utf-8"))
    endpoints = inspect_api_endpoints()
    claims = parse_claim_matrix()
    final_evidence = load_reportable_summaries()

    tables = build_tables(
        datasets=datasets,
        router_metrics=router_metrics,
        readiness=readiness,
        corpus=corpus,
        config=config,
        endpoints=endpoints,
        claims=claims,
        final_evidence=final_evidence,
    )
    for name, headers, rows in tables:
        write_table(name, headers, rows)

    figure_descriptions = build_figures(
        datasets,
        router_metrics,
        readiness,
        corpus,
        claims,
        final_evidence,
    )
    write_catalog(tables, figure_descriptions, final_evidence)

    print(f"Generated {len(list(FIGURE_DIR.glob('*.png')))} PNG/SVG figure pairs")
    print(f"Generated {len(list(TABLE_DIR.glob('*.csv')))} CSV/Markdown table pairs")
    print(f"Asset catalog: {OUTPUT_DIR / 'README.md'}")
    return 0


def prepare_output() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    for directory in (FIGURE_DIR, TABLE_DIR):
        for path in directory.iterdir():
            if path.is_file():
                path.unlink()


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT,
            "axes.titlecolor": TEXT,
            "xtick.color": TEXT,
            "ytick.color": TEXT,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "legend.frameon": False,
        }
    )


def load_dataset(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("queries", payload)
    if not isinstance(rows, list):
        raise ValueError(f"Unsupported dataset shape: {path}")
    return [row for row in rows if isinstance(row, dict)]


def load_reportable_summaries() -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    _, current_snapshot_sha256 = source_snapshot()
    for name, path in FINAL_SUMMARY_PATHS.items():
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        manifest_path = path.parent / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if (
            payload.get("thesis_reporting_allowed") is not True
            or manifest.get("thesis_reporting_allowed") is not True
            or manifest.get("source_snapshot_sha256") != current_snapshot_sha256
        ):
            continue
        payload["_source_path"] = path
        summaries[name] = payload
    return summaries


def intent_of(row: dict[str, Any]) -> str:
    return str(row.get("ground_truth_intent") or row.get("expected_intent") or "UNKNOWN").upper()


def evaluate_router(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    router = RuleBasedRouter()
    confusion = {actual: {predicted: 0 for predicted in INTENTS} for actual in INTENTS}
    for row in rows:
        actual = intent_of(row)
        predicted = str(router.classify(str(row.get("question") or "")).intent).upper()
        if actual in confusion and predicted in confusion[actual]:
            confusion[actual][predicted] += 1

    total = sum(sum(values.values()) for values in confusion.values())
    correct = sum(confusion[label][label] for label in INTENTS)
    per_intent: dict[str, dict[str, float | int]] = {}
    for label in INTENTS:
        true_positive = confusion[label][label]
        support = sum(confusion[label].values())
        predicted_total = sum(confusion[actual][label] for actual in INTENTS)
        precision = true_positive / predicted_total if predicted_total else 0.0
        recall = true_positive / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_intent[label] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    return {
        "total": total,
        "accuracy": correct / total if total else 0.0,
        "confusion": confusion,
        "per_intent": per_intent,
    }


def summarize_corpus() -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"chunks": 0, "pages": set(), "characters": 0}
    )
    for chunk in load_chunks():
        source = str(chunk.get("source") or "unknown")
        grouped[source]["chunks"] += 1
        if chunk.get("page") is not None:
            grouped[source]["pages"].add(chunk["page"])
        grouped[source]["characters"] += len(str(chunk.get("text") or ""))

    rows = []
    for source, values in sorted(grouped.items()):
        stem = Path(source).stem
        parts = stem.split("_")
        chunks = int(values["chunks"])
        rows.append(
            {
                "company": parts[0].upper(),
                "year": parts[1] if len(parts) > 1 else "Unknown",
                "source": source,
                "pages": len(values["pages"]),
                "chunks": chunks,
                "avg_characters": values["characters"] / chunks if chunks else 0.0,
            }
        )
    return rows


def inspect_api_endpoints() -> list[list[str]]:
    tree = ast.parse(API_ENTRYPOINT.read_text(encoding="utf-8"))
    descriptions = {
        "/query": "Execute one natural-language query",
        "/query/stream": "Stream metadata and result with server-sent events",
        "/health": "Report API, database, RAG, and cache health",
        "/metrics": "Report runtime latency, cache, routing, and failures",
    }
    rows: list[list[str]] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            route = str(decorator.args[0].value)
            rows.append([decorator.func.attr.upper(), route, descriptions.get(route, node.name)])
    return rows


def parse_claim_matrix() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in CLAIM_MATRIX.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| C"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 8:
            continue
        rows.append(
            {
                "id": cells[0],
                "claim": cells[1],
                "label": cells[3],
                "status": cells[4],
                "required_work": cells[6],
            }
        )
    return rows


def build_tables(
    *,
    datasets: dict[str, list[dict[str, Any]]],
    router_metrics: dict[str, dict[str, Any]],
    readiness: dict[str, Any],
    corpus: list[dict[str, Any]],
    config: dict[str, Any],
    endpoints: list[list[str]],
    claims: list[dict[str, str]],
    final_evidence: dict[str, dict[str, Any]],
) -> list[tuple[str, list[str], list[list[Any]]]]:
    tables: list[tuple[str, list[str], list[list[Any]]]] = []

    composition = []
    for name, rows in datasets.items():
        counts = Counter(intent_of(row) for row in rows)
        composition.append([name, counts["RAG"], counts["SQL"], counts["HYBRID"], len(rows)])
    tables.append(("table01_benchmark_composition", ["Dataset", "RAG", "SQL", "HYBRID", "Total"], composition))

    router_rows = []
    for dataset, metrics in router_metrics.items():
        for intent in INTENTS:
            values = metrics["per_intent"][intent]
            router_rows.append(
                [dataset, intent, values["support"], pct(values["precision"]), pct(values["recall"]), pct(values["f1"])]
            )
        router_rows.append([dataset, "Overall", metrics["total"], "", pct(metrics["accuracy"]), ""])
    tables.append(("table02_router_performance", ["Dataset", "Class", "Support", "Precision", "Recall/Accuracy", "F1"], router_rows))

    stress = router_metrics["Stress 100"]["confusion"]
    tables.append(
        (
            "table03_router_stress_confusion_matrix",
            ["Actual", *[f"Predicted {intent}" for intent in INTENTS]],
            [[actual, *[stress[actual][predicted] for predicted in INTENTS]] for actual in INTENTS],
        )
    )

    tables.append(
        (
            "table04_no_ollama_readiness",
            ["Measure", "Value", "Interpretation"],
            [
                ["Curated prompts", readiness["total"], "Static audit cases"],
                ["Route accuracy", pct(readiness["route_accuracy"]), "Against curated labels"],
                ["No-Ollama safe rate", pct(readiness["no_ollama_safe_rate"]), "Route and planner coverage"],
                ["SQL cases requiring fast path", readiness["needs_sql"], "SQL and HYBRID cases"],
                ["SQL fast paths available", readiness["sql_fast_path"], "Deterministic planner match"],
            ],
        )
    )

    corpus_rows = [
        [row["company"], row["year"], row["source"], row["pages"], row["chunks"], round(row["avg_characters"], 1)]
        for row in corpus
    ]
    corpus_rows.append(
        ["Total", "", "9 reports", sum(row["pages"] for row in corpus), sum(row["chunks"] for row in corpus), ""]
    )
    tables.append(("table05_annual_report_corpus", ["Company", "Year", "Source", "Page IDs", "Chunks", "Avg characters"], corpus_rows))

    tables.append(
        (
            "table06_frozen_runtime_configuration",
            ["Setting", "Value"],
            [[key, json.dumps(value, ensure_ascii=False) if value is None or isinstance(value, (dict, list)) else value] for key, value in sorted(config.items())]
            + [["chunk_store", str(CHUNKS_FILE.relative_to(PROJECT_ROOT)).replace("\\", "/")]],
        )
    )
    tables.append(("table07_api_endpoints", ["Method", "Endpoint", "Purpose"], endpoints))
    tables.append(
        (
            "table08_claim_evidence_status",
            ["ID", "Claim", "Evidence label", "Status", "Required work"],
            [[row["id"], row["claim"], row["label"], row["status"], row["required_work"]] for row in claims],
        )
    )
    tables.append(
        (
            "table09_asset_provenance",
            ["Asset group", "Source", "SHA-256", "Evidence type", "Reporting boundary"],
            provenance_rows(final_evidence),
        )
    )

    answer_quality = final_evidence.get("answer_quality")
    if answer_quality:
        summary = answer_quality["summary"]
        rows = [
            [
                intent,
                values["query_count"],
                pct(values["automatic_score"]),
                pct(values["pass_rate"]),
            ]
            for intent, values in summary.get("per_intent", {}).items()
        ]
        rows.append(
            [
                "Overall",
                summary["query_count"],
                pct(summary["automatic_score"]),
                pct(summary["technical_pass_rate"]),
            ]
        )
        tables.append(
            (
                "table10_answer_quality",
                ["Intent", "Queries", "Automatic evidence score", "Technical pass rate"],
                rows,
            )
        )

    baseline = final_evidence.get("baseline")
    if baseline:
        rows = []
        for system, values in baseline["summary"].items():
            rows.append(
                [
                    system,
                    values["query_count"],
                    pct(values["automatic_score"]),
                    pct(values["technical_success_rate"]),
                    values.get("mean_latency_ms") or "",
                ]
            )
        tables.append(
            (
                "table11_baseline_comparison",
                ["System", "Queries", "Automatic evidence score", "Technical success rate", "Mean latency (ms)"],
                rows,
            )
        )

    components = final_evidence.get("components")
    if components:
        rows = []
        for variant, values in components["summary"].items():
            rows.append(
                [
                    variant,
                    values["query_count"],
                    pct(values["automatic_score"]),
                    pct(values["technical_pass_rate"]),
                    values.get("mean_latency_ms") or "",
                ]
            )
        tables.append(
            (
                "table12_component_comparison",
                ["Variant", "Queries", "Automatic evidence score", "Technical pass rate", "Mean latency (ms)"],
                rows,
            )
        )

    async_evidence = final_evidence.get("async")
    if async_evidence:
        summary = async_evidence["summary"]
        rows = []
        for mode in ("sequential", "async"):
            values = summary.get(mode) or {}
            rows.extend(
                [
                    [f"{mode} P50 latency", values.get("p50_ms", ""), "ms"],
                    [f"{mode} P95 latency", values.get("p95_ms", ""), "ms"],
                    [f"{mode} mean latency", values.get("avg_ms", ""), "ms"],
                ]
            )
        rows.extend(
            [
                ["P50 speedup", summary.get("speedup_p50") or "", "x"],
                ["Exact output-match rate", round(summary["exact_output_match_rate"] * 100, 2), "%"],
            ]
        )
        tables.append(("table13_async_hybrid", ["Measure", "Value", "Unit"], rows))
    return tables


def provenance_rows(final_evidence: dict[str, dict[str, Any]]) -> list[list[str]]:
    sources = [
        ("Curated benchmark", EVAL_150, "Direct dataset inventory", "Development/validation set"),
        ("Answer-quality benchmark", EVAL_90, "Direct dataset inventory", "Experimental setup only until executed"),
        ("Router stress benchmark", STRESS_100, "Direct dataset inventory", "Adversarial routing set"),
        ("Router implementation", PROJECT_ROOT / "src" / "router" / "rule_based_router.py", "Measured deterministic execution", "Name the evaluated dataset"),
        ("No-Ollama audit", PROJECT_ROOT / "scripts" / "audit_no_ollama_readiness.py", "Static executable audit", "Not semantic answer quality"),
        ("Corpus summary", CHUNKS_FILE, "Direct corpus inventory", "Page IDs are not physical page totals"),
        ("Source manifest", PROJECT_ROOT / "data" / "source_manifest.json", "Source-file inventory", "Original PDFs are outside Git"),
        ("Frozen configuration", FULL_CONFIG, "Configuration inspection", "Not performance evidence"),
        ("API surface", API_ENTRYPOINT, "Source inspection", "Not performance evidence"),
        ("Claim status", CLAIM_MATRIX, "Research governance", "Blocked claims remain unreportable"),
    ]
    rows = [
        [name, path.relative_to(PROJECT_ROOT).as_posix(), sha256(path), evidence_type, boundary]
        for name, path, evidence_type, boundary in sources
    ]
    for name, payload in final_evidence.items():
        path = payload["_source_path"]
        rows.append(
            [
                f"Final {name.replace('_', ' ')}",
                path.relative_to(PROJECT_ROOT).as_posix(),
                sha256(path),
                str(payload.get("evidence_type") or "reportable summary"),
                "thesis_reporting_allowed=true",
            ]
        )
    return rows


def build_figures(
    datasets: dict[str, list[dict[str, Any]]],
    router_metrics: dict[str, dict[str, Any]],
    readiness: dict[str, Any],
    corpus: list[dict[str, Any]],
    claims: list[dict[str, str]],
    final_evidence: dict[str, dict[str, Any]],
) -> list[tuple[str, str, str]]:
    descriptions = [
        ("fig01_system_architecture", "Querionyx runtime architecture", "Chapter 3"),
        ("fig02_benchmark_intent_distribution", "Benchmark intent composition", "Chapter 4 setup"),
        ("fig03_benchmark_difficulty_distribution", "Benchmark difficulty composition", "Chapter 4 setup"),
        ("fig04_router_recall_by_intent", "Router recall by intent", "Chapter 4 routing"),
        ("fig05_router_stress_confusion_matrix", "Stress-test confusion matrix", "Chapter 4 error analysis"),
        ("fig06_no_ollama_readiness", "Static no-Ollama readiness", "Chapter 3 deployment"),
        ("fig07_corpus_chunks_by_report", "Annual-report chunk distribution", "Chapter 3 data"),
        ("fig08_claim_evidence_readiness", "Claim-evidence readiness", "Appendix"),
    ]
    figure_architecture()
    figure_intent_distribution(datasets)
    figure_difficulty_distribution(datasets)
    figure_router_recall(router_metrics)
    figure_confusion(router_metrics["Stress 100"]["confusion"])
    figure_no_ollama(readiness)
    figure_corpus(corpus)
    figure_claim_status(claims)

    if final_evidence.get("answer_quality"):
        figure_answer_quality(final_evidence["answer_quality"]["summary"])
        descriptions.append(("fig09_answer_quality", "Automatic evidence score by intent", "Chapter 4 results"))
    if final_evidence.get("baseline"):
        figure_system_comparison(
            final_evidence["baseline"]["summary"],
            "Baseline Comparison",
            "fig10_baseline_comparison",
        )
        descriptions.append(("fig10_baseline_comparison", "Frozen baseline comparison", "Chapter 4 results"))
    if final_evidence.get("components"):
        figure_system_comparison(
            final_evidence["components"]["summary"],
            "Component Comparison",
            "fig11_component_comparison",
        )
        descriptions.append(("fig11_component_comparison", "Frozen component comparison", "Chapter 4 ablation"))
    if final_evidence.get("async"):
        figure_async_latency(final_evidence["async"]["summary"])
        descriptions.append(("fig12_async_latency", "Sequential and asynchronous latency", "Chapter 4 efficiency"))
    return descriptions


def figure_architecture() -> None:
    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")
    boxes = [
        (0.4, 2.35, 1.6, 1.1, "Question", "#e2e8f0"),
        (2.6, 2.35, 1.8, 1.1, "Rule router", "#dbeafe"),
        (5.0, 4.25, 2.2, 1.0, "Lightweight RAG", "#dbeafe"),
        (5.0, 2.35, 2.2, 1.0, "Text-to-SQL", "#ccfbf1"),
        (5.0, 0.45, 2.2, 1.0, "Hybrid executor", "#fef3c7"),
        (7.9, 4.25, 1.8, 1.0, "Chunk corpus", "#f1f5f9"),
        (7.9, 2.35, 1.8, 1.0, "PostgreSQL", "#f1f5f9"),
        (10.3, 2.35, 1.3, 1.1, "Answer\n+ trace", "#dcfce7"),
    ]
    for x, y, width, height, label, color in boxes:
        ax.add_patch(plt.Rectangle((x, y), width, height, facecolor=color, edgecolor="#64748b", linewidth=1.2))
        ax.text(x + width / 2, y + height / 2, label, ha="center", va="center", color=TEXT, weight="bold")
    arrows = [
        ((2.0, 2.9), (2.6, 2.9), 0.0),
        ((4.4, 2.9), (5.0, 4.75), 0.0),
        ((4.4, 2.9), (5.0, 2.85), 0.0),
        ((4.4, 2.9), (5.0, 0.95), 0.0),
        ((6.1, 1.45), (6.1, 2.35), 0.0),
        ((7.2, 4.75), (7.9, 4.75), 0.0),
        ((7.2, 2.85), (7.9, 2.85), 0.0),
        ((9.7, 4.75), (10.3, 3.25), 0.0),
        ((9.7, 2.85), (10.3, 2.85), 0.0),
    ]
    for start, end, radius in arrows:
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops={
                "arrowstyle": "->",
                "color": "#475569",
                "lw": 1.4,
                "connectionstyle": f"arc3,rad={radius}",
            },
        )
    ax.plot([7.2, 7.55, 7.55], [0.95, 0.95, 4.75], color="#475569", lw=1.4)
    ax.annotate(
        "",
        xy=(7.2, 4.75),
        xytext=(7.55, 4.75),
        arrowprops={"arrowstyle": "->", "color": "#475569", "lw": 1.4},
    )
    ax.set_title("Querionyx Runtime Architecture", fontsize=16, weight="bold", pad=12)
    save_figure(fig, "fig01_system_architecture")


def figure_intent_distribution(datasets: dict[str, list[dict[str, Any]]]) -> None:
    names = list(datasets)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bottoms = [0] * len(names)
    for intent in INTENTS:
        values = [Counter(intent_of(row) for row in datasets[name])[intent] for name in names]
        ax.bar(names, values, bottom=bottoms, label=intent, color=COLORS[intent])
        bottoms = [left + right for left, right in zip(bottoms, values)]
    ax.set_ylabel("Queries")
    ax.set_title("Benchmark Intent Composition", weight="bold")
    ax.legend(ncol=3, loc="upper right")
    ax.grid(axis="y", color=GRID, alpha=0.5)
    save_figure(fig, "fig02_benchmark_intent_distribution")


def figure_difficulty_distribution(datasets: dict[str, list[dict[str, Any]]]) -> None:
    names = [name for name in datasets if name != "Stress 100"]
    difficulties = ["easy", "medium", "hard"]
    palette = ["#16a34a", "#d97706", "#dc2626"]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    width = 0.24
    positions = list(range(len(names)))
    for offset, (difficulty, color) in enumerate(zip(difficulties, palette)):
        values = [Counter(str(row.get("difficulty") or "unspecified").lower() for row in datasets[name])[difficulty] for name in names]
        ax.bar([position + (offset - 1) * width for position in positions], values, width, label=difficulty.title(), color=color)
    ax.set_xticks(positions, names)
    ax.set_ylabel("Queries")
    ax.set_title("Benchmark Difficulty Composition", weight="bold")
    ax.legend(ncol=3)
    ax.grid(axis="y", color=GRID, alpha=0.5)
    save_figure(fig, "fig03_benchmark_difficulty_distribution")


def figure_router_recall(router_metrics: dict[str, dict[str, Any]]) -> None:
    names = list(router_metrics)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    width = 0.24
    positions = list(range(len(names)))
    for offset, intent in enumerate(INTENTS):
        values = [router_metrics[name]["per_intent"][intent]["recall"] * 100 for name in names]
        ax.bar([position + (offset - 1) * width for position in positions], values, width, label=intent, color=COLORS[intent])
    ax.set_xticks(positions, names)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Recall (%)")
    ax.set_title("Deterministic Router Recall by Intent", weight="bold")
    ax.legend(ncol=3)
    ax.grid(axis="y", color=GRID, alpha=0.5)
    save_figure(fig, "fig04_router_recall_by_intent")


def figure_confusion(confusion: dict[str, dict[str, int]]) -> None:
    matrix = [[confusion[actual][predicted] for predicted in INTENTS] for actual in INTENTS]
    fig, ax = plt.subplots(figsize=(6.5, 5.6))
    image = ax.imshow(matrix, cmap="Blues")
    for row, values in enumerate(matrix):
        for column, value in enumerate(values):
            ax.text(column, row, value, ha="center", va="center", color="white" if value > 18 else TEXT, weight="bold")
    ax.set_xticks(range(3), INTENTS)
    ax.set_yticks(range(3), INTENTS)
    ax.set_xlabel("Predicted intent")
    ax.set_ylabel("Actual intent")
    ax.set_title("Router Stress-Test Confusion Matrix", weight="bold")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    save_figure(fig, "fig05_router_stress_confusion_matrix")


def figure_no_ollama(readiness: dict[str, Any]) -> None:
    labels = ["Route labels", "No-Ollama safety", "SQL fast paths"]
    values = [
        readiness["route_accuracy"] * 100,
        readiness["no_ollama_safe_rate"] * 100,
        readiness["sql_fast_path"] / readiness["needs_sql"] * 100 if readiness["needs_sql"] else 0,
    ]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    bars = ax.barh(labels, values, color=["#2563eb", "#0f766e", "#d97706"])
    ax.set_xlim(0, 105)
    ax.set_xlabel("Coverage (%)")
    ax.set_title("Static No-Ollama Readiness", weight="bold")
    ax.grid(axis="x", color=GRID, alpha=0.5)
    for bar, value in zip(bars, values):
        ax.text(value - 2, bar.get_y() + bar.get_height() / 2, f"{value:.0f}%", ha="right", va="center", color="white", weight="bold")
    save_figure(fig, "fig06_no_ollama_readiness")


def figure_corpus(corpus: list[dict[str, Any]]) -> None:
    labels = [f"{row['company']} {row['year']}" for row in corpus]
    values = [row["chunks"] for row in corpus]
    colors = [COLORS["RAG"], "#60a5fa", "#93c5fd", COLORS["SQL"], "#2dd4bf", "#99f6e4", COLORS["HYBRID"], "#fbbf24", "#fde68a"]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.bar(labels, values, color=colors[: len(labels)])
    ax.set_ylabel("Chunks")
    ax.set_title("Annual-Report Corpus by Source", weight="bold")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", color=GRID, alpha=0.5)
    save_figure(fig, "fig07_corpus_chunks_by_report")


def figure_claim_status(claims: list[dict[str, str]]) -> None:
    groups = Counter(claim_group(row["status"]) for row in claims)
    labels = ["Approved", "Pending", "Blocked"]
    values = [groups[label] for label in labels]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    bars = ax.bar(labels, values, color=["#16a34a", "#d97706", "#dc2626"])
    ax.set_ylabel("Claims")
    ax.set_title("Claim-Evidence Readiness", weight="bold")
    ax.grid(axis="y", color=GRID, alpha=0.5)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.08, str(value), ha="center", weight="bold")
    save_figure(fig, "fig08_claim_evidence_readiness")


def figure_answer_quality(summary: dict[str, Any]) -> None:
    per_intent = summary.get("per_intent") or {}
    labels = [intent for intent in INTENTS if intent in per_intent]
    quality = [per_intent[label]["automatic_score"] * 100 for label in labels]
    technical = [per_intent[label]["pass_rate"] * 100 for label in labels]
    positions = list(range(len(labels)))
    width = 0.34
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.bar([value - width / 2 for value in positions], quality, width, label="Evidence score", color="#2563eb")
    ax.bar([value + width / 2 for value in positions], technical, width, label="Technical pass", color="#0f766e")
    ax.set_xticks(positions, labels)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Rate (%)")
    ax.set_title("Automatic Evidence Score by Intent", weight="bold")
    ax.legend(ncol=2)
    ax.grid(axis="y", color=GRID, alpha=0.5)
    save_figure(fig, "fig09_answer_quality")


def figure_system_comparison(summary: dict[str, Any], title: str, filename: str) -> None:
    keys = list(summary)
    labels = [key.replace("_", " ").title() for key in keys]
    quality = [summary[key]["automatic_score"] * 100 for key in keys]
    technical = [
        summary[key].get("technical_success_rate", summary[key].get("technical_pass_rate", 0.0)) * 100
        for key in keys
    ]
    positions = list(range(len(keys)))
    width = 0.34
    fig, ax = plt.subplots(figsize=(max(8.5, len(keys) * 1.7), 5.4))
    ax.bar([value - width / 2 for value in positions], quality, width, label="Evidence score", color="#2563eb")
    ax.bar([value + width / 2 for value in positions], technical, width, label="Technical success", color="#d97706")
    ax.set_xticks(positions, labels, rotation=18, ha="right")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Rate (%)")
    ax.set_title(title, weight="bold")
    ax.legend(ncol=2)
    ax.grid(axis="y", color=GRID, alpha=0.5)
    save_figure(fig, filename)


def figure_async_latency(summary: dict[str, Any]) -> None:
    labels = ["Sequential", "Async"]
    p50 = [float((summary.get(mode.lower()) or {}).get("p50_ms") or 0.0) for mode in labels]
    p95 = [float((summary.get(mode.lower()) or {}).get("p95_ms") or 0.0) for mode in labels]
    positions = list(range(len(labels)))
    width = 0.34
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.bar([value - width / 2 for value in positions], p50, width, label="P50", color="#0f766e")
    ax.bar([value + width / 2 for value in positions], p95, width, label="P95", color="#d97706")
    ax.set_xticks(positions, labels)
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Sequential vs. Asynchronous Hybrid Latency", weight="bold")
    ax.legend(ncol=2)
    ax.grid(axis="y", color=GRID, alpha=0.5)
    save_figure(fig, "fig12_async_latency")


def claim_group(status: str) -> str:
    lowered = status.lower()
    if lowered.startswith("approved"):
        return "Approved"
    if "blocked" in lowered or "rejected" in lowered:
        return "Blocked"
    return "Pending"


def save_figure(fig: Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    svg_path = FIGURE_DIR / f"{name}.svg"
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)
    svg_text = svg_path.read_text(encoding="utf-8")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
    )


def write_table(name: str, headers: list[str], rows: Iterable[Iterable[Any]]) -> None:
    normalized = [[format_cell(value) for value in row] for row in rows]
    csv_path = TABLE_DIR / f"{name}.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(normalized)

    markdown = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    markdown.extend("| " + " | ".join(escape_markdown(value) for value in row) + " |" for row in normalized)
    (TABLE_DIR / f"{name}.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")


def write_catalog(
    tables: list[tuple[str, list[str], list[list[Any]]]],
    figure_descriptions: list[tuple[str, str, str]],
    final_evidence: dict[str, dict[str, Any]],
) -> None:
    commit, dirty = git_state()
    evidence_note = (
        "Reportable final summary groups included: " + ", ".join(sorted(final_evidence)) + "."
        if final_evidence
        else "Final answer-quality, baseline, component, and latency assets are omitted until their automatic summaries are reportable."
    )
    lines = [
        "# Querionyx Thesis Assets",
        "",
        "These assets are generated only from the current source tree, frozen benchmark files, the versioned chunk corpus, and reportable automatic summaries.",
        evidence_note,
        "",
        f"- Source commit: `{commit or 'unavailable'}`",
        f"- Working tree dirty at generation: `{'yes' if dirty else 'no'}`",
        "- Regenerate: `python scripts/generate_thesis_assets.py`",
        "",
        "## Figures",
        "",
        "| Asset | Caption | Placement |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| `{name}.png` / `.svg` | {caption} | {placement} |" for name, caption, placement in figure_descriptions)
    lines.extend(["", "## Tables", "", "| Asset | Rows |", "| --- | ---: |"])
    lines.extend(f"| `{name}.csv` / `.md` | {len(rows)} |" for name, _, rows in tables)
    lines.extend(
        [
            "",
            "## Reporting Boundary",
            "",
            "- Router metrics must name the exact curated or stress dataset.",
            "- No-Ollama readiness is static route/planner coverage, not semantic correctness.",
            "- Corpus page counts are distinct page identifiers represented in chunks.",
            "- Blocked claims in the claim-evidence matrix must not appear as findings.",
            "- Generate final performance assets only after `scripts/check_project_lock.py` marks the corresponding evidence artifacts reportable.",
            "",
        ]
    )
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def git_state() -> tuple[str | None, bool]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return commit, dirty
    except Exception:
        return None, True


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def format_cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def escape_markdown(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
