"""Phase diagram: optimal P:D split as function of workload shape (prompt × output).
Layout: 3 rows (rate=20/50/100) × 5 output columns (16,64,128,256,512).
Data: Experiment A (o=16,512) + teammate overlap data (o=64,128,256).
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DATA_A    = "results/overnight_A_split_summary.csv"
DATA_TEAM = "pd_disaggregation_deliverables/raw_csv/core_split_overlap_matrix_summary.csv"
OUT_PATH  = "pd_disaggregation_deliverables/figures/phase_diagram_optimal_split.png"

COLS = ["prompt", "output", "rate", "split", "status",
        "pd_over_baseline_e2e_p99"]

df_a    = pd.read_csv(DATA_A)[COLS]
df_team = pd.read_csv(DATA_TEAM)[COLS]

df = pd.concat([df_a, df_team], ignore_index=True)
df = df[df["status"] == "ok"].copy()
df = df.drop_duplicates(subset=["prompt", "output", "rate", "split"])

best = (
    df.sort_values("pd_over_baseline_e2e_p99")
      .groupby(["prompt", "output", "rate"], as_index=False)
      .head(1)
)

prompts = sorted(df["prompt"].unique())   # [128, 256, 512]
outputs = sorted(df["output"].unique())   # [16, 64, 128, 256, 512]
rates   = sorted(df["rate"].unique())     # [20, 50, 100]
splits  = ["2:6", "4:4", "6:2"]

split_color = {"2:6": "#5b9bd5", "4:4": "#ed7d31", "6:2": "#70ad47"}

fig, axes = plt.subplots(3, 1, figsize=(13, 10))
fig.patch.set_facecolor("#f8f8f8")

for ri, rate in enumerate(rates):
    ax = axes[ri]
    ax.set_facecolor("#ebebeb")

    sub = best[best["rate"] == rate]

    for yi, prompt in enumerate(prompts):
        for xi, output in enumerate(outputs):
            row = sub[(sub["prompt"] == prompt) & (sub["output"] == output)]
            if row.empty:
                continue
            sp  = row.iloc[0]["split"]
            val = row.iloc[0]["pd_over_baseline_e2e_p99"]

            rect = mpatches.FancyBboxPatch(
                (xi - 0.42, yi - 0.42), 0.84, 0.84,
                boxstyle="round,pad=0.05",
                facecolor=split_color[sp], edgecolor="white", linewidth=1.5,
            )
            ax.add_patch(rect)

            ax.text(xi, yi + 0.10, sp,
                    ha="center", va="center", fontsize=12,
                    fontweight="bold", color="white")
            ax.text(xi, yi - 0.18, f"E2E={val:.2f}×",
                    ha="center", va="center", fontsize=8,
                    color="white", alpha=0.92)

    ax.set_xlim(-0.55, len(outputs) - 0.45)
    ax.set_ylim(-0.55, len(prompts) - 0.45)
    ax.set_xticks(range(len(outputs)))
    ax.set_yticks(range(len(prompts)))
    ax.set_xticklabels([str(o) for o in outputs], fontsize=10)
    ax.set_yticklabels([str(p) for p in prompts], fontsize=10)
    ax.set_ylabel("Prompt length\n(tokens)", fontsize=10, labelpad=6)
    if ri == len(rates) - 1:
        ax.set_xlabel("Output length (tokens)", fontsize=10, labelpad=6)
    ax.set_title(f"Rate = {rate} req/s", fontsize=11, fontweight="bold", pad=6)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

legend_patches = [
    mpatches.Patch(color=split_color[s], label=f"Best split: {s}")
    for s in splits
]
fig.legend(
    handles=legend_patches,
    loc="lower center", ncol=3,
    fontsize=10, framealpha=0.85,
    bbox_to_anchor=(0.5, -0.02),
)

fig.suptitle(
    "Optimal P:D Split by Workload Shape  ·  bw = 25 GB/s  ·  overlap scheduler\n"
    "Color = best split (lowest E2E p99 ratio vs baseline)",
    fontsize=11, fontweight="bold",
)
plt.tight_layout(rect=[0, 0.05, 1, 0.97])

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
plt.savefig(OUT_PATH, dpi=160, bbox_inches="tight")
print(f"Saved → {OUT_PATH}")
plt.show()
