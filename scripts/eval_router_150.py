"""Evaluate RuleBasedRouter on the expanded 150-query set.

Loads `data/test_queries/eval_150_queries.json`, runs `RuleBasedRouter.classify`
and prints per-intent and overall accuracy and a confusion matrix.

Run:
  python scripts/eval_router_150.py
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from src.router.rule_based_router import RuleBasedRouter


def load_dataset(path: Path) -> list:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload.get("queries", payload)


def normalize_intent(s: str) -> str:
    return (s or "").upper()


def main():
    path = PROJECT_ROOT / "data" / "test_queries" / "eval_150_queries.json"
    if not path.exists():
        print(f"Dataset not found: {path}")
        raise SystemExit(2)

    queries = load_dataset(path)
    router = RuleBasedRouter()

    intents = ["RAG", "SQL", "HYBRID"]
    confusion: Dict[str, Dict[str, int]] = {a: {b: 0 for b in intents} for a in intents}
    totals = {k: 0 for k in intents}
    correct = {k: 0 for k in intents}

    for q in queries:
        expected = normalize_intent(q.get("ground_truth_intent", "RAG"))
        res = router.classify(q.get("question", ""))
        pred = normalize_intent(res.intent)
        if expected not in intents:
            expected = "RAG"
        if pred not in intents:
            pred = "RAG"

        confusion[expected][pred] += 1
        totals[expected] += 1
        if expected == pred:
            correct[expected] += 1

    total_queries = sum(totals.values())
    total_correct = sum(correct.values())

    print("\nRouter-only evaluation results")
    print(f"Total queries: {total_queries}")
    print(f"Overall accuracy: {total_correct}/{total_queries} = {total_correct/total_queries:.4f}\n")

    for intent in intents:
        t = totals[intent]
        c = correct[intent]
        acc = (c / t) if t > 0 else 0.0
        print(f"{intent}: {c}/{t} = {acc:.4f}")

    print("\nConfusion matrix (rows=expected, cols=predicted):")
    hdr = "\t" + "\t".join(intents)
    print(hdr)
    for a in intents:
        row = a + "\t" + "\t".join(str(confusion[a][b]) for b in intents)
        print(row)


if __name__ == "__main__":
    main()
