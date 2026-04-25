"""Plot PD-over-baseline ratios from aggregated parameter sweep results."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


METRICS = {
    "effective_ttft_p99": "pd_over_baseline_effective_ttft_p99",
    "ttft_p99": "pd_over_baseline_ttft_times_p99",
    "tbt_p99": "pd_over_baseline_tbt_times_p99",
    "e2e_p99": "pd_over_baseline_response_times_p99",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/plots"))
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df = df[df["status"] == "ok"].copy()
    if df.empty:
        raise ValueError("No complete rows found in input CSV")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for label, column in METRICS.items():
        if column not in df.columns:
            continue
        fig, ax = plt.subplots(figsize=(8, 4.8))
        for (prompt, output, rate), group in df.groupby(["prompt", "output", "rate"]):
            group = group.sort_values("bandwidth")
            series_label = f"p{prompt} o{output} r{rate}"
            ax.plot(group["bandwidth"], group[column], marker="o", label=series_label)

        ax.axhline(1.0, color="black", linewidth=1, linestyle="--")
        ax.set_xscale("log", base=2)
        ax.invert_xaxis()
        ticks = sorted(df["bandwidth"].unique())
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{tick:g}" for tick in ticks])
        ax.set_xlabel("KV transfer bandwidth (GB/s)")
        ax.set_ylabel(f"PD / baseline {label}")
        ax.set_title(f"PD crossover: {label}")
        ax.grid(True, which="both", linestyle=":", linewidth=0.7)
        ax.legend(fontsize=8, ncol=2)
        fig.tight_layout()

        output_path = args.output_dir / f"{args.input.stem}_{label}.png"
        fig.savefig(output_path, dpi=180)
        plt.close(fig)
        print(output_path)


if __name__ == "__main__":
    main()
