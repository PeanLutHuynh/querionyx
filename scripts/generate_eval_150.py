"""Generate `data/test_queries/eval_150_queries.json` by extending the existing 90-query set.

This script loads `data/test_queries/eval_90_queries.json`, appends 60 new queries
(20 RAG, 20 SQL, 20 HYBRID) focused on FPT, Vinamilk, Masan (2023-2025) and Northwind
SQL edge cases, and writes the expanded dataset to `data/test_queries/eval_150_queries.json`.

Run locally:
  python scripts/generate_eval_150.py
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "test_queries" / "eval_90_queries.json"
DST = ROOT / "data" / "test_queries" / "eval_150_queries.json"


def load_base():
    with SRC.open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    return payload


def make_rag_items(start_idx: int, count: int) -> list:
    companies = ["FPT", "Vinamilk", "Masan"]
    years = [2023, 2024, 2025]
    items = []
    i = start_idx
    for n in range(count):
        comp = companies[n % len(companies)]
        year = years[n % len(years)]
        q = {
            "id": f"unstr_{i:03d}",
            "question": f"{comp} có những điểm nổi bật nào trong báo cáo thường niên năm {year}?",
            "ground_truth_intent": "RAG",
            "ground_truth_answer": f"Tìm trong báo cáo {comp} {year} - tóm tắt điểm nổi bật, chỉ số, sự kiện",
            "source_hint": "annual_reports",
            "difficulty": "medium",
        }
        items.append(q)
        i += 1
    return items


def make_sql_items(start_idx: int, count: int) -> list:
    templates = [
        ("SELECT COUNT(*) FROM orders WHERE EXTRACT(YEAR FROM order_date) = {year};", "hard"),
        ("SELECT customer_id, SUM(quantity * unit_price) as total FROM order_details od JOIN orders o ON od.order_id=o.order_id GROUP BY customer_id ORDER BY total DESC LIMIT {n};", "hard"),
        ("SELECT p.product_name, SUM(od.quantity) AS total_qty FROM order_details od JOIN products p ON od.product_id = p.product_id GROUP BY p.product_name ORDER BY total_qty DESC LIMIT {n};", "medium"),
        ("SELECT EXTRACT(YEAR FROM order_date) as year, COUNT(*) FROM orders GROUP BY year ORDER BY year;", "medium"),
        ("SELECT supplier_id, COUNT(*) FROM products GROUP BY supplier_id HAVING COUNT(*) > {n};", "hard"),
    ]
    items = []
    i = start_idx
    for n in range(count):
        tpl, diff = templates[n % len(templates)]
        if "{year}" in tpl:
            year = 2023 + (n % 3)
            sql = tpl.format(year=year)
            qtext = f"Tổng số đơn hàng trong năm {year} là bao nhiêu?"
        elif "{n}" in tpl:
            sql = tpl.format(n=5)
            qtext = "Top khách hàng theo tổng chi tiêu (top N) là ai?"
        else:
            sql = tpl.format(n=5)
            qtext = "Truy vấn doanh thu/đơn hàng/phân nhóm theo yêu cầu"

        items.append(
            {
                "id": f"str_{i:03d}",
                "question": qtext,
                "ground_truth_intent": "SQL",
                "ground_truth_answer": sql,
                "source_hint": "northwind_db",
                "difficulty": diff,
            }
        )
        i += 1
    return items


def make_hybrid_items(start_idx: int, count: int) -> list:
    companies = ["FPT", "Vinamilk", "Masan"]
    years = [2023, 2024, 2025]
    sql_examples = [
        "SELECT COUNT(*) FROM orders;",
        "SELECT SUM(units_in_stock) FROM products;",
        "SELECT customer_id, SUM(quantity*unit_price) as total FROM order_details GROUP BY customer_id ORDER BY total DESC LIMIT 1;",
        "SELECT EXTRACT(YEAR FROM order_date) as year, COUNT(*) FROM orders GROUP BY year;",
    ]
    items = []
    i = start_idx
    for n in range(count):
        comp = companies[n % len(companies)]
        year = years[n % len(years)]
        sql = sql_examples[n % len(sql_examples)]
        q = {
            "id": f"hyb_{i:03d}",
            "question": f"Theo báo cáo {comp} năm {year}, chiến lược chính là gì và hiện có bao nhiêu đơn hàng trong hệ thống?",
            "ground_truth_intent": "HYBRID",
            "ground_truth_answer": f"RAG: tìm chiến lược {comp} {year}; SQL: {sql}",
            "source_hint": "annual_reports + northwind_db",
            "difficulty": "hard" if (n % 3 == 0) else "medium",
        }
        items.append(q)
        i += 1
    return items


def main():
    base = load_base()
    queries = base.get("queries", [])

    # Count existing families
    rag_count = sum(1 for q in queries if q.get("ground_truth_intent") == "RAG")
    sql_count = sum(1 for q in queries if q.get("ground_truth_intent") == "SQL")
    hyb_count = sum(1 for q in queries if q.get("ground_truth_intent") == "HYBRID")

    # We want 50/50/50 total
    need_rag = 50 - rag_count
    need_sql = 50 - sql_count
    need_hyb = 50 - hyb_count

    new_items = []
    if need_rag > 0:
        start_idx = rag_count + 1
        new_items.extend(make_rag_items(start_idx, need_rag))
    if need_sql > 0:
        start_idx = sql_count + 1
        new_items.extend(make_sql_items(start_idx, need_sql))
    if need_hyb > 0:
        start_idx = hyb_count + 1
        new_items.extend(make_hybrid_items(start_idx, need_hyb))

    combined = {
        "metadata": {
            "total_queries": len(queries) + len(new_items),
            "distribution": {"RAG": 50, "SQL": 50, "HYBRID": 50},
            "created_date": date.today().isoformat(),
            "purpose": "Expanded router evaluation set - 150 queries (balanced)"
        },
        "queries": queries + new_items,
    }

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {DST} ({combined['metadata']['total_queries']} queries)")


if __name__ == "__main__":
    main()
