"""Generate synthetic traces for the PD disaggregation parameter study."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def parse_numbers(value: str, cast):
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


def trace_name(
    prompt: int,
    output: int,
    rate: int,
    duration: int,
    tag: str = "",
) -> str:
    suffix = f"_{tag}" if tag else ""
    return f"param_p{prompt}_o{output}_r{rate}_{duration}s{suffix}"


def stable_seed(base_seed: int, prompt: int, output: int, rate: int, duration: int) -> int:
    return base_seed + prompt * 1_000_000 + output * 1_000 + rate * 10 + duration


def generate_trace(
    output_dir: Path,
    prompt: int,
    output: int,
    rate: int,
    duration: int,
    seed: int,
    tag: str = "",
) -> tuple[Path, int]:
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{trace_name(prompt, output, rate, duration, tag)}.csv"

    arrival = 0.0
    request_id = 0
    rows = []
    while True:
        arrival += rng.expovariate(rate)
        if arrival >= duration:
            break
        rows.append(
            {
                "request_id": request_id,
                "request_type": 2,
                "application_id": 0,
                "arrival_timestamp": arrival,
                "batch_size": 1,
                "prompt_size": prompt,
                "token_size": output,
            }
        )
        request_id += 1

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "request_id",
                "request_type",
                "application_id",
                "arrival_timestamp",
                "batch_size",
                "prompt_size",
                "token_size",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    return path, len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default="128,512,1024,2048")
    parser.add_argument("--outputs", default="16,64,256,512")
    parser.add_argument("--rates", default="20,50,100")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--tag", default="")
    parser.add_argument("--output-dir", type=Path, default=Path("traces"))
    args = parser.parse_args()

    prompts = parse_numbers(args.prompts, int)
    outputs = parse_numbers(args.outputs, int)
    rates = parse_numbers(args.rates, int)

    total = 0
    for prompt in prompts:
        for output in outputs:
            for rate in rates:
                seed = stable_seed(args.seed, prompt, output, rate, args.duration)
                path, count = generate_trace(
                    args.output_dir, prompt, output, rate, args.duration, seed, args.tag
                )
                total += 1
                print(f"{path}: {count} requests")

    print(f"generated {total} traces")


if __name__ == "__main__":
    main()
