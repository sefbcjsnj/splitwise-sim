import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.gridspec import GridSpec

DATA_PATH = "../pd_disaggregation_deliverables/raw_csv/core_split_overlap_matrix_summary.csv"
OUT_TMPL  = "../pd_disaggregation_deliverables/figures/3d_split_tradeoff_o{}.png"

df = pd.read_csv(DATA_PATH)
df = df[df["status"] == "ok"].copy()

prompt_map = {128: 0, 256: 2, 512: 4}
rate_map   = {20: 0,  50: 2,  100: 4}
split_map  = {"2:6": 0, "4:4": 3, "6:2": 6}
ZV         = [0, 3, 6]

vmin, vmax = 0.6, 2.0
norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=1.0, vmax=vmax)
cmap = cm.RdYlGn_r

metrics = [
    ("pd_over_baseline_e2e_p99",           "E2E p99  (PD / Baseline)"),
    ("pd_over_baseline_tbt_p99",            "TBT p99  (PD / Baseline)"),
    ("pd_over_baseline_effective_ttft_p99", "effective TTFT p99  (PD / Baseline)"),
]

for OUTPUT in [64, 128, 256]:
    out_path = OUT_TMPL.format(OUTPUT)

    agg = (df[df["output"] == OUTPUT]
             .groupby(["prompt", "rate", "split"])
             [["pd_over_baseline_e2e_p99",
               "pd_over_baseline_effective_ttft_p99",
               "pd_over_baseline_tbt_p99"]]
             .mean()
             .reset_index())

    agg["xi"] = agg["prompt"].map(prompt_map).astype(float)
    agg["yi"] = agg["rate"].map(rate_map).astype(float)
    agg["zi"] = agg["split"].map(split_map).astype(float)

    fig = plt.figure(figsize=(26, 20))
    fig.patch.set_facecolor("#f5f5f5")

    gs = GridSpec(2, 4, figure=fig, hspace=0.05, wspace=0.10)
    ax_positions = [
        gs[0, 0:2],
        gs[0, 2:4],
        gs[1, 1:3],
    ]

    for col, (metric, title) in enumerate(metrics):
        ax = fig.add_subplot(ax_positions[col], projection="3d")
        ax.set_facecolor("#ebebeb")

        xs = agg["xi"].values
        ys = agg["yi"].values
        zs = agg["zi"].values
        cs = agg[metric].values

        sc = ax.scatter(xs, ys, zs,
                        c=cs, cmap=cmap, norm=norm,
                        s=600, edgecolors="#333333", linewidths=0.6,
                        alpha=0.95, depthshade=False, zorder=5)

        for xi, yi, zi, ci in zip(xs, ys, zs, cs):
            ax.text(xi, yi, zi + 0.32, f"{ci:.2f}",
                    fontsize=11, ha="center", va="bottom",
                    fontweight="bold", color="#111111")

        xx, yy = np.meshgrid([-0.6, 4.6], [-0.6, 4.6])
        for zv in ZV:
            ax.plot_surface(xx, yy, np.full_like(xx, float(zv)),
                            alpha=0.07, color="steelblue", zorder=1)

        for zv in ZV:
            sub = agg[agg["zi"] == zv]
            for xv in [0, 2, 4]:
                pts = sub[sub["xi"] == xv].sort_values("yi")
                ax.plot(pts["xi"], pts["yi"], pts["zi"],
                        "--", color="grey", alpha=0.35, linewidth=0.8, zorder=2)
            for yv in [0, 2, 4]:
                pts = sub[sub["yi"] == yv].sort_values("xi")
                ax.plot(pts["xi"], pts["yi"], pts["zi"],
                        "--", color="grey", alpha=0.35, linewidth=0.8, zorder=2)

        ax.set_xlabel("Prompt length", labelpad=6, fontsize=15)
        ax.set_ylabel("Request rate R", labelpad=6, fontsize=15)
        ax.set_zlabel("P:D split",      labelpad=6, fontsize=15)

        ax.set_xticks([0, 2, 4]); ax.set_xticklabels(["128", "256", "512"], fontsize=12)
        ax.set_yticks([0, 2, 4]); ax.set_yticklabels(["20",  "50",  "100"], fontsize=12)
        ax.set_zticks(ZV);        ax.set_zticklabels(["2:6", "4:4", "6:2"], fontsize=12)

        ax.set_xlim(-0.6, 4.6)
        ax.set_ylim(-0.6, 4.6)
        ax.set_zlim(-0.6, 6.8)

        ax.set_box_aspect([1, 1, 1.1])
        ax.view_init(elev=22, azim=-52)
        ax.set_title(title, fontsize=15, fontweight="bold", pad=10)

        cb = fig.colorbar(sc, ax=ax, pad=0.08, shrink=0.48, aspect=14)
        cb.set_label("PD / Baseline ratio\n(green = PD wins,  red = PD loses)", fontsize=10)
        cb.set_ticks([0.6, 0.7, 0.8, 0.9, 1.0, 1.25, 1.5, 2.0])
        cb.set_ticklabels(["0.6", "0.7", "0.8", "0.9", "1.0", "1.25", "1.5", "2.0"])
        cb.ax.axhline(y=0.5, color="black", linewidth=1.2, linestyle="--")

    fig.suptitle(
        f"PD Disaggregation Trade-off  ·  bw = 25 GB/s  ·  output length = {OUTPUT} tokens  ·  overlap scheduler\n"
        "Green = PD wins (ratio < 1),  Red = PD loses (ratio > 1)",
        fontsize=15, fontweight="bold", y=0.95
    )
    plt.subplots_adjust(left=0.04, right=0.96)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    print(f"Saved → {out_path}")
    plt.close()
