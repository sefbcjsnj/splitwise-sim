"""Plot the core resource-split experiment."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


METRICS = {
    "e2e": "pd_over_baseline_e2e_p99",
    "tbt": "pd_over_baseline_tbt_p99",
    "handoff": "pd_over_baseline_effective_ttft_p99",
}


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
        default=Path("results/core_split_analysis/figures"),
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df = df[df["status"] == "ok"].copy()
    for column in METRICS.values():
        df[column] = pd.to_numeric(df[column], errors="coerce")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Rate sensitivity by split.
    for metric_name, column in METRICS.items():
        grouped = (
            df.groupby(["rate", "split"])[column]
            .median()
            .reset_index()
            .sort_values(["split", "rate"])
        )
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        for split, subset in grouped.groupby("split"):
            ax.plot(subset["rate"], subset[column], marker="o", label=split)
        ax.axhline(1.0, color="black", linewidth=1, linestyle="--")
        ax.set_xlabel("Request rate (RPS)")
        ax.set_ylabel("PD / baseline")
        ax.set_title(f"Core split experiment: {metric_name} p99")
        ax.legend(title="prompt:decode")
        fig.tight_layout()
        path = args.output_dir / f"core_split_{metric_name}_by_rate.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        print(path)

    # Workload shape heatmaps for E2E, one plot per rate and split.
    for rate in sorted(df["rate"].unique()):
        for split in sorted(df["split"].unique()):
            subset = df[(df["rate"] == rate) & (df["split"] == split)]
            pivot = subset.pivot_table(
                index="prompt",
                columns="output",
                values="pd_over_baseline_e2e_p99",
                aggfunc="mean",
            ).sort_index()
            fig, ax = plt.subplots(figsize=(6.2, 4.6))
            image = ax.imshow(pivot.values, aspect="auto", cmap="RdBu_r", vmin=0.5, vmax=1.5)
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels([str(value) for value in pivot.columns])
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels([str(value) for value in pivot.index])
            ax.set_xlabel("Output length")
            ax.set_ylabel("Prompt length")
            ax.set_title(f"E2E p99 PD/baseline, split={split}, rate={rate}")
            for y, prompt in enumerate(pivot.index):
                for x, output in enumerate(pivot.columns):
                    value = pivot.loc[prompt, output]
                    ax.text(x, y, f"{value:.2f}", ha="center", va="center", fontsize=8)
            cbar = fig.colorbar(image, ax=ax)
            cbar.set_label("PD / baseline")
            fig.tight_layout()
            path = args.output_dir / f"core_split_e2e_heatmap_r{rate}_split_{split.replace(':', '_')}.png"
            fig.savefig(path, dpi=180)
            plt.close(fig)
            print(path)

    # Best split map by E2E for each rate.
    for rate in sorted(df["rate"].unique()):
        subset = df[df["rate"] == rate].copy()
        best = (
            subset.sort_values("pd_over_baseline_e2e_p99")
            .groupby(["prompt", "output"], as_index=False)
            .head(1)
        )
        prompts = sorted(best["prompt"].unique())
        outputs = sorted(best["output"].unique())
        fig, ax = plt.subplots(figsize=(6.2, 4.6))
        ax.imshow([[0 for _ in outputs] for _ in prompts], cmap="Greys", vmin=0, vmax=1)
        ax.set_xticks(range(len(outputs)))
        ax.set_xticklabels([str(value) for value in outputs])
        ax.set_yticks(range(len(prompts)))
        ax.set_yticklabels([str(value) for value in prompts])
        ax.set_xlabel("Output length")
        ax.set_ylabel("Prompt length")
        ax.set_title(f"Best E2E split by workload, rate={rate}")
        for y, prompt in enumerate(prompts):
            for x, output in enumerate(outputs):
                row = best[(best["prompt"] == prompt) & (best["output"] == output)].iloc[0]
                ax.text(
                    x,
                    y,
                    f"{row['split']}\n{row['pd_over_baseline_e2e_p99']:.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                )
        fig.tight_layout()
        path = args.output_dir / f"core_split_best_split_r{rate}.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        print(path)


if __name__ == "__main__":
    main()
