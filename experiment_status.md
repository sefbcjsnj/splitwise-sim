# Experiment Status

## Current Scope

This experiment uses SplitwiseSim to study when prefill-decode disaggregation helps under a CPU-only simulation workflow.

Current fixed setup:

| Dimension | Setting |
| --- | --- |
| Model | `llama2-70b` |
| Hardware | A100-only, `a100-80gb` |
| Total servers | 8 DGX-A100 servers |
| Baseline scheduler | `token_jsq` |
| PD scheduler | `mixed_pool_a100_bw*` |
| Main PD split | 4 prompt instances, 4 token instances |
| Trace duration | 10 seconds for main sweep |
| Validation duration | 30 seconds for selected cases |

## Completed Experiments

### Main Parameter Sweep

Completed:

| Variable | Values |
| --- | --- |
| Prompt length | 128, 512, 1024, 2048 |
| Output length | 16, 64, 256 |
| Request rate | 20, 50, 100 RPS |
| KV bandwidth | 50, 25, 12.5, 3.125 GB/s |

Result:

```text
144 complete PD/baseline pairs
```

Main CSV:

```text
results/main_o16_o64_o256_pairs.csv
```

Main plots:

```text
results/plots/main_o16_o64_o256_pairs_effective_ttft_p99.png
results/plots/main_o16_o64_o256_pairs_tbt_p99.png
results/plots/main_o16_o64_o256_pairs_e2e_p99.png
```

Heatmaps:

```text
results/heatmaps/
```

### Output 512 Validation

Completed a smaller long-output validation at:

```text
output length = 512
request rate = 20 RPS
bandwidth = 25 GB/s
prompt length = 128, 512, 1024, 2048
```

CSV:

```text
results/output512_validation_pairs.csv
```

### Resource Split Sweep

Completed representative resource split sweep:

| Prompt:Token split | Meaning |
| --- | --- |
| 2:6 | decode-heavy |
| 4:4 | balanced |
| 6:2 | prefill-heavy |

Representative workloads:

```text
p128 o16 r100
p512 o64 r100
p1024 o64 r100
p2048 o256 r100
```

CSV:

```text
results/resource_split_summary.csv
```

Plots:

```text
results/resource_split_plots/resource_split_summary_effective_ttft_p99.png
results/resource_split_plots/resource_split_summary_tbt_p99.png
results/resource_split_plots/resource_split_summary_e2e_p99.png
```

### 30-Second Robustness Check

Completed selected 30-second traces:

```text
p128 o16 r100 bw25
p2048 o256 r100 bw25
```

CSV:

```text
results/robustness_30s_complete.csv
```

### Trace-Seed Robustness Check

Completed a small true trace-seed robustness check using independently generated Poisson arrival traces:

```text
trace seeds = 101, 102, 103
p128 o64 r100 bw25
p2048 o256 r100 bw25
```

CSV:

```text
results/report_assets/tables/seed_robustness_per_seed.csv
results/report_assets/tables/seed_robustness_summary.csv
```

Result:

| Workload | Mean E2E PD/baseline | Range | PD wins |
| --- | ---: | ---: | ---: |
| p128 o64 r100 bw25 | 0.664 | 0.650-0.673 | 3 / 3 |
| p2048 o256 r100 bw25 | 1.729 | 1.412-1.956 | 0 / 3 |

### Report Assets

Generated report-ready assets:

```text
report_draft.md
results/report_assets/report_summary.md
results/report_assets/tables/
results/report_assets/figures/
```

The report asset generation script is:

```text
scripts/create_report_assets.py
```

## Preliminary Findings

Across the 144 main parameter points:

| Metric | PD better count | Share | Median PD / baseline |
| --- | ---: | ---: | ---: |
| TTFT + handoff p99 | 8 / 144 | 5.6% | 1.675 |
| TBT p99 | 109 / 144 | 75.7% | 0.941 |
| E2E p99 | 90 / 144 | 62.5% | 0.962 |

Interpretation:

1. PD often improves token generation latency and end-to-end latency.
2. PD rarely improves the TTFT + handoff metric once KV transfer overhead is included.
3. Low bandwidth strongly hurts the prefill-to-decode handoff path.
4. Resource split is a first-order parameter; 4:4 is not always optimal.
5. The most promising PD region so far is short-to-medium output under high request rate, where decode batching benefits dominate.

## Important Metric Note

SplitwiseSim's raw `ttft_times` is recorded when prompt computation completes. In this simulator, the prompt task also generates the first output token, so raw TTFT is the simulator's standard first-token metric.

KV cache transfer happens after prompt completion and before the remaining token task starts. To expose this handoff penalty, this study also computes:

For this study, use:

```text
effective_ttft = ttft_times + nth_token_overheads
```

The column is named `effective_ttft`, but it is best interpreted as `TTFT + handoff overhead` or `first decode-token readiness`, not pure user-visible TTFT. The aggregation script computes:

```text
effective_ttft_p50
effective_ttft_p90
effective_ttft_p99
```

## Remaining Work

Recommended remaining work:

1. Polish the report narrative around the trade-off:

   PD improves TBT/E2E in many settings, but the KV transfer path makes the TTFT + handoff metric worse in most A100-only 4:4 settings.

2. Select final figures for the course submission:

   Use `results/report_assets/figures/`, especially E2E p99 and TTFT + handoff heatmaps.

3. Add one figure showing resource split sensitivity:

   Use `results/resource_split_plots/resource_split_summary_e2e_p99.png`.

4. Optionally run more `output=512` high-load points:

   These are slower and should be used only as validation, not as the main matrix.

5. Optionally add an SLO/goodput analysis:

   Define TTFT/TBT/E2E SLOs and report the highest RPS satisfying them.

## Reproduction Commands

Generate traces:

```powershell
C:\ProgramData\anaconda3\envs\splitwise-sim\python.exe scripts\generate_param_traces.py --prompts 128,512,1024,2048 --outputs 16,64,256 --rates 20,50,100 --duration 10 --seed 21
```

Run main sweep:

```powershell
C:\ProgramData\anaconda3\envs\splitwise-sim\python.exe scripts\run_param_sweep.py --prompts 128,512,1024,2048 --outputs 16,64,256 --rates 20,50,100 --bandwidths 50,25,12.5,3.125 --duration 10
```

Aggregate:

```powershell
C:\ProgramData\anaconda3\envs\splitwise-sim\python.exe scripts\aggregate_param_results.py --prompts 128,512,1024,2048 --outputs 16,64,256 --rates 20,50,100 --bandwidths 50,25,12.5,3.125 --duration 10 --output results\main_o16_o64_o256_pairs.csv
```

Plot:

```powershell
C:\ProgramData\anaconda3\envs\splitwise-sim\python.exe scripts\plot_param_heatmaps.py --input results\main_o16_o64_o256_pairs.csv --output-dir results\heatmaps
```

Create report assets:

```powershell
C:\ProgramData\anaconda3\envs\splitwise-sim\python.exe scripts\create_report_assets.py
```
