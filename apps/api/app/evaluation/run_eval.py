"""Evaluation harness — run the analysis pipeline against a gold dataset.

Loads evaluation items from ``data/gold_v1.json``, runs each through
``analyze_service.run_analysis()`` **directly** (no HTTP), collects
predicted pillars, and computes multi-label precision / recall / F1
per pillar plus an overall micro-average.

Results are printed to the console and written to a timestamped JSON
file in ``evaluation/output/``.

Usage::

    cd apps/api
    python -m app.evaluation.run_eval

Or with a custom dataset path::

    python -m app.evaluation.run_eval --dataset path/to/gold.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.evaluation.gold_dataset_schema import GoldDataset, GoldItem
from app.models.enums import CurriculumItemType
from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.services.analyze_service import run_analysis

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_DATASET = _THIS_DIR / "data" / "gold_v1.json"
_OUTPUT_DIR = _THIS_DIR / "output"

#: Minimum pillar score to consider a pillar "predicted"
_PILLAR_SCORE_THRESHOLD: float = 0.1


# =====================================================================
# Metrics helpers
# =====================================================================


def _compute_metrics(
    gold: set[str],
    predicted: set[str],
) -> dict[str, float]:
    """Compute precision, recall, F1 for a single item."""
    tp = len(gold & predicted)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return {"precision": precision, "recall": recall, "f1": f1}


def _compute_micro_average(
    per_item: list[dict[str, set[str]]],
) -> dict[str, float]:
    """Compute micro-averaged P/R/F1 across all items."""
    total_tp = 0
    total_predicted = 0
    total_gold = 0

    for item in per_item:
        gold = item["gold"]
        predicted = item["predicted"]
        total_tp += len(gold & predicted)
        total_predicted += len(predicted)
        total_gold += len(gold)

    precision = total_tp / total_predicted if total_predicted else 0.0
    recall = total_tp / total_gold if total_gold else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return {"precision": precision, "recall": recall, "f1": f1}


# =====================================================================
# Core evaluation logic
# =====================================================================


def _run_single_item(
    db: Session,
    item: GoldItem,
) -> AnalyzeResponse | None:
    """Run analysis for a single gold item, returning the response or None on failure."""
    request = AnalyzeRequest(
        curriculum_text=item.lesson_text,
        title=item.title,
        subject=item.subject,
        grade_band=item.grade_band,
        rubric_text=item.rubric_text,
        item_type=CurriculumItemType.LESSON,
        triggered_by="evaluation-harness",
    )
    try:
        return run_analysis(db=db, request=request)
    except Exception:
        logger.exception("Evaluation item '%s' failed.", item.id)
        return None


def _extract_predicted_pillars(
    response: AnalyzeResponse,
    threshold: float = _PILLAR_SCORE_THRESHOLD,
) -> set[str]:
    """Extract pillar codes above the score threshold."""
    pillars: set[str] = set()
    for ps in response.pillar_scores:
        if ps.score >= threshold and ps.pillar_code is not None:
            pillars.add(ps.pillar_code.value)
    return pillars


def run_evaluation(dataset_path: Path) -> dict:
    """Execute the full evaluation and return the results dict."""
    settings = get_settings()

    # Load dataset
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset = GoldDataset(items=raw)
    logger.info("Loaded %d evaluation items from %s", len(dataset.items), dataset_path)

    # Per-pillar stats
    pillar_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"tp": 0, "fp": 0, "fn": 0}
    )
    per_item_sets: list[dict[str, set[str]]] = []
    item_results: list[dict] = []

    db: Session = SessionLocal()
    try:
        for item in dataset.items:
            response = _run_single_item(db, item)

            if response is None:
                item_results.append({
                    "id": item.id,
                    "status": "failed",
                    "expected": item.expected_pillars,
                    "predicted": [],
                })
                per_item_sets.append({
                    "gold": set(item.expected_pillars),
                    "predicted": set(),
                })
                continue

            predicted = _extract_predicted_pillars(response)
            gold = set(item.expected_pillars)

            per_item_sets.append({"gold": gold, "predicted": predicted})

            # Per-pillar TP/FP/FN
            for p in gold | predicted:
                if p in gold and p in predicted:
                    pillar_stats[p]["tp"] += 1
                elif p in predicted:
                    pillar_stats[p]["fp"] += 1
                else:
                    pillar_stats[p]["fn"] += 1

            item_results.append({
                "id": item.id,
                "status": str(response.status.value),
                "expected": sorted(gold),
                "predicted": sorted(predicted),
                "overall_score": response.overall_score,
                "match_method": response.match_method.value,
                "analysis_run_id": str(response.analysis_run_id),
            })
    finally:
        db.close()

    # Compute per-pillar P/R/F1
    pillar_metrics: dict[str, dict[str, float]] = {}
    for pillar, counts in sorted(pillar_stats.items()):
        tp = counts["tp"]
        fp = counts["fp"]
        fn = counts["fn"]
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        pillar_metrics[pillar] = {"precision": p, "recall": r, "f1": f}

    micro = _compute_micro_average(per_item_sets)

    # Build output
    results = {
        "run_metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset": str(dataset_path),
            "item_count": len(dataset.items),
            "embedding_model_name": settings.EMBEDDING_MODEL_NAME,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_dim": settings.EMBEDDING_DIM,
            "match_top_k": settings.MATCH_TOP_K,
            "semantic_min_similarity": settings.SEMANTIC_MIN_SIMILARITY,
            "pillar_score_threshold": _PILLAR_SCORE_THRESHOLD,
            "retrieval_config_version": "v1",
            "scoring_rule_version": "v1-deterministic",
        },
        "micro_average": micro,
        "per_pillar": pillar_metrics,
        "items": item_results,
    }

    return results


def _print_results(results: dict) -> None:
    """Pretty-print evaluation results to the console."""
    print("\n" + "=" * 60)
    print("  EVALUATION RESULTS")
    print("=" * 60)

    meta = results["run_metadata"]
    print(f"  Dataset:    {meta['dataset']}")
    print(f"  Items:      {meta['item_count']}")
    print(f"  Embedding:  {meta['embedding_provider']} / {meta['embedding_model_name']}")
    print(f"  Timestamp:  {meta['timestamp']}")

    print("\n  Per-Pillar Metrics:")
    print(f"  {'Pillar':<10} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print(f"  {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    for pillar, m in results["per_pillar"].items():
        print(f"  {pillar:<10} {m['precision']:>10.3f} {m['recall']:>10.3f} {m['f1']:>10.3f}")

    micro = results["micro_average"]
    print(f"\n  Micro-Avg:  P={micro['precision']:.3f}  R={micro['recall']:.3f}  F1={micro['f1']:.3f}")

    # Per-item summary
    print(f"\n  Item Details:")
    for item in results["items"]:
        status_icon = "✓" if item["status"] == "completed" else "✗"
        print(
            f"  {status_icon} {item['id']}: "
            f"expected={item['expected']}  predicted={item['predicted']}"
        )

    print("=" * 60 + "\n")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run curriculum analysis evaluation.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=_DEFAULT_DATASET,
        help=f"Path to gold dataset JSON (default: {_DEFAULT_DATASET})",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

    if not args.dataset.exists():
        print(f"ERROR: Dataset file not found: {args.dataset}", file=sys.stderr)
        print(f"Create it at: {_DEFAULT_DATASET}", file=sys.stderr)
        sys.exit(1)

    results = run_evaluation(args.dataset)
    _print_results(results)

    # Write to output file
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = _OUTPUT_DIR / f"eval_{ts}.json"
    output_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"Results written to: {output_path}")


if __name__ == "__main__":
    main()
