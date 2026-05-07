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
            f'{sql["avg_latency_ms"]:.2f}',
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
    boxes = [
        ("User Query", 330, 30, 180, 50),
        ("Adaptive Router", 330, 120, 180, 50),
        ("RAG Pipeline", 90, 220, 180, 60),
        ("SQL Pipeline", 330, 220, 180, 60),
        ("HYBRID Handler", 570, 220, 180, 60),
        ("Fusion Layer", 330, 340, 180, 55),
        ("Grounded Answer", 330, 450, 180, 50),
    ]
    arrows = [
        ((420, 80), (420, 120)),
        ((420, 170), (180, 220)),
        ((420, 170), (420, 220)),
        ((420, 170), (660, 220)),
        ((180, 280), (420, 340)),
        ((420, 280), (420, 340)),
        ((660, 280), (420, 340)),
        ((420, 395), (420, 450)),
    ]
    parts = svg_header(840, 540)
    for label, x, y, w, h in boxes:
        fill = LIGHT if label not in {"Adaptive Router", "Fusion Layer"} else "#eff6ff"
        parts.append(rect(x, y, w, h, fill=fill, stroke=BLUE if label in {"Adaptive Router", "Fusion Layer"} else SLATE))
        parts.append(text(x + w / 2, y + h / 2 + 5, label, size=14, weight="600", anchor="middle"))
    for start, end in arrows:
        parts.append(arrow(start, end))
    parts.append(svg_footer())
    write_svg("figure1_system_architecture", parts)


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


def draw_legend(parts: list[str], items: list[tuple[str, str]], x: int, y: int) -> None:
    offset = 0
    item_width = 82
    for color, label in items:
        # ô màu
        parts.append(rect(x + offset, y, 16, 16, fill=color, stroke=color, radius=2))
        # text căn theo baseline ô màu
        parts.append(text(x + offset + 22, y + 13, label, size=11))
        offset += item_width


def export_figure_3_router_heatmap(matrix_payload: dict[str, dict[str, int]]) -> None:
    labels = ["RAG", "SQL", "HYBRID"]
    matrix = [[matrix_payload.get(actual, {}).get(pred, 0) for pred in labels] for actual in labels]
    max_value = max(max(row) for row in matrix) or 1

    width, height = 620, 520
    left, top, cell = 150, 100, 105
    parts = svg_header(width, height)
    parts.append(text(left + cell * 1.5, 70, "Predicted Intent", size=13, weight="600", anchor="middle"))
    parts.append(text(38, top + cell * 1.5, "Ground Truth", size=13, weight="600", anchor="middle", rotate=-90))
    for i, actual in enumerate(labels):
        parts.append(text(left - 16, top + i * cell + cell / 2 + 5, actual, size=12, weight="600", anchor="end"))
        parts.append(text(left + i * cell + cell / 2, top - 15, labels[i], size=12, weight="600", anchor="middle"))
        for j, _pred in enumerate(labels):
            value = matrix[i][j]
            strength = value / max_value
            fill = heat_color(strength)
            x, y = left + j * cell, top + i * cell
            parts.append(rect(x, y, cell, cell, fill=fill, stroke="#ffffff", radius=0))
            text_color = "#ffffff" if strength > 0.55 else "#0f172a"
            parts.append(text(x + cell / 2, y + cell / 2 + 7, str(value), size=20, weight="700", anchor="middle", fill=text_color))
    parts.append(svg_footer())
    write_svg("figure3_router_confusion_matrix", parts)


def export_figure_4_ablation(metrics: dict[str, Any]) -> None:
    baseline = metrics["full_system"]["hybrid_correctness"]
    items = [
        ("No Router", metrics["no_adaptive_router"]["hybrid_correctness"]),
        ("Dense Only", metrics["dense_only"]["hybrid_correctness"]),
        ("Hybrid Disabled", metrics["hybrid_disabled"]["hybrid_correctness"]),
        ("Recursive Chunking", metrics["recursive_chunking"]["hybrid_correctness"]),
    ]
    drops = [(label, (baseline - score) / baseline * 100) for label, score in items]

    width, height = 820, 460
    left, top, chart_w, chart_h = 85, 70, 650, 290
    max_drop = max(value for _, value in drops) * 1.2
    parts = svg_header(width, height)
    draw_axes(parts, left, top, chart_w, chart_h, "Correctness Drop (%)", "Configuration")
    bar_w = 85
    gap = chart_w / len(drops)
    for i, (label, value) in enumerate(drops):
        h = (value / max_drop) * chart_h
        x = left + gap * i + gap / 2 - bar_w / 2
        y = top + chart_h - h
        color = RED if "Hybrid" in label else BLUE
        parts.append(rect(x, y, bar_w, h, fill=color, stroke=color, radius=2))
        parts.append(text(x + bar_w / 2, y - 8, f"-{value:.1f}%", size=11, weight="600", anchor="middle"))
        parts.append(text(x + bar_w / 2, top + chart_h + 28, label, size=11, anchor="middle"))
    parts.append(svg_footer())
    write_svg("figure4_ablation_impact", parts)


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


def line(x1: float, y1: float, x2: float, y2: float, stroke: str = GRID, width: float = 1.2) -> str:
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}"/>'


def arrow(start: tuple[float, float], end: tuple[float, float]) -> str:
    return (
        f'<line x1="{start[0]:.1f}" y1="{start[1]:.1f}" x2="{end[0]:.1f}" y2="{end[1]:.1f}" '
        'stroke="#334155" stroke-width="1.8" marker-end="url(#arrow)"/>'
    )


def circle(x: float, y: float, r: float, fill: str) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="#ffffff" stroke-width="1"/>'


def polyline(points: Iterable[tuple[float, float]], stroke: str) -> str:
    point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{point_text}" fill="none" stroke="{stroke}" stroke-width="2.5"/>'


def draw_axes(parts: list[str], left: int, top: int, chart_w: int, chart_h: int, y_label: str, x_label: str) -> None:
    parts.append(line(left, top, left, top + chart_h, SLATE, 1.5))
    parts.append(line(left, top + chart_h, left + chart_w, top + chart_h, SLATE, 1.5))
    for i in range(1, 5):
        y = top + chart_h - chart_h * i / 4
        parts.append(line(left, y, left + chart_w, y, GRID, 0.8))
    parts.append(text(left - 48, top + chart_h / 2, y_label, size=12, weight="600", anchor="middle", rotate=-90))
    parts.append(text(left + chart_w / 2, top + chart_h + 58, x_label, size=12, weight="600", anchor="middle"))


def draw_legend(parts: list[str], items: list[tuple[str, str]], x: int, y: int) -> None:
    offset = 0
    for color, label in items:
        parts.append(rect(x + offset, y, 16, 16, fill=color, stroke=color, radius=2))
        parts.append(text(x + offset + 22, y + 13, label, size=11))
        offset += 92


def heat_color(strength: float) -> str:
    strength = max(0.0, min(1.0, strength))
    start = (239, 246, 255)
    end = (37, 99, 235)
    rgb = tuple(math.floor(start[i] + (end[i] - start[i]) * strength) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


if __name__ == "__main__":
    raise SystemExit(main())
