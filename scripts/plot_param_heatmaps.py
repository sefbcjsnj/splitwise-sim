"""Create heatmaps for PD-over-baseline crossover regions."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


METRICS = {
    "effective_ttft_p99": "pd_over_baseline_effective_ttft_p99",
    "tbt_p99": "pd_over_baseline_tbt_times_p99",
    "e2e_p99": "pd_over_baseline_response_times_p99",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/heatmaps"))
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df = df[df["status"] == "ok"].copy()
    if df.empty:
        raise ValueError("No complete rows found in input CSV")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for metric_name, column in METRICS.items():
        if column not in df.columns:
            continue
        for output in sorted(df["output"].unique()):
            for rate in sorted(df["rate"].unique()):
                subset = df[(df["output"] == output) & (df["rate"] == rate)]
                if subset.empty:
                    continue

                pivot = subset.pivot_table(
                    index="prompt",
                    columns="bandwidth",
                    values=column,
                    aggfunc="mean",
                )
                pivot = pivot.sort_index().reindex(sorted(pivot.columns, reverse=True), axis=1)

                fig, ax = plt.subplots(figsize=(7.2, 4.8))
                image = ax.imshow(pivot.values, aspect="auto", cmap="RdBu_r", vmin=0.5, vmax=1.5)
                ax.set_xticks(range(len(pivot.columns)))
                ax.set_xticklabels([f"{value:g}" for value in pivot.columns])
                ax.set_yticks(range(len(pivot.index)))
                ax.set_yticklabels([str(value) for value in pivot.index])
                ax.set_xlabel("KV transfer bandwidth (GB/s)")
                ax.set_ylabel("Prompt length (tokens)")
                ax.set_title(f"{metric_name}: output={output}, rate={rate} RPS")

                for y, prompt in enumerate(pivot.index):
                    for x, bandwidth in enumerate(pivot.columns):
                        value = pivot.loc[prompt, bandwidth]
                        ax.text(x, y, f"{value:.2f}", ha="center", va="center", fontsize=8)

                cbar = fig.colorbar(image, ax=ax)
                cbar.set_label("PD / baseline")
                fig.tight_layout()

                output_path = args.output_dir / f"{args.input.stem}_{metric_name}_o{output}_r{rate}.png"
                fig.savefig(output_path, dpi=180)
                plt.close(fig)
                print(output_path)


if __name__ == "__main__":
    main()
