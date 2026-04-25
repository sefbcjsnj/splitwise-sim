"""Plot prompt/token resource split sensitivity."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


METRICS = {
    "effective_ttft_p99": "pd_over_baseline_effective_ttft_p99",
    "tbt_p99": "pd_over_baseline_tbt_p99",
    "e2e_p99": "pd_over_baseline_e2e_p99",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results/resource_split_summary.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/resource_split_plots"))
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df = df[df["status"] == "ok"].copy()
    if df.empty:
        raise ValueError("No complete rows found")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    df["workload"] = df.apply(
        lambda row: f"p{int(row.prompt)} o{int(row.output)} r{int(row.rate)}",
        axis=1,
    )

    for label, column in METRICS.items():
        fig, ax = plt.subplots(figsize=(8, 4.8))
        for workload, group in df.groupby("workload"):
            group = group.sort_values("split")
            ax.plot(group["split"], group[column], marker="o", label=workload)

        ax.axhline(1.0, color="black", linewidth=1, linestyle="--")
        ax.set_xlabel("Prompt:token instances")
        ax.set_ylabel(f"PD / baseline {label}")
        ax.set_title(f"Resource split sensitivity: {label}")
        ax.grid(True, linestyle=":", linewidth=0.7)
        ax.legend(fontsize=8)
        fig.tight_layout()

        output_path = args.output_dir / f"{args.input.stem}_{label}.png"
        fig.savefig(output_path, dpi=180)
        plt.close(fig)
        print(output_path)


if __name__ == "__main__":
    main()
