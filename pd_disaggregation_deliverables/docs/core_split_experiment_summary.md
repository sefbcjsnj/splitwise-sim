# Core Resource-Split Experiment Summary

## Goal

This experiment isolates the load-balance question:

```text
Given a fixed 8-GPU budget and fixed KV bandwidth, how should resources be split between prefill and decode for different prompt/output workloads?
```

Bandwidth is fixed at 25 GB/s so the experiment focuses on workload shape, request rate, and prompt:decode server split.

## Design

| Variable | Values |
| --- | --- |
| Prompt length | 128, 256, 512 |
| Output length | 64, 128, 256 |
| Request rate | 20, 50, 100 RPS |
| Prompt:decode split | 2:6, 4:4, 6:2 |
| Total A100 servers | 8 |
| KV bandwidth | 25 GB/s |
| Trace duration | 10 seconds |

This produced 27 baseline runs and 81 PD runs.

## Main Results

| Metric | PD better | Median PD / baseline |
| --- | ---: | ---: |
| TTFT + handoff p99 | 0 / 81 | 1.555 |
| TBT p99 | 71 / 81 | 0.853 |
| E2E p99 | 70 / 81 | 0.869 |

The strongest result is that PD improves TBT and E2E for most moderate prompt/output workloads, but the handoff path remains worse because PD still has to move KV state from prefill to decode.

## Split Sensitivity

| Split | E2E win share | Median E2E ratio | Median TBT ratio | Median TTFT + handoff ratio |
| --- | ---: | ---: | ---: | ---: |
| 2:6 | 66.7% | 0.937 | 0.929 | 3.054 |
| 4:4 | 92.6% | 0.852 | 0.843 | 1.633 |
| 6:2 | 100.0% | 0.828 | 0.825 | 1.275 |

In this workload range, the prefill-heavy 6:2 split is best most often. It is the best E2E split for 17 of the 27 prompt/output/rate workloads. The 4:4 split is best for 9 workloads, and 2:6 is best for only 1 workload.

## Interpretation

These results suggest that, for Llama-2-70B in SplitwiseSim with prompt lengths up to 512 and output lengths up to 256, the bottleneck is not purely decode. Under a fixed 8-GPU budget, giving too few GPUs to prefill causes handoff and queueing penalties that can erase decode-side gains.

This supports the refined project claim:

```text
PD effectiveness depends on matching the prefill/decode resource split to the workload's prefill demand, decode demand, and KV handoff cost.
```

The result also aligns with DistServe/Splitwise-style arguments: PD helps by decoupling phases, but resource allocation must be phase-aware. A fixed 4:4 split is only a baseline, not a generally optimal policy.

## Files

| File | Purpose |
| --- | --- |
| `pd_disaggregation_deliverables/raw_csv/core_split_matrix_summary.csv` | Full aggregated core split result |
| `pd_disaggregation_deliverables/tables/core_split_analysis/metric_summary.csv` | Overall metric summary |
| `pd_disaggregation_deliverables/tables/core_split_analysis/summary_by_split.csv` | Split-level summary |
| `pd_disaggregation_deliverables/tables/core_split_analysis/best_split_by_workload.csv` | Best split for each workload |
| `pd_disaggregation_deliverables/figures/core_split_analysis/` | Core split plots and heatmaps |
