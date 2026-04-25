"""Run baseline and PD SplitwiseSim sweeps for generated synthetic traces."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path


MODEL_ARGS = [
    "applications.0.model_architecture=llama2-70b",
    "applications.0.model_size=llama2-70b-fp16",
    "performance_model=db",
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
    scheduler = f"mixed_pool_a100_bw{bandwidth_label(bandwidth)}"
    return (
        Path("results")
        / str(seed)
        / f"splitwise_{prompt_instances}_{token_instances}"
        / trace
        / f"{total_a100}_0"
        / "llama2-70b"
        / scheduler
        / "summary.csv"
    )


def run_command(
    command: list[str],
    log_path: Path,
    dry_run: bool,
) -> tuple[int, float]:
    print(" ".join(command))
    if dry_run:
        return 0, 0.0

    start = time.perf_counter()
    result = subprocess.run(command, text=True, capture_output=True)
    elapsed = time.perf_counter() - start

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(result.stdout)
        if result.stderr:
            handle.write("\n--- STDERR ---\n")
            handle.write(result.stderr)

    if result.returncode != 0:
        print(f"FAILED rc={result.returncode}: {log_path}")
    else:
        print(f"OK {elapsed:.2f}s: {log_path}")
    return result.returncode, elapsed


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
    parser.add_argument("--systems", default="baseline,pd")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--runlog", type=Path, default=Path("results/param_sweep_runlog.csv"))
    args = parser.parse_args()

    if args.prompt_instances + args.token_instances > args.total_a100:
        raise ValueError("prompt_instances + token_instances cannot exceed total_a100")

    prompts = parse_numbers(args.prompts, int)
    outputs = parse_numbers(args.outputs, int)
    rates = parse_numbers(args.rates, int)
    bandwidths = parse_numbers(args.bandwidths, float)
    systems = {item.strip() for item in args.systems.split(",") if item.strip()}

    run_rows = []
    python = sys.executable

    for prompt in prompts:
        for output in outputs:
            for rate in rates:
                trace = trace_name(prompt, output, rate, args.duration, args.trace_tag)

                if "baseline" in systems:
                    summary = baseline_summary_path(args.seed, trace, args.total_a100)
                    status = "skipped"
                    elapsed = 0.0
                    rc = 0
                    if args.force or not summary.exists():
                        command = [
                            python,
                            "run.py",
                            *MODEL_ARGS,
                            "applications.0.scheduler=token_jsq",
                            "cluster=half_half",
                            f"cluster.servers.0.count={args.total_a100}",
                            "cluster.servers.1.count=0",
                            "start_state=baseline",
                            f"trace.filename={trace}",
                            f"seed={args.seed}",
                        ]
                        log_path = Path("results/param_sweep_logs") / f"baseline_{trace}.log"
                        rc, elapsed = run_command(command, log_path, args.dry_run)
                        status = "ok" if rc == 0 else "failed"

                    run_rows.append(
                        {
                            "system": "baseline",
                            "prompt": prompt,
                            "output": output,
                            "rate": rate,
                            "bandwidth": "",
                            "trace": trace,
                            "returncode": rc,
                            "status": status,
                            "elapsed_seconds": elapsed,
                            "summary": str(summary),
                        }
                    )

                if "pd" in systems:
                    for bandwidth in bandwidths:
                        scheduler = f"mixed_pool_a100_bw{bandwidth_label(bandwidth)}"
                        summary = pd_summary_path(
                            args.seed,
                            trace,
                            args.total_a100,
                            args.prompt_instances,
                            args.token_instances,
                            bandwidth,
                        )
                        status = "skipped"
                        elapsed = 0.0
                        rc = 0
                        if args.force or not summary.exists():
                            command = [
                                python,
                                "run.py",
                                *MODEL_ARGS,
                                f"applications.0.scheduler={scheduler}",
                                "cluster=half_half",
                                f"cluster.servers.0.count={args.total_a100}",
                                "cluster.servers.1.count=0",
                                "start_state=splitwise",
                                "start_state.split_type=homogeneous",
                                f"start_state.prompt.num_instances={args.prompt_instances}",
                                f"start_state.token.num_instances={args.token_instances}",
                                f"trace.filename={trace}",
                                f"seed={args.seed}",
                            ]
                            log_path = (
                                Path("results/param_sweep_logs")
                                / (
                                    f"pd_p{args.prompt_instances}_t{args.token_instances}_"
                                    f"bw{bandwidth_label(bandwidth)}_{trace}.log"
                                )
                            )
                            rc, elapsed = run_command(command, log_path, args.dry_run)
                            status = "ok" if rc == 0 else "failed"

                        run_rows.append(
                            {
                                "system": "pd",
                                "prompt": prompt,
                                "output": output,
                                "rate": rate,
                                "bandwidth": bandwidth,
                                "trace": trace,
                                "returncode": rc,
                                "status": status,
                                "elapsed_seconds": elapsed,
                                "summary": str(summary),
                            }
                        )

    args.runlog.parent.mkdir(parents=True, exist_ok=True)
    with args.runlog.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(run_rows[0].keys()))
        writer.writeheader()
        writer.writerows(run_rows)

    failures = [row for row in run_rows if row["returncode"] != 0]
    print(f"wrote {args.runlog}")
    print(f"runs={len(run_rows)} failures={len(failures)}")


if __name__ == "__main__":
    main()
