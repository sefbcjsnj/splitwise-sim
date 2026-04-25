"""Aggregate SplitwiseSim parameter sweep summaries into pairwise ratios."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd


METRICS = [
    "ttft_times_p50",
    "ttft_times_p90",
    "ttft_times_p99",
    "tbt_times_p50",
    "tbt_times_p90",
    "tbt_times_p99",
    "response_times_p50",
    "response_times_p90",
    "response_times_p99",
    "queue_times_p99",
    "nth_token_overheads_p99",
]


def parse_numbers(value: str, cast):
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


def bandwidth_label(value: float) -> str:
    text = f"{value:g}"
    return text.replace(".", "_")


def trace_name(
    prompt: int,
    output: int,
    rate: int,
    duration: int,
    tag: str = "",
) -> str:
    suffix = f"_{tag}" if tag else ""
    return f"param_p{prompt}_o{output}_r{rate}_{duration}s{suffix}"


def read_summary(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.DictReader(handle))


def read_effective_ttft(summary_path: Path) -> dict[str, float]:
    detailed_path = summary_path.parent / "detailed" / "0.csv"
    if not detailed_path.exists():
        return {}
    detailed = pd.read_csv(detailed_path)
    effective_ttft = detailed["ttft_times"] + detailed["nth_token_overheads"]
    return {
        "effective_ttft_p50": float(effective_ttft.quantile(0.50)),
        "effective_ttft_p90": float(effective_ttft.quantile(0.90)),
        "effective_ttft_p99": float(effective_ttft.quantile(0.99)),
    }


def baseline_summary_path(seed: int, trace: str, total_a100: int) -> Path:
    return (
        Path("results")
        / str(seed)
        / "baseline"
        / trace
        / f"{total_a100}_0"
        / "llama2-70b"
        / "token_jsq"
        / "summary.csv"
    )


def pd_summary_path(
    seed: int,
    trace: str,
    total_a100: int,
    prompt_instances: int,
    token_instances: int,
    bandwidth: float,
) -> Path:
    return (
        Path("results")
        / str(seed)
        / f"splitwise_{prompt_instances}_{token_instances}"
        / trace
        / f"{total_a100}_0"
        / "llama2-70b"
        / f"mixed_pool_a100_bw{bandwidth_label(bandwidth)}"
        / "summary.csv"
    )


def as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default="128,512,1024,2048")
    parser.add_argument("--outputs", default="16,64,256,512")
    parser.add_argument("--rates", default="20,50,100")
    parser.add_argument("--bandwidths", default="50,25,12.5,3.125")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--total-a100", type=int, default=8)
    parser.add_argument("--prompt-instances", type=int, default=4)
    parser.add_argument("--token-instances", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--trace-tag", default="")
    parser.add_argument("--output", type=Path, default=Path("results/param_sweep_pairs.csv"))
    args = parser.parse_args()

    prompts = parse_numbers(args.prompts, int)
    outputs = parse_numbers(args.outputs, int)
    rates = parse_numbers(args.rates, int)
    bandwidths = parse_numbers(args.bandwidths, float)

    rows = []
    for prompt in prompts:
        for output in outputs:
            for rate in rates:
                trace = trace_name(prompt, output, rate, args.duration, args.trace_tag)
                baseline_path = baseline_summary_path(args.seed, trace, args.total_a100)
                baseline = read_summary(baseline_path)
                for bandwidth in bandwidths:
                    pd_path = pd_summary_path(
                        args.seed,
                        trace,
                        args.total_a100,
                        args.prompt_instances,
                        args.token_instances,
                        bandwidth,
                    )
                    pd = read_summary(pd_path)
                    row = {
                        "prompt": prompt,
                        "output": output,
                        "rate": rate,
                        "bandwidth": bandwidth,
                        "trace": trace,
                        "baseline_summary": str(baseline_path),
                        "pd_summary": str(pd_path),
                        "status": "ok" if baseline and pd else "missing",
                    }
                    if baseline and pd:
                        baseline_effective = read_effective_ttft(baseline_path)
                        pd_effective = read_effective_ttft(pd_path)
                        for metric in METRICS:
                            b_value = as_float(baseline, metric)
                            p_value = as_float(pd, metric)
                            row[f"baseline_{metric}"] = b_value
                            row[f"pd_{metric}"] = p_value
                            row[f"pd_over_baseline_{metric}"] = (
                                p_value / b_value if b_value != 0 else ""
                            )
                        for metric, b_value in baseline_effective.items():
                            p_value = pd_effective.get(metric)
                            if p_value is None:
                                continue
                            row[f"baseline_{metric}"] = b_value
                            row[f"pd_{metric}"] = p_value
                            row[f"pd_over_baseline_{metric}"] = (
                                p_value / b_value if b_value != 0 else ""
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
    print(f"pairs={len(rows)} complete={complete}")


if __name__ == "__main__":
    main()
