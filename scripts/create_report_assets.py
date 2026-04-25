"""Build report-ready tables, figures, and a compact result summary."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import pandas as pd


MAIN_METRICS = {
    "effective_ttft_p99": "pd_over_baseline_effective_ttft_p99",
    "tbt_p99": "pd_over_baseline_tbt_times_p99",
    "e2e_p99": "pd_over_baseline_response_times_p99",
}


CASE_COLUMNS = [
    "prompt",
    "output",
    "rate",
    "bandwidth",
    "pd_over_baseline_effective_ttft_p99",
    "pd_over_baseline_tbt_times_p99",
    "pd_over_baseline_response_times_p99",
]


def ratio_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric, column in MAIN_METRICS.items():
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        rows.append(
            {
                "metric": metric,
                "cases": int(values.size),
                "pd_better_count": int((values < 1.0).sum()),
                "pd_better_share": float((values < 1.0).mean()),
                "median_pd_over_baseline": float(values.median()),
                "p10_pd_over_baseline": float(values.quantile(0.10)),
                "p90_pd_over_baseline": float(values.quantile(0.90)),
                "min_pd_over_baseline": float(values.min()),
                "max_pd_over_baseline": float(values.max()),
            }
        )
    return pd.DataFrame(rows)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format="%.6g")
    print(path)


def copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(dst)
    return True


def seed_from_path(path: Path) -> int | None:
    match = re.search(r"robustness_(?:trace_)?seed(\d+)_", path.name)
    return int(match.group(1)) if match else None


def workload_label(row: pd.Series) -> str:
    return f"p{int(row['prompt'])}_o{int(row['output'])}_r{int(row['rate'])}_bw{row['bandwidth']:g}"


def build_seed_robustness(results_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    paths = sorted(results_dir.glob("robustness_trace_seed*_p*_bw25.csv"))
    if not paths:
        paths = sorted(results_dir.glob("robustness_seed*_p*_bw25.csv"))
    for path in paths:
        seed = seed_from_path(path)
        if seed is None:
            continue
        df = pd.read_csv(path)
        df = df[df["status"] == "ok"].copy()
        if df.empty:
            continue
        for _, row in df.iterrows():
            rows.append(
                {
                    "seed": seed,
                    "workload": workload_label(row),
                    "prompt": int(row["prompt"]),
                    "output": int(row["output"]),
                    "rate": int(row["rate"]),
                    "bandwidth": float(row["bandwidth"]),
                    "effective_ttft_ratio": float(
                        row["pd_over_baseline_effective_ttft_p99"]
                    ),
                    "tbt_ratio": float(row["pd_over_baseline_tbt_times_p99"]),
                    "e2e_ratio": float(row["pd_over_baseline_response_times_p99"]),
                }
            )

    per_seed = pd.DataFrame(rows)
    if per_seed.empty:
        return per_seed, per_seed

    grouped = []
    for workload, subset in per_seed.groupby("workload", sort=True):
        grouped.append(
            {
                "workload": workload,
                "seeds": int(subset["seed"].nunique()),
                "effective_ttft_ratio_mean": float(
                    subset["effective_ttft_ratio"].mean()
                ),
                "effective_ttft_ratio_min": float(subset["effective_ttft_ratio"].min()),
                "effective_ttft_ratio_max": float(subset["effective_ttft_ratio"].max()),
                "tbt_ratio_mean": float(subset["tbt_ratio"].mean()),
                "tbt_ratio_min": float(subset["tbt_ratio"].min()),
                "tbt_ratio_max": float(subset["tbt_ratio"].max()),
                "e2e_ratio_mean": float(subset["e2e_ratio"].mean()),
                "e2e_ratio_min": float(subset["e2e_ratio"].min()),
                "e2e_ratio_max": float(subset["e2e_ratio"].max()),
                "e2e_win_count": int((subset["e2e_ratio"] < 1.0).sum()),
            }
        )
    return per_seed, pd.DataFrame(grouped)


def build_markdown(
    output_path: Path,
    main: pd.DataFrame,
    metric_summary: pd.DataFrame,
    best_e2e: pd.DataFrame,
    worst_e2e: pd.DataFrame,
    seed_summary: pd.DataFrame,
    output512: pd.DataFrame,
    copied_figures: list[Path],
) -> None:
    e2e = metric_summary[metric_summary["metric"] == "e2e_p99"].iloc[0]
    tbt = metric_summary[metric_summary["metric"] == "tbt_p99"].iloc[0]
    ttft = metric_summary[metric_summary["metric"] == "effective_ttft_p99"].iloc[0]
    best = best_e2e.iloc[0]
    worst = worst_e2e.iloc[0]

    lines = [
        "# Report Assets Summary",
        "",
        "## Coverage",
        "",
        (
            f"The main sweep contains {len(main)} complete PD/baseline pairs over "
            "prompt length, output length, request rate, and KV transfer bandwidth."
        ),
        "",
        "Fixed setup: Llama-2-70B, A100-only, 8 total servers, coupled baseline with "
        "`token_jsq`, and PD with a 4:4 prompt/decode split unless otherwise noted.",
        "",
        "## Key Results",
        "",
        (
            f"- TTFT + handoff p99 improved in {int(ttft['pd_better_count'])}/"
            f"{int(ttft['cases'])} cases "
            f"({100 * ttft['pd_better_share']:.1f}%). Median PD/baseline ratio: "
            f"{ttft['median_pd_over_baseline']:.3f}."
        ),
        (
            f"- TBT p99 improved in {int(tbt['pd_better_count'])}/"
            f"{int(tbt['cases'])} cases "
            f"({100 * tbt['pd_better_share']:.1f}%). Median PD/baseline ratio: "
            f"{tbt['median_pd_over_baseline']:.3f}."
        ),
        (
            f"- E2E p99 improved in {int(e2e['pd_better_count'])}/"
            f"{int(e2e['cases'])} cases "
            f"({100 * e2e['pd_better_share']:.1f}%). Median PD/baseline ratio: "
            f"{e2e['median_pd_over_baseline']:.3f}."
        ),
        "",
        "This supports the main trade-off: PD often improves decode-token latency and "
        "sometimes end-to-end latency, but KV transfer usually worsens the handoff "
        "path between prefill and decode. The underlying CSV column is named "
        "`effective_ttft`, but it should be read as TTFT plus handoff overhead, "
        "not pure user-visible TTFT.",
        "",
        "## Best and Worst E2E Cases",
        "",
        (
            "Best E2E case: "
            f"prompt={int(best['prompt'])}, output={int(best['output'])}, "
            f"rate={int(best['rate'])} RPS, bandwidth={best['bandwidth']:g} GB/s, "
            f"E2E ratio={best['pd_over_baseline_response_times_p99']:.3f}."
        ),
        (
            "Worst E2E case: "
            f"prompt={int(worst['prompt'])}, output={int(worst['output'])}, "
            f"rate={int(worst['rate'])} RPS, bandwidth={worst['bandwidth']:g} GB/s, "
            f"E2E ratio={worst['pd_over_baseline_response_times_p99']:.3f}."
        ),
        "",
        "## Robustness",
        "",
    ]

    if seed_summary.empty:
        lines.append("Seed robustness results were not found.")
    else:
        for _, row in seed_summary.iterrows():
            lines.append(
                f"- {row['workload']}: E2E mean={row['e2e_ratio_mean']:.3f}, "
                f"range=[{row['e2e_ratio_min']:.3f}, {row['e2e_ratio_max']:.3f}], "
                f"wins={int(row['e2e_win_count'])}/{int(row['seeds'])} seeds."
            )

    lines.extend(
        [
            "",
            "## Output 512 Validation",
            "",
        ]
    )

    if output512.empty:
        lines.append("Output-512 validation results were not found.")
    else:
        for _, row in output512.iterrows():
            lines.append(
                f"- prompt={int(row['prompt'])}, rate={int(row['rate'])} RPS, "
                f"bandwidth={row['bandwidth']:g} GB/s: "
                f"E2E ratio={row['pd_over_baseline_response_times_p99']:.3f}, "
                f"TTFT + handoff ratio={row['pd_over_baseline_effective_ttft_p99']:.3f}."
            )

    lines.extend(
        [
            "",
            "## Selected Figures",
            "",
        ]
    )
    if copied_figures:
        for fig in copied_figures:
            lines.append(f"- `{fig.relative_to(output_path.parent)}`")
    else:
        lines.append("No selected figures were copied.")

    lines.extend(
        [
            "",
            "## Recommended Report Claim",
            "",
            "In this simulator study, prefill-decode disaggregation is not a universal "
            "latency win. It is most useful when decode batching/resource isolation "
            "reduces TBT enough to compensate for KV transfer. It is least favorable "
            "when KV handoff delay, low bandwidth, or poorly matched prompt/decode "
            "resource splits dominate.",
            "",
        ]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--main",
        type=Path,
        default=Path("results/main_o16_o64_o256_pairs.csv"),
    )
    parser.add_argument(
        "--resource",
        type=Path,
        default=Path("results/resource_split_summary.csv"),
    )
    parser.add_argument(
        "--output512",
        type=Path,
        default=Path("results/output512_validation_pairs.csv"),
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/report_assets"),
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = args.output_dir / "tables"
    figures_dir = args.output_dir / "figures"

    main = pd.read_csv(args.main)
    main = main[main["status"] == "ok"].copy()

    metric_summary = ratio_summary(main)
    write_csv(metric_summary, tables_dir / "main_metric_summary.csv")

    e2e_by_output_rate = (
        main.groupby(["output", "rate"])["pd_over_baseline_response_times_p99"]
        .agg(
            cases="count",
            pd_better_count=lambda s: int((s < 1.0).sum()),
            pd_better_share=lambda s: float((s < 1.0).mean()),
            median_pd_over_baseline="median",
            min_pd_over_baseline="min",
            max_pd_over_baseline="max",
        )
        .reset_index()
    )
    write_csv(e2e_by_output_rate, tables_dir / "e2e_by_output_rate.csv")

    bandwidth_sensitivity = (
        main.groupby("bandwidth")
        .agg(
            cases=("pd_over_baseline_response_times_p99", "count"),
            e2e_win_share=(
                "pd_over_baseline_response_times_p99",
                lambda s: float((s < 1.0).mean()),
            ),
            e2e_median_ratio=("pd_over_baseline_response_times_p99", "median"),
            effective_ttft_median_ratio=(
                "pd_over_baseline_effective_ttft_p99",
                "median",
            ),
            tbt_median_ratio=("pd_over_baseline_tbt_times_p99", "median"),
        )
        .reset_index()
        .sort_values("bandwidth", ascending=False)
    )
    write_csv(bandwidth_sensitivity, tables_dir / "bandwidth_sensitivity.csv")

    best_e2e = (
        main[CASE_COLUMNS]
        .sort_values("pd_over_baseline_response_times_p99")
        .head(10)
        .copy()
    )
    worst_e2e = (
        main[CASE_COLUMNS]
        .sort_values("pd_over_baseline_response_times_p99", ascending=False)
        .head(10)
        .copy()
    )
    write_csv(best_e2e, tables_dir / "best_e2e_cases.csv")
    write_csv(worst_e2e, tables_dir / "worst_e2e_cases.csv")

    per_seed, seed_summary = build_seed_robustness(args.results_dir)
    write_csv(per_seed, tables_dir / "seed_robustness_per_seed.csv")
    write_csv(seed_summary, tables_dir / "seed_robustness_summary.csv")

    if args.resource.exists():
        resource = pd.read_csv(args.resource)
        resource = resource[resource["status"] == "ok"].copy()
        resource_sorted = resource.sort_values(
            ["prompt", "output", "rate", "pd_over_baseline_e2e_p99"]
        )
        best_resource = (
            resource_sorted.groupby(["prompt", "output", "rate"])
            .head(1)
            .reset_index(drop=True)
        )
        write_csv(resource, tables_dir / "resource_split_all.csv")
        write_csv(best_resource, tables_dir / "resource_split_best.csv")
    else:
        resource = pd.DataFrame()

    if args.output512.exists():
        output512 = pd.read_csv(args.output512)
        output512 = output512[output512["status"] == "ok"].copy()
        keep = [col for col in CASE_COLUMNS if col in output512.columns]
        write_csv(output512[keep], tables_dir / "output512_validation.csv")
    else:
        output512 = pd.DataFrame()

    robustness_30s = args.results_dir / "robustness_30s_complete.csv"
    if robustness_30s.exists():
        copy_if_exists(robustness_30s, tables_dir / "robustness_30s_complete.csv")

    figure_sources = {
        "main_e2e_ratio_lines.png": args.results_dir
        / "plots"
        / "main_o16_o64_o256_pairs_e2e_p99.png",
        "main_effective_ttft_ratio_lines.png": args.results_dir
        / "plots"
        / "main_o16_o64_o256_pairs_effective_ttft_p99.png",
        "main_tbt_ratio_lines.png": args.results_dir
        / "plots"
        / "main_o16_o64_o256_pairs_tbt_p99.png",
        "heatmap_e2e_o64_r100.png": args.results_dir
        / "heatmaps"
        / "main_o16_o64_o256_pairs_e2e_p99_o64_r100.png",
        "heatmap_effective_ttft_o64_r100.png": args.results_dir
        / "heatmaps"
        / "main_o16_o64_o256_pairs_effective_ttft_p99_o64_r100.png",
        "heatmap_e2e_o256_r100.png": args.results_dir
        / "heatmaps"
        / "main_o16_o64_o256_pairs_e2e_p99_o256_r100.png",
        "heatmap_effective_ttft_o256_r100.png": args.results_dir
        / "heatmaps"
        / "main_o16_o64_o256_pairs_effective_ttft_p99_o256_r100.png",
        "resource_split_e2e.png": args.results_dir
        / "resource_split_plots"
        / "resource_split_summary_e2e_p99.png",
        "resource_split_effective_ttft.png": args.results_dir
        / "resource_split_plots"
        / "resource_split_summary_effective_ttft_p99.png",
        "output512_e2e_lines.png": args.results_dir
        / "plots"
        / "output512_validation_pairs_e2e_p99.png",
    }
    copied_figures = []
    for name, src in figure_sources.items():
        dst = figures_dir / name
        if copy_if_exists(src, dst):
            copied_figures.append(dst)

    build_markdown(
        args.output_dir / "report_summary.md",
        main,
        metric_summary,
        best_e2e,
        worst_e2e,
        seed_summary,
        output512,
        copied_figures,
    )


if __name__ == "__main__":
    main()
