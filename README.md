# When Does Prefill-Decode Disaggregation Help?

This repository is a course-project fork of [SplitwiseSim](https://github.com/Mutinifni/splitwise-sim). It uses SplitwiseSim as a CPU-friendly simulator to study:

```text
When Does Prefill-Decode Disaggregation Help?
A Parametric Study of Trade-offs in LLM Serving
```

The project compares a coupled LLM serving baseline against prefill-decode (PD) disaggregation across workload shape, KV-cache transfer bandwidth, request rate, and prompt/decode resource allocation.

## Summary

Prefill-decode disaggregation is not a universal latency win. In this A100-only simulator study, PD often improves decode-token latency and sometimes improves end-to-end tail latency, but it introduces a KV-cache handoff delay between the prefill worker and the decode worker.

The main sweep has 144 parameter points:

```text
4 prompt lengths x 3 output lengths x 3 request rates x 4 KV bandwidths = 144
```

For each point, the experiment runs both a coupled baseline and a PD-disaggregated configuration. `PD better` means the PD p99 latency is lower than the baseline p99 latency for that metric. `Median PD / baseline` is the median ratio across all 144 points, where values below 1.0 mean PD is faster and values above 1.0 mean PD is slower.

Metric meanings:

| Metric | Meaning |
| --- | --- |
| raw TTFT p99 | 99th percentile time-to-first-token as recorded by SplitwiseSim when the prompt task finishes |
| TTFT + handoff p99 | Raw TTFT plus the delay before the decode/token task starts; in PD this includes KV-cache transfer and token-side queueing |
| TBT p99 | 99th percentile time-between-tokens, a decode-stage latency/smoothness metric |
| E2E p99 | 99th percentile end-to-end request latency from arrival to completion |

Main sweep results:

| Metric | PD better | Share | Median PD / baseline |
| --- | ---: | ---: | ---: |
| TTFT + handoff p99 | 8 / 144 | 5.6% | 1.675 |
| TBT p99 | 109 / 144 | 75.7% | 0.941 |
| E2E p99 | 90 / 144 | 62.5% | 0.962 |

Interpretation:

- PD improves TBT p99 in 109/144 cases, so its strongest benefit is decode-side token generation latency.
- PD improves E2E p99 in 90/144 cases, so decode improvements often carry through to total request latency.
- PD improves TTFT + handoff p99 in only 8/144 cases, because disaggregation adds a KV-cache transfer before decode-side token generation can continue.
- The median TTFT + handoff ratio is 1.675, meaning the prefill-to-decode handoff path is usually worse in this setup even when TBT or E2E improves.

The key takeaway is:

> PD helps when decode-side batching and resource isolation outweigh KV-transfer/handoff overhead. It hurts when handoff delay, low KV bandwidth, long prompts, or a poor prompt/decode resource split dominate.

## What This Fork Adds

| Path | Purpose |
| --- | --- |
| [`PD_DISAGGREGATION_STUDY.md`](PD_DISAGGREGATION_STUDY.md) | Short project overview and main result |
| [`report_draft.md`](report_draft.md) | Main report draft |
| [`experiment_status.md`](experiment_status.md) | Completed experiments, results, and reproduction commands |
| [`pd_disaggregation_deliverables/`](pd_disaggregation_deliverables/) | Report-ready figures, tables, raw CSV summaries, and docs |
| [`scripts/generate_param_traces.py`](scripts/generate_param_traces.py) | Synthetic Poisson trace generation |
| [`scripts/run_param_sweep.py`](scripts/run_param_sweep.py) | Baseline and PD simulation sweep runner |
| [`scripts/aggregate_param_results.py`](scripts/aggregate_param_results.py) | Metric aggregation and PD/baseline ratios |
| [`scripts/plot_param_results.py`](scripts/plot_param_results.py) | Line plots for parameter sweeps |
| [`scripts/plot_param_heatmaps.py`](scripts/plot_param_heatmaps.py) | Heatmaps for crossover regions |
| [`scripts/create_report_assets.py`](scripts/create_report_assets.py) | Copies/creates report-ready tables and figures |
| [`configs/orchestrator_repo/schedulers/mixed_pool_a100_bw*.yml`](configs/orchestrator_repo/schedulers/) | A100-only PD scheduler configs with varied KV bandwidth |

Large raw simulator outputs and generated traces are intentionally not committed. The committed `pd_disaggregation_deliverables/` directory contains the compact results needed for review, reporting, and plotting.

## Experiment Design

The main experiment varies four dimensions:

| Dimension | Values |
| --- | --- |
| Prompt length | 128, 512, 1024, 2048 tokens |
| Output length | 16, 64, 256 tokens |
| Request rate | 20, 50, 100 RPS |
| KV transfer bandwidth | 50, 25, 12.5, 3.125 GB/s |

Fixed setup:

| Component | Setting |
| --- | --- |
| Model | Llama-2-70B |
| Hardware | A100-only |
| Total servers | 8 |
| Coupled baseline | `token_jsq` |
| Main PD split | 4 prompt instances, 4 decode/token instances |
| Arrival process | Poisson synthetic traces |
| Main trace duration | 10 seconds |

Additional checks include:

| Check | Purpose |
| --- | --- |
| Output-512 validation | Test longer generation at smaller scope |
| Resource split sweep | Compare 2:6, 4:4, and 6:2 prompt/decode splits |
| 30-second validation | Check selected cases with longer traces |
| Trace-seed robustness | Confirm favorable/unfavorable cases across independent arrival traces |

## Results And Report Assets

For a quick look, start here:

| File or folder | Contents |
| --- | --- |
| [`pd_disaggregation_deliverables/report_summary.md`](pd_disaggregation_deliverables/report_summary.md) | Compact result summary |
| [`pd_disaggregation_deliverables/report_draft.md`](pd_disaggregation_deliverables/report_draft.md) | Report draft copy |
| [`pd_disaggregation_deliverables/figures/`](pd_disaggregation_deliverables/figures/) | Selected line plots and heatmaps |
| [`pd_disaggregation_deliverables/tables/`](pd_disaggregation_deliverables/tables/) | Report-ready CSV tables |
| [`pd_disaggregation_deliverables/raw_csv/`](pd_disaggregation_deliverables/raw_csv/) | Main aggregated CSV outputs |
| [`pd_disaggregation_deliverables/docs/`](pd_disaggregation_deliverables/docs/) | Experiment plan and status documents |

Representative results:

| Case | Setting | E2E p99 PD / baseline |
| --- | --- | ---: |
| Best observed E2E case | prompt=128, output=64, rate=100 RPS, bandwidth=50 GB/s | 0.671 |
| Worst observed E2E case | prompt=2048, output=256, rate=100 RPS, bandwidth=12.5 GB/s | 1.942 |
| Robust favorable case | p128 o64 r100 bw25, 3 trace seeds | mean 0.664 |
| Robust unfavorable case | p2048 o256 r100 bw25, 3 trace seeds | mean 1.729 |

Core resource-split experiment:

| Split | E2E win share | Median E2E PD / baseline |
| --- | ---: | ---: |
| 2:6 | 66.7% | 0.937 |
| 4:4 | 92.6% | 0.852 |
| 6:2 | 100.0% | 0.828 |

This focused experiment fixes bandwidth at 25 GB/s and sweeps prompt lengths 128/256/512, output lengths 64/128/256, request rates 20/50/100, and prompt:decode splits 2:6/4:4/6:2. In this moderate workload range, the prefill-heavy 6:2 split performs best most often, showing that fixed 4:4 allocation is not generally optimal.

See [`pd_disaggregation_deliverables/docs/core_split_experiment_summary.md`](pd_disaggregation_deliverables/docs/core_split_experiment_summary.md) for details.

Core overlap sensitivity:

| Mode | TTFT + handoff median | E2E win share | Median E2E PD / baseline |
| --- | ---: | ---: | ---: |
| No overlap | 1.555 | 86.4% | 0.869 |
| Overlap | 1.440 | 87.7% | 0.869 |

Overlap reduces the handoff penalty, but in this moderate workload matrix it only slightly changes E2E because PD already improves most E2E cases. The best split distribution is unchanged: 6:2 is best for 17/27 workloads, 4:4 for 9/27, and 2:6 for 1/27.

See [`pd_disaggregation_deliverables/docs/core_split_overlap_summary.md`](pd_disaggregation_deliverables/docs/core_split_overlap_summary.md) for details.

## Metric Note

SplitwiseSim's raw `ttft_times` is recorded when the prompt task completes. In this simulator, the prompt task generates the first output token, and the KV-cache transfer happens between the prompt task and the remaining decode/token task. Therefore raw TTFT and KV handoff delay are separate effects.

This study reports the derived metric:

```text
effective_ttft = ttft_times + nth_token_overheads
```

The CSV column is named `effective_ttft_*`, but conceptually it is better read as `TTFT + handoff overhead` or `first decode-token readiness`, not pure user-visible TTFT. It is useful for exposing the PD handoff penalty.

## Reproducing The Main Sweep

Create and activate a Python 3.11 environment:

```bash
conda create -n splitwise-sim python=3.11
conda activate splitwise-sim
pip install -r requirements.txt
```

Generate traces:

```bash
python scripts/generate_param_traces.py \
  --prompts 128,512,1024,2048 \
  --outputs 16,64,256 \
  --rates 20,50,100 \
  --duration 10 \
  --seed 21
```

Run the main baseline/PD sweep:

```bash
python scripts/run_param_sweep.py \
  --prompts 128,512,1024,2048 \
  --outputs 16,64,256 \
  --rates 20,50,100 \
  --bandwidths 50,25,12.5,3.125 \
  --duration 10
```

Aggregate results:

```bash
python scripts/aggregate_param_results.py \
  --prompts 128,512,1024,2048 \
  --outputs 16,64,256 \
  --rates 20,50,100 \
  --bandwidths 50,25,12.5,3.125 \
  --duration 10 \
  --output results/main_o16_o64_o256_pairs.csv
```

Generate report assets:

```bash
python scripts/create_report_assets.py
```

The sweep can be run on CPU because SplitwiseSim is a simulator. Runtime depends on workload size; the full sweep is more expensive than a single sanity run but does not require GPUs.

## Repository Layout

```text
.
+-- configs/                                  # SplitwiseSim configs plus A100-only PD bandwidth configs
+-- scripts/                                  # Experiment automation and plotting scripts
+-- pd_disaggregation_deliverables/            # Compact report-ready results
|   +-- figures/
|   +-- tables/
|   +-- raw_csv/
|   +-- docs/
+-- report_draft.md
+-- experiment_status.md
+-- PD_DISAGGREGATION_STUDY.md
+-- run.py                                    # SplitwiseSim entry point
```

## Attribution

This project builds on SplitwiseSim:

```text
https://github.com/Mutinifni/splitwise-sim
```

The original simulator was developed for evaluating Splitwise-style LLM serving. This fork adds the course-project experiment scripts, A100-only PD scheduler variants, result summaries, and report assets for the prefill-decode disaggregation trade-off study.
