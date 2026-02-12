#!/usr/bin/env python3
"""Train and persist the cost estimation model artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.cost_estimation_service import (
    CostEstimationError,
    CostEstimationService,
    train_cost_estimation_model,
)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train two-stage cost estimation model (overrun -> actual cost)."
    )
    parser.add_argument(
        "--dataset-path",
        required=True,
        help="Path to training CSV dataset.",
    )
    parser.add_argument(
        "--output-model-path",
        default=str(CostEstimationService.DEFAULT_MODEL_PATH),
        help="Where to save the trained model artifact JSON.",
    )
    parser.add_argument(
        "--ridge-alpha",
        type=float,
        default=10.0,
        help="L2 regularization strength for ridge regression.",
    )
    parser.add_argument(
        "--folds",
        type=int,
        default=5,
        help="Number of K-folds for cross-validation metrics.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed used by K-fold splitting.",
    )
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    dataset_path = Path(args.dataset_path)
    output_model_path = Path(args.output_model_path)

    try:
        result = train_cost_estimation_model(
            dataset_path=dataset_path,
            output_model_path=output_model_path,
            ridge_alpha=args.ridge_alpha,
            folds=args.folds,
            random_seed=args.random_seed,
        )
    except CostEstimationError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
