"""Aggregate resource-split experiments for selected workloads."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd


METRICS = [
    "effective_ttft_p99",
    "tbt_p99",
    "e2e_p99",
]


def parse_workload(value: str) -> tuple[int, int, int]:
    prompt, output, rate = value.split(":")
    return int(prompt), int(output), int(rate)


def parse_split(value: str) -> tuple[int, int]:
    prompt_instances, token_instances = value.split(":")
    return int(prompt_instances), int(token_instances)


def read_detailed(path: Path) -> pd.DataFrame | None:
    detailed = path / "detailed" / "0.csv"
    if not detailed.exists():
        return None
    return pd.read_csv(detailed)


def summarize(df: pd.DataFrame) -> dict[str, float]:
    effective_ttft = df["ttft_times"] + df["nth_token_overheads"]
    return {
        "effective_ttft_p99": float(effective_ttft.quantile(0.99)),
        "tbt_p99": float(df["tbt_times"].quantile(0.99)),
        "e2e_p99": float(df["response_times"].quantile(0.99)),
    }


def baseline_dir(seed: int, trace: str, total_a100: int) -> Path:
    return (
        Path("results")
        / str(seed)
        / "baseline"
        / trace
        / f"{total_a100}_0"
        / "llama2-70b"
        / "token_jsq"
    )


def pd_dir(seed: int, trace: str, total_a100: int, split: tuple[int, int], bandwidth: str) -> Path:
    prompt_instances, token_instances = split
    return (
        Path("results")
        / str(seed)
        / f"splitwise_{prompt_instances}_{token_instances}"
        / trace
        / f"{total_a100}_0"
        / "llama2-70b"
        / f"mixed_pool_a100_bw{bandwidth}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workloads", default="128:16:100,512:64:100,1024:64:100,2048:256:100")
    parser.add_argument("--splits", default="2:6,4:4,6:2")
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--total-a100", type=int, default=8)
    parser.add_argument("--bandwidth", default="25")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--trace-tag", default="")
    parser.add_argument("--output", type=Path, default=Path("results/resource_split_summary.csv"))
    args = parser.parse_args()

    workloads = [parse_workload(item.strip()) for item in args.workloads.split(",") if item.strip()]
    splits = [parse_split(item.strip()) for item in args.splits.split(",") if item.strip()]

    rows = []
    for prompt, output, rate in workloads:
        suffix = f"_{args.trace_tag}" if args.trace_tag else ""
        trace = f"param_p{prompt}_o{output}_r{rate}_{args.duration}s{suffix}"
        baseline_df = read_detailed(baseline_dir(args.seed, trace, args.total_a100))
        baseline_metrics = summarize(baseline_df) if baseline_df is not None else None

        for split in splits:
            pd_df = read_detailed(pd_dir(args.seed, trace, args.total_a100, split, args.bandwidth))
            row = {
                "prompt": prompt,
                "output": output,
                "rate": rate,
                "bandwidth": args.bandwidth,
                "split": f"{split[0]}:{split[1]}",
                "status": "ok" if baseline_metrics and pd_df is not None else "missing",
            }
            if baseline_metrics and pd_df is not None:
                pd_metrics = summarize(pd_df)
                for metric in METRICS:
                    row[f"baseline_{metric}"] = baseline_metrics[metric]
                    row[f"pd_{metric}"] = pd_metrics[metric]
                    row[f"pd_over_baseline_{metric}"] = (
                        pd_metrics[metric] / baseline_metrics[metric]
                        if baseline_metrics[metric] != 0
                        else ""
                    )
            rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    complete = sum(1 for row in rows if row["status"] == "ok")
    print(f"wrote {args.output}")
    print(f"rows={len(rows)} complete={complete}")


if __name__ == "__main__":
    main()
