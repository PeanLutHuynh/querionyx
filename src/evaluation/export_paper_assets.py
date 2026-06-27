"""Export paper-ready tables, figures, and narrative snippets.

The exporter intentionally does not recompute benchmark metrics. It consumes
``docs/results/consolidated_results.json`` so the paper assets stay aligned with
the latest full evaluation run.
"""

from __future__ import annotations

import csv
import html
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_FILE = PROJECT_ROOT / "docs" / "results" / "consolidated_results.json"
PAPER_ASSETS_DIR = PROJECT_ROOT / "docs" / "paper_assets"
TABLE_DIR = PAPER_ASSETS_DIR / "tables"
CHART_DIR = PAPER_ASSETS_DIR / "figures"
NARRATIVE_FILE = PROJECT_ROOT / "docs" / "research" / "paper_narrative_snippets.md"

BLUE = "#2563eb"
TEAL = "#0f766e"
AMBER = "#d97706"
RED = "#dc2626"
SLATE = "#334155"
GRID = "#cbd5e1"
LIGHT = "#f8fafc"


def main() -> int:
    payload = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    tables = payload["tables"]

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    NARRATIVE_FILE.parent.mkdir(parents=True, exist_ok=True)

    export_tables(tables)
    export_figures(tables)
    export_narrative_snippets()

    print("Paper assets exported:")
    print(f"  Tables: {TABLE_DIR}")
    print(f"  Figures: {CHART_DIR}")
    print(f"  Narrative snippets: {NARRATIVE_FILE}")
    return 0


def export_tables(tables: dict[str, Any]) -> None:
    export_table_1_system_overview(tables)
    export_table_2_rag(tables["table2_rag"]["metrics"])
    export_table_3_sql(tables["table3_sql"]["metrics"])
    export_table_4_hybrid(tables["table4_hybrid"]["metrics"])
    export_table_5_ablation(tables["table6_ablation"]["metrics"])


def export_table_1_system_overview(tables: dict[str, Any]) -> None:
    router = tables["table1_router"]["metrics"]["adaptive_router"]
    rag_v3 = tables["table2_rag"]["metrics"]["rag_v3"]
    sql = tables["table3_sql"]["metrics"]
    hybrid = tables["table4_hybrid"]["metrics"]
    perf = tables["table5_performance"]["metrics"]

    rows = [
        ["Module", "Primary Metric", "Score", "Success Rate", "Latency (ms)", "Role"],
        [
            "Adaptive Router",
            "Intent accuracy",
            pct(router["accuracy"]),
            "N/A",
            f'{router["avg_latency_ms"]:.2f}',
            "Routes queries to RAG, SQL, or HYBRID",
        ],
        [
            "RAG V3",
            "Context precision",
            pct(rag_v3["context_precision"]),
            pct(rag_v3["success_rate"]),
            f'{rag_v3["avg_retrieval_latency_ms"]:.2f}',
            "Unstructured document retrieval",
        ],
        [
            "Text-to-SQL",
            "Execution accuracy",
            pct(sql["execution_accuracy"]),
            pct(sql["successful"] / sql["total"]),
            f'{sql["avg_latency_ms"]:.2f} ms',
            "Structured database querying",
        ],
        [
            "Hybrid Handler",
            "Hybrid correctness",
            pct(hybrid["hybrid_correctness"]),
            pct(hybrid["correct"] / hybrid["total"]),
            f'{hybrid["latency_p50_ms"]:.2f} / {hybrid["latency_p95_ms"]:.2f}',
            "Combines evidence from documents and SQL",
        ],
        [
            "End-to-End System",
            "Query success",
            pct(1.0 - perf["error_rate"]),
            pct(perf["successful_queries"] / perf["total_queries"]),
            f'{perf["latency_by_type"]["HYBRID"]["p50_ms"]:.2f} / {perf["latency_by_type"]["HYBRID"]["p95_ms"]:.2f}',
            "Full pipeline performance",
        ],
    ]
    write_table("table1_system_overview", rows)


def export_table_2_rag(metrics: dict[str, Any]) -> None:
    rows = [["Version", "Success Rate", "Precision", "Recall", "Latency (ms)", "Avg Chunks"]]
    for key, label in [("rag_v1", "V1"), ("rag_v2", "V2"), ("rag_v3", "V3")]:
        m = metrics[key]
        rows.append(
            [
                label,
                pct(m["success_rate"]),
                f'{m["context_precision"]:.4f}',
                f'{m["context_recall"]:.4f}',
                f'{m["avg_retrieval_latency_ms"]:.2f}',
                f'{m["avg_context_chunks"]:.2f}',
            ]
        )
    write_table("table2_rag_comparison", rows)


def export_table_3_sql(metrics: dict[str, Any]) -> None:
    errors = metrics["error_breakdown"]
    rows = [
        ["Metric", "Value"],
        ["Total SQL queries", str(metrics["total"])],
        ["Successful executions", str(metrics["successful"])],
        ["Execution accuracy", pct(metrics["execution_accuracy"])],
        ["Exact match rate", pct(metrics["exact_match_rate"])],
        ["Retry rate", pct(metrics["retry_rate"])],
        ["Average latency (ms)", f'{metrics["avg_latency_ms"]:.2f}'],
        ["Schema errors", str(errors.get("schema_error", 0))],
        ["Syntax errors", str(errors.get("syntax_error", 0))],
    ]
    write_table("table3_sql_evaluation", rows)


def export_table_4_hybrid(metrics: dict[str, Any]) -> None:
    breakdown = metrics["component_breakdown"]
    rows = [
        ["Metric", "Value"],
        ["Total HYBRID queries", str(metrics["total"])],
        ["Correct", str(metrics["correct"])],
        ["Hybrid correctness", pct(metrics["hybrid_correctness"])],
        ["Fallback rate", pct(metrics["fallback_rate"])],
        ["Latency P50 (ms)", f'{metrics["latency_p50_ms"]:.2f}'],
        ["Latency P95 (ms)", f'{metrics["latency_p95_ms"]:.2f}'],
        ["Full merge cases", str(breakdown.get("full_merge", 0))],
        ["RAG fallback cases", str(breakdown.get("rag_fallback", 0))],
        ["SQL fallback cases", str(breakdown.get("sql_fallback", 0))],
    ]
    write_table("table4_hybrid_evaluation", rows)


def export_table_5_ablation(metrics: dict[str, Any]) -> None:
    keep = [
        ("full_system", "Full System"),
        ("no_adaptive_router", "No Adaptive Router"),
        ("dense_only", "Dense Only"),
        ("hybrid_disabled", "Hybrid Disabled"),
    ]
    baseline = metrics["full_system"]["hybrid_correctness"]
    rows = [["Configuration", "Correctness", "Context Recall", "Router Accuracy", "Latency (ms)", "Correctness Drop"]]
    for key, label in keep:
        m = metrics[key]
        drop = 0.0 if key == "full_system" else (baseline - m["hybrid_correctness"]) / baseline
        rows.append(
            [
                label,
                f'{m["hybrid_correctness"]:.4f}',
                f'{m["context_recall"]:.4f}',
                f'{m["router_hybrid_accuracy"]:.4f}',
                f'{m["avg_latency_ms"]:.2f}',
                "Baseline" if key == "full_system" else pct(drop),
            ]
        )
    write_table("table5_ablation_study", rows)


def export_figures(tables: dict[str, Any]) -> None:
    export_figure_1_architecture()
    export_figure_2_rag(tables["table2_rag"]["metrics"])
    export_figure_3_router_heatmap(tables["table1_router"]["metrics"]["adaptive_router"]["confusion_matrix"])
    export_figure_4_ablation(tables["table6_ablation"]["metrics"])


def export_figure_1_architecture() -> None:
    """Export the reviewer-requested algorithmic workflow.

    The paper originally used this slot for a component architecture diagram.
    Reviewer feedback asks for the actual query-processing workflow, so Figure 1
    is now a flowchart equivalent of Algorithm 1.
    """

    width, height = 1800, 930
    parts = svg_header(width, height)
    parts.append(text(90, 102, "Input: user_query q", size=22, weight="600"))
    parts.append(text(90, 136, "Output: grounded_answer a", size=22, weight="600"))

    boxes = {
        "query": ("USER QUERY\nq", 80, 365, 250, 86),
        "router": ("ADAPTIVE ROUTER\nintent + routing scores", 390, 345, 405, 120),
        "rag": ("RAG\nRAGPipeline(q)", 875, 155, 380, 106),
        "sql": ("SQL\nTextToSQL(q)", 875, 345, 380, 106),
        "hybrid": ("HYBRID\nasync RAG + SQL", 875, 535, 465, 112),
        "fusion": ("BOTH SUCCEED\nFusionLayer", 1370, 490, 340, 106),
        "fallback": ("ONE BRANCH FAILS\nFallback", 1370, 635, 340, 106),
        "answer": ("GROUNDED ANSWER\na", 1510, 325, 260, 106),
        "log": ("TRACE LOG SIDE CHANNEL\nrouting, branch status, fallback\nevidence, SQL, latency", 560, 770, 760, 110),
    }

    for key, (label, x, y, w, h) in boxes.items():
        fill = "#eff6ff" if key in {"router", "fusion", "answer"} else "#f8fafc"
        stroke = BLUE if key in {"router", "fusion", "answer"} else SLATE
        if key == "log":
            fill = "#fffbeb"
            stroke = AMBER
        parts.append(rect(x, y, w, h, fill=fill, stroke=stroke, radius=8))
        add_multiline_text(parts, x + w / 2, y + h / 2, label, size=19, weight="700", anchor="middle")

    arrows = [
        ((330, 408), (390, 408)),
        ((795, 405), (875, 208)),
        ((795, 405), (875, 398)),
        ((795, 405), (875, 591)),
        ((1255, 208), (1510, 378)),
        ((1255, 398), (1510, 378)),
        ((1340, 591), (1370, 543)),
        ((1340, 591), (1370, 688)),
        ((1710, 543), (1760, 378)),
        ((1710, 688), (1760, 378)),
    ]
    for start, end in arrows:
        parts.append(arrow(start, end))

    trace_arrows = [
        ((590, 465), (720, 770)),
        ((1065, 261), (800, 770)),
        ((1065, 451), (890, 770)),
        ((1105, 647), (995, 770)),
        ((1540, 741), (1180, 770)),
        ((1640, 431), (1260, 770)),
    ]
    for start, end in trace_arrows:
        parts.append(dashed_arrow(start, end, AMBER))

    parts.append(svg_footer())
    write_svg("figure1_system_architecture", parts)
    export_figure_1_architecture_png()


def export_figure_2_rag(metrics: dict[str, Any]) -> None:
    labels = ["V1", "V2", "V3"]

    precision = [metrics[k]["context_precision"] for k in ["rag_v1", "rag_v2", "rag_v3"]]
    recall = [metrics[k]["context_recall"] for k in ["rag_v1", "rag_v2", "rag_v3"]]
    latency = [metrics[k]["avg_retrieval_latency_ms"] for k in ["rag_v1", "rag_v2", "rag_v3"]]

    width, height = 860, 540  # thêm chút chiều cao cho legend
    left = 80
    top = 90
    chart_w = 680
    chart_h = 320

    group_w = chart_w / len(labels)
    bar_w = 34

    # Tăng padding phía trên cho đường latency + label
    max_latency = max(latency) * 1.35

    parts = svg_header(width, height)

    # Trục
    draw_axes(parts, left, top, chart_w, chart_h, "Quality Score", "RAG Version")

    # ----- Bars + labels -----
    for i, label in enumerate(labels):
        cx = left + group_w * i + group_w / 2

        # Precision
        p = precision[i]
        p_h = p * chart_h
        p_x = cx - 20 - bar_w
        p_y = top + chart_h - p_h

        parts.append(
            rect(
                p_x,
                p_y,
                bar_w,
                p_h,
                fill=BLUE,
                stroke=BLUE,
                radius=3,
            )
        )
        # label giữa bar precision
        parts.append(
            text(
                p_x + bar_w / 2,
                p_y - 8,
                f"{p:.3f}",
                size=10,
                anchor="middle",
            )
        )

        # Recall
        r = recall[i]
        r_h = r * chart_h
        r_x = cx + 20
        r_y = top + chart_h - r_h

        parts.append(
            rect(
                r_x,
                r_y,
                bar_w,
                r_h,
                fill=TEAL,
                stroke=TEAL,
                radius=3,
            )
        )
        # label giữa bar recall
        parts.append(
            text(
                r_x + bar_w / 2,
                r_y - 8,
                f"{r:.3f}",
                size=10,
                anchor="middle",
            )
        )

        # Nhãn X
        parts.append(
            text(
                cx,
                top + chart_h + 28,
                label,
                size=12,
                weight="600",
                anchor="middle",
            )
        )

    # ----- Latency line + labels -----
    points: list[tuple[float, float]] = []
    label_offset = chart_h * 0.08  # khoảng cách label so với điểm

    for i, value in enumerate(latency):
        cx = left + group_w * i + group_w / 2
        y = top + chart_h - (value / max_latency) * chart_h

        points.append((cx, y))
        parts.append(circle(cx, y, 5, AMBER))

        parts.append(
            text(
                cx,
                y - label_offset,
                f"{value:.0f} ms",
                size=10,
                anchor="middle",
            )
        )

    parts.append(polyline(points, AMBER))

    # ----- Legend căn giữa dưới chart -----
    legend_items = [
        (BLUE, "Precision"),
        (TEAL, "Recall"),
        (AMBER, "Latency"),
    ]
    item_width = 82  # 16 (ô) + 6 gap + ~60 text
    total_legend_width = len(legend_items) * item_width
    chart_center_x = left + chart_w / 2
    legend_start_x = int(chart_center_x - total_legend_width / 2)

    draw_legend(
        parts,
        legend_items,
        x=legend_start_x,
        y=height - 40,
    )

    parts.append(svg_footer())
    write_svg("figure2_rag_comparison", parts)


def export_figure_1_architecture_png() -> None:
    """Export a 300 DPI raster companion for Word workflows."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    except ModuleNotFoundError:
        return

    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=300)
    ax.set_xlim(0, 1800)
    ax.set_ylim(930, 0)
    ax.axis("off")

    def box(key: str, label: str, x: int, y: int, w: int, h: int) -> None:
        fill = "#eff6ff" if key in {"router", "fusion", "answer"} else "#f8fafc"
        edge = BLUE if key in {"router", "fusion", "answer"} else SLATE
        if key == "log":
            fill = "#fffbeb"
            edge = AMBER
        patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=10", linewidth=1.8, edgecolor=edge, facecolor=fill)
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#0f172a", linespacing=1.25)

    def arr(start: tuple[int, int], end: tuple[int, int], dashed: bool = False) -> None:
        color = AMBER if dashed else SLATE
        style = (0, (5, 5)) if dashed else "solid"
        patch = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13, linewidth=1.6, linestyle=style, color=color)
        ax.add_patch(patch)

    ax.text(90, 102, "Input: user_query q", ha="left", va="center", fontsize=12.5, fontweight="bold")
    ax.text(90, 136, "Output: grounded_answer a", ha="left", va="center", fontsize=12.5, fontweight="bold")

    boxes = {
        "query": ("USER QUERY\nq", 80, 365, 250, 86),
        "router": ("ADAPTIVE ROUTER\nintent + routing scores", 390, 345, 405, 120),
        "rag": ("RAG\nRAGPipeline(q)", 875, 155, 380, 106),
        "sql": ("SQL\nTextToSQL(q)", 875, 345, 380, 106),
        "hybrid": ("HYBRID\nasync RAG + SQL", 875, 535, 465, 112),
        "fusion": ("BOTH SUCCEED\nFusionLayer", 1370, 490, 340, 106),
        "fallback": ("ONE BRANCH FAILS\nFallback", 1370, 635, 340, 106),
        "answer": ("GROUNDED ANSWER\na", 1510, 325, 260, 106),
        "log": ("TRACE LOG SIDE CHANNEL\nrouting, branch status, fallback\nevidence, SQL, latency", 560, 770, 760, 110),
    }
    for key, values in boxes.items():
        box(key, *values)

    for start, end in [
        ((330, 408), (390, 408)),
        ((795, 405), (875, 208)),
        ((795, 405), (875, 398)),
        ((795, 405), (875, 591)),
        ((1255, 208), (1510, 378)),
        ((1255, 398), (1510, 378)),
        ((1340, 591), (1370, 543)),
        ((1340, 591), (1370, 688)),
        ((1710, 543), (1760, 378)),
        ((1710, 688), (1760, 378)),
    ]:
        arr(start, end)

    for start, end in [
        ((590, 465), (720, 770)),
        ((1065, 261), (800, 770)),
        ((1065, 451), (890, 770)),
        ((1105, 647), (995, 770)),
        ((1540, 741), (1180, 770)),
        ((1640, 431), (1260, 770)),
    ]:
        arr(start, end, dashed=True)

    fig.savefig(CHART_DIR / "figure1_system_architecture.png", dpi=300, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def export_figure_3_router_heatmap(matrix_payload: dict[str, dict[str, int]]) -> None:
    labels = ["RAG", "SQL", "HYBRID"]
    matrix = [[matrix_payload.get(actual, {}).get(pred, 0) for pred in labels] for actual in labels]
    max_value = max(max(row) for row in matrix) or 1

    width, height = 1400, 1100
    left, top, cell = 315, 215, 230
    parts = svg_header(width, height)
    parts.append(text(left + cell * 1.5, 145, "Predicted Intent", size=30, weight="700", anchor="middle"))
    parts.append(text(90, top + cell * 1.5, "Ground Truth", size=30, weight="700", anchor="middle", rotate=-90))
    for i, actual in enumerate(labels):
        parts.append(text(left - 34, top + i * cell + cell / 2 + 10, actual, size=28, weight="700", anchor="end"))
        parts.append(text(left + i * cell + cell / 2, top - 30, labels[i], size=28, weight="700", anchor="middle"))
        for j, _pred in enumerate(labels):
            value = matrix[i][j]
            strength = value / max_value
            fill = heat_color(strength, row=i, col=j)
            x, y = left + j * cell, top + i * cell
            parts.append(rect(x, y, cell, cell, fill=fill, stroke="#ffffff", radius=0))
            text_color = "#ffffff" if strength > 0.55 else "#0f172a"
            parts.append(text(x + cell / 2, y + cell / 2 + 18, str(value), size=58, weight="700", anchor="middle", fill=text_color))
    parts.append(svg_footer())
    write_svg("figure3_router_confusion_matrix", parts)
    export_figure_3_router_heatmap_png(labels, matrix)


def export_figure_4_ablation(metrics: dict[str, Any]) -> None:
    baseline = metrics["full_system"]["hybrid_correctness"]
    items = [
        ("No Router", metrics["no_adaptive_router"]["hybrid_correctness"]),
        ("Dense Only", metrics["dense_only"]["hybrid_correctness"]),
        ("Hybrid Disabled", metrics["hybrid_disabled"]["hybrid_correctness"]),
        ("Recursive Chunking", metrics["recursive_chunking"]["hybrid_correctness"]),
    ]
    drops = [(label, (baseline - score) / baseline * 100) for label, score in items]

    width, height = 1500, 950
    left, top, chart_w, chart_h = 165, 130, 1060, 540
    max_drop = max(value for _, value in drops) * 1.2
    parts = svg_header(width, height)
    draw_axes(parts, left, top, chart_w, chart_h, "Correctness Drop (%)", "Configuration", axis_label_size=20)
    bar_w = 100
    gap = chart_w / len(drops)
    line_points: list[tuple[float, float]] = []
    for i, (label, value) in enumerate(drops):
        h = (value / max_drop) * chart_h
        x = left + gap * i + gap / 2 - bar_w / 2
        y = top + chart_h - h
        color = RED if "Hybrid" in label else BLUE
        parts.append(rect(x, y, bar_w, h, fill=color, stroke=color, radius=2))
        parts.append(text(x + bar_w / 2, y - 20, f"-{value:.1f}%", size=26, weight="700", anchor="middle"))
        add_multiline_text(parts, x + bar_w / 2, top + chart_h + 55, label.replace(" ", "\n"), size=22, weight="700", anchor="middle")
        line_points.append((x + bar_w / 2, y))
    parts.append(polyline(line_points, AMBER))
    for x, y in line_points:
        parts.append(circle(x, y, 7, AMBER))
    draw_legend(parts, [(BLUE, "Correctness drop"), (RED, "Largest drop"), (AMBER, "Drop trend")], x=335, y=690)
    parts.append(svg_footer())
    write_svg("figure4_ablation_impact", parts)
    export_figure_4_ablation_png(drops)


def export_figure_3_router_heatmap_png(labels: list[str], matrix: list[list[int]]) -> None:
    """Export a 300 DPI raster companion for Word/PDF workflows."""
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        return

    fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
    import matplotlib.colors as mcolors

    max_value = max(max(row) for row in matrix) or 1
    colors = [
        [mcolors.to_rgb(heat_color(value / max_value, row=i, col=j)) for j, value in enumerate(row)]
        for i, row in enumerate(matrix)
    ]
    ax.imshow(colors)
    ax.set_xticks(range(len(labels)), labels=labels, fontsize=18, fontweight="bold")
    ax.set_yticks(range(len(labels)), labels=labels, fontsize=18, fontweight="bold")
    ax.set_xlabel("Predicted Intent", fontsize=22, fontweight="bold", labelpad=28)
    ax.set_ylabel("Ground Truth", fontsize=22, fontweight="bold", labelpad=18)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            color = "white" if value > max(max(r) for r in matrix) * 0.55 else "#0f172a"
            ax.text(j, i, str(value), ha="center", va="center", color=color, fontsize=34, fontweight="bold")
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.18, left=0.20)
    fig.savefig(CHART_DIR / "figure3_router_confusion_matrix.png", dpi=300)
    plt.close(fig)


def export_figure_4_ablation_png(drops: list[tuple[str, float]]) -> None:
    """Export the ablation chart as a true matplotlib chart, not a screenshot."""
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        return

    labels = [label.replace(" ", "\n") for label, _ in drops]
    values = [value for _, value in drops]
    colors = [RED if "Hybrid" in label else "#4da6ff" for label, _ in drops]

    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=300)
    bars = ax.bar(labels, values, color=colors, width=0.52)
    ax.plot(labels, values, color=AMBER, marker="o", linewidth=3.2, markersize=8)
    ax.set_ylabel("Correctness Drop (%)", fontsize=18, fontweight="bold")
    ax.set_xlabel("Configuration", fontsize=18, fontweight="bold", labelpad=16)
    ax.set_ylim(0, max(values) * 1.25)
    ax.tick_params(axis="both", labelsize=15)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.03,
            f"-{value:.1f}%",
            ha="center",
            fontsize=17,
            fontweight="bold",
        )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.20, left=0.13)
    fig.savefig(CHART_DIR / "figure4_ablation_impact.png", dpi=300)
    plt.close(fig)


def export_narrative_snippets() -> None:
    snippets = """# Paper Narrative Snippets

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
"""
    NARRATIVE_FILE.write_text(snippets, encoding="utf-8")


def write_table(name: str, rows: list[list[str]]) -> None:
    csv_path = TABLE_DIR / f"{name}.csv"
    md_path = TABLE_DIR / f"{name}.md"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    md_path.write_text(to_markdown(rows), encoding="utf-8")


def to_markdown(rows: list[list[str]]) -> str:
    header = rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines) + "\n"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">',
        '<path d="M0,0 L0,6 L9,3 z" fill="#334155" />',
        "</marker>",
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]


def svg_footer() -> str:
    return "</svg>\n"


def write_svg(name: str, parts: Sequence[str]) -> None:
    (CHART_DIR / f"{name}.svg").write_text("\n".join(parts), encoding="utf-8")


def rect(x: float, y: float, w: float, h: float, fill: str, stroke: str, radius: int = 6) -> str:
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'


def text(
    x: float,
    y: float,
    value: str,
    size: int = 12,
    weight: str = "400",
    anchor: str = "start",
    fill: str = "#0f172a",
    rotate: int | None = None,
) -> str:
    transform = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}"{transform}>{html.escape(value)}</text>'
    )


def add_multiline_text(
    parts: list[str],
    x: float,
    y: float,
    value: str,
    size: int = 12,
    weight: str = "400",
    anchor: str = "start",
    fill: str = "#0f172a",
    line_height: float = 1.25,
) -> None:
    lines = value.split("\n")
    start_y = y - (len(lines) - 1) * size * line_height / 2
    for idx, line_text in enumerate(lines):
        parts.append(text(x, start_y + idx * size * line_height + size * 0.35, line_text, size=size, weight=weight, anchor=anchor, fill=fill))


def line(x1: float, y1: float, x2: float, y2: float, stroke: str = GRID, width: float = 1.2) -> str:
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"/>'


def arrow(start: tuple[float, float], end: tuple[float, float]) -> str:
    return (
        f'<line x1="{start[0]:.1f}" y1="{start[1]:.1f}" x2="{end[0]:.1f}" y2="{end[1]:.1f}" '
        'stroke="#334155" stroke-width="1.8" marker-end="url(#arrow)"/>'
    )


def dashed_arrow(start: tuple[float, float], end: tuple[float, float], stroke: str) -> str:
    return (
        f'<line x1="{start[0]:.1f}" y1="{start[1]:.1f}" x2="{end[0]:.1f}" y2="{end[1]:.1f}" '
        f'stroke="{stroke}" stroke-width="1.4" stroke-dasharray="6 6" marker-end="url(#arrow)"/>'
    )


def circle(x: float, y: float, r: float, fill: str) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="#ffffff" stroke-width="1"/>'


def polyline(points: Iterable[tuple[float, float]], stroke: str) -> str:
    point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{point_text}" fill="none" stroke="{stroke}" stroke-width="2.5"/>'


def draw_axes(
    parts: list[str],
    left: int,
    top: int,
    chart_w: int,
    chart_h: int,
    y_label: str,
    x_label: str,
    axis_label_size: int = 12,
) -> None:
    parts.append(line(left, top, left, top + chart_h, SLATE, 1.5))
    parts.append(line(left, top + chart_h, left + chart_w, top + chart_h, SLATE, 1.5))
    for i in range(1, 5):
        y = top + chart_h - chart_h * i / 4
        parts.append(line(left, y, left + chart_w, y, GRID, 0.8))
    offset = 62 if axis_label_size > 12 else 48
    x_offset = 78 if axis_label_size > 12 else 58
    weight = "700" if axis_label_size > 12 else "600"
    parts.append(text(left - offset, top + chart_h / 2, y_label, size=axis_label_size, weight=weight, anchor="middle", rotate=-90))
    parts.append(text(left + chart_w / 2, top + chart_h + x_offset, x_label, size=axis_label_size, weight=weight, anchor="middle"))


def draw_legend(parts: list[str], items: list[tuple[str, str]], x: int, y: int) -> None:
    offset = 0
    for color, label in items:
        parts.append(rect(x + offset, y, 16, 16, fill=color, stroke=color, radius=2))
        parts.append(text(x + offset + 22, y + 13, label, size=11))
        offset += 92


def heat_color(strength: float, row: int = 0, col: int = 0) -> str:
    strength = max(0.0, min(1.0, strength))
    start = (239, 246, 255)
    end = (37, 99, 235)
    if strength == 0.0:
        # Keep zero values visibly light, but avoid identical cells in print.
        strength = 0.015 * (row + col)
    rgb = tuple(math.floor(start[i] + (end[i] - start[i]) * strength) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


if __name__ == "__main__":
    raise SystemExit(main())
