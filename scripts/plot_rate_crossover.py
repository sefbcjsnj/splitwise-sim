"""Rate crossover: E2E p99 ratio vs request rate, faceted by (prompt × output).
Lines = P:D splits.  Reference line at ratio = 1.0.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

DATA_PATH_B    = "results/overnight_B_split_summary.csv"
DATA_PATH_TEAM = "pd_disaggregation_deliverables/raw_csv/core_split_overlap_matrix_summary.csv"
OUT_PATH       = "pd_disaggregation_deliverables/figures/rate_crossover_e2e.png"

COLS = ["bandwidth", "baseline_e2e_p99", "baseline_effective_ttft_p99",
        "baseline_tbt_p99", "output", "pd_e2e_p99", "pd_effective_ttft_p99",
        "pd_over_baseline_e2e_p99", "pd_over_baseline_effective_ttft_p99",
        "pd_over_baseline_tbt_p99", "pd_tbt_p99", "prompt", "rate", "split", "status"]

df_b    = pd.read_csv(DATA_PATH_B)[COLS]
df_team = pd.read_csv(DATA_PATH_TEAM)[COLS]

# keep teammate rows that match Exp B scope (prompt=128/512, output=64/128/256)
df_team = df_team[df_team["prompt"].isin([128, 512])]

df = pd.concat([df_b, df_team], ignore_index=True)
df = df[df["status"] == "ok"].copy()
# drop duplicates if any overlap (keep first, i.e. Exp B)
df = df.drop_duplicates(subset=["prompt", "output", "rate", "split"])

prompts = sorted(df["prompt"].unique())   # [128, 512]
outputs = sorted(df["output"].unique())   # [64, 128, 256]
rates   = sorted(df["rate"].unique())     # [10, 20, 30, 50, 70, 100, 150]
splits  = ["2:6", "4:4", "6:2"]

split_style = {
    "2:6": {"color": "#5b9bd5", "marker": "o", "ls": "-"},
    "4:4": {"color": "#ed7d31", "marker": "s", "ls": "--"},
    "6:2": {"color": "#70ad47", "marker": "^", "ls": "-."},
}

nrows, ncols = len(prompts), len(outputs)
fig, axes = plt.subplots(nrows, ncols, figsize=(13, 7), sharey=False)
fig.patch.set_facecolor("#f8f8f8")

for ri, prompt in enumerate(prompts):
    for ci, output in enumerate(outputs):
        ax = axes[ri][ci]
        ax.set_facecolor("#f2f2f2")

        sub = df[(df["prompt"] == prompt) & (df["output"] == output)]

        for sp in splits:
            s = sub[sub["split"] == sp].sort_values("rate")
            st = split_style[sp]
            ax.plot(s["rate"], s["pd_over_baseline_e2e_p99"],
                    color=st["color"], marker=st["marker"],
                    linestyle=st["ls"], linewidth=1.8, markersize=6,
                    label=sp, zorder=3)
            # annotate last point
            last = s.iloc[-1]
            ax.annotate(
                f"{last['pd_over_baseline_e2e_p99']:.2f}",
                xy=(last["rate"], last["pd_over_baseline_e2e_p99"]),
                xytext=(4, 0), textcoords="offset points",
                fontsize=7, color=st["color"], va="center",
            )

        ax.axhline(1.0, color="black", linewidth=1.0, linestyle=":", alpha=0.7, zorder=2)
        ax.set_xticks(rates)
        ax.set_xticklabels([str(r) for r in rates], fontsize=8)
        ax.tick_params(labelsize=8)

        for spine in ax.spines.values():
            spine.set_color("#cccccc")

        # column headers (output)
        if ri == 0:
            ax.set_title(f"Output = {output} tokens", fontsize=10, fontweight="bold", pad=6)
        # row labels (prompt)
        if ci == 0:
            ax.set_ylabel(f"Prompt={prompt}\nE2E p99  (PD / Baseline)", fontsize=9)
        if ri == nrows - 1:
            ax.set_xlabel("Request rate (req/s)", fontsize=9)

# legend
legend_handles = [
    mlines.Line2D([], [],
                  color=split_style[sp]["color"],
                  marker=split_style[sp]["marker"],
                  linestyle=split_style[sp]["ls"],
                  linewidth=1.8, markersize=6, label=f"Split {sp}")
    for sp in splits
]
legend_handles.append(
    mlines.Line2D([], [], color="black", linewidth=1.0, linestyle=":",
                  alpha=0.7, label="ratio = 1.0  (PD = Baseline)")
)
fig.legend(
    handles=legend_handles,
    loc="lower center", ncol=4,
    fontsize=9.5, framealpha=0.88,
    bbox_to_anchor=(0.5, -0.04),
)

fig.suptitle(
    "PD vs Baseline E2E p99 Ratio across Request Rates  ·  bw = 25 GB/s  ·  overlap scheduler\n"
    "Below 1.0 = PD wins,  Above 1.0 = PD loses",
    fontsize=11, fontweight="bold", y=1.02,
)
plt.tight_layout(rect=[0, 0.08, 1, 1])

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
plt.savefig(OUT_PATH, dpi=160, bbox_inches="tight")
print(f"Saved → {OUT_PATH}")
plt.show()
