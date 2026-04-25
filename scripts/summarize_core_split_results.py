"""Summarize the core prompt/output/rate/resource-split experiment."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


METRIC_COLUMNS = {
    "handoff": "pd_over_baseline_effective_ttft_p99",
    "tbt": "pd_over_baseline_tbt_p99",
    "e2e": "pd_over_baseline_e2e_p99",
}


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format="%.6g")
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results/core_split_matrix_summary.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/core_split_analysis"),
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df = df[df["status"] == "ok"].copy()
    if df.empty:
        raise ValueError("No complete rows found")

    for column in METRIC_COLUMNS.values():
        df[column] = pd.to_numeric(df[column], errors="coerce")

    metric_summary_rows = []
    for metric, column in METRIC_COLUMNS.items():
        s = df[column].dropna()
        metric_summary_rows.append(
            {
                "metric": metric,
                "cases": int(s.size),
                "pd_better_count": int((s < 1.0).sum()),
                "pd_better_share": float((s < 1.0).mean()),
                "median_pd_over_baseline": float(s.median()),
                "p10_pd_over_baseline": float(s.quantile(0.10)),
                "p90_pd_over_baseline": float(s.quantile(0.90)),
            }
        )
    write_csv(pd.DataFrame(metric_summary_rows), args.output_dir / "metric_summary.csv")

    best_by_workload = (
        df.sort_values("pd_over_baseline_e2e_p99")
        .groupby(["prompt", "output", "rate"], as_index=False)
        .head(1)
        .sort_values(["prompt", "output", "rate"])
    )
    write_csv(best_by_workload, args.output_dir / "best_split_by_workload.csv")

    split_summary = (
        df.groupby("split")
        .agg(
            cases=("split", "size"),
            e2e_win_share=("pd_over_baseline_e2e_p99", lambda s: float((s < 1.0).mean())),
            e2e_median=("pd_over_baseline_e2e_p99", "median"),
            tbt_median=("pd_over_baseline_tbt_p99", "median"),
            handoff_median=("pd_over_baseline_effective_ttft_p99", "median"),
        )
        .reset_index()
        .sort_values("split")
    )
    write_csv(split_summary, args.output_dir / "summary_by_split.csv")

    shape_summary = (
        df.groupby(["prompt", "output", "split"])
        .agg(
            cases=("split", "size"),
            e2e_win_share=("pd_over_baseline_e2e_p99", lambda s: float((s < 1.0).mean())),
            e2e_median=("pd_over_baseline_e2e_p99", "median"),
            tbt_median=("pd_over_baseline_tbt_p99", "median"),
            handoff_median=("pd_over_baseline_effective_ttft_p99", "median"),
        )
        .reset_index()
        .sort_values(["prompt", "output", "split"])
    )
    write_csv(shape_summary, args.output_dir / "summary_by_shape_and_split.csv")

    rate_summary = (
        df.groupby(["rate", "split"])
        .agg(
            cases=("split", "size"),
            e2e_win_share=("pd_over_baseline_e2e_p99", lambda s: float((s < 1.0).mean())),
            e2e_median=("pd_over_baseline_e2e_p99", "median"),
            tbt_median=("pd_over_baseline_tbt_p99", "median"),
            handoff_median=("pd_over_baseline_effective_ttft_p99", "median"),
        )
        .reset_index()
        .sort_values(["rate", "split"])
    )
    write_csv(rate_summary, args.output_dir / "summary_by_rate_and_split.csv")

    print("\nMetric summary")
    print(pd.DataFrame(metric_summary_rows).round(3).to_string(index=False))
    print("\nBest split counts by E2E")
    print(best_by_workload["split"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
