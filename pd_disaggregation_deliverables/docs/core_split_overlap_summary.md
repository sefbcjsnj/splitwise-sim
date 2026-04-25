# Core Resource-Split Overlap Experiment Summary

## Goal

This experiment repeats the clean core resource-split matrix with an overlap scheduler. The overlap scheduler approximates hiding most KV handoff cost by using 10x the configured KV bandwidth, following the existing overlap scheduler convention in SplitwiseSim.

The goal is to test whether hiding KV handoff changes the main resource-split conclusion.

## Design

Same matrix as the no-overlap core split experiment:

| Variable | Values |
| --- | --- |
| Prompt length | 128, 256, 512 |
| Output length | 64, 128, 256 |
| Request rate | 20, 50, 100 RPS |
| Prompt:decode split | 2:6, 4:4, 6:2 |
| Total A100 servers | 8 |
| Base KV bandwidth | 25 GB/s |
| Effective overlap bandwidth | 250 GB/s |
| Trace duration | 10 seconds |

This produced 81 overlap-PD runs, reusing the same 27 baseline runs.

## Overlap vs No-Overlap

| Mode | Metric | PD better | Median PD / baseline |
| --- | --- | ---: | ---: |
| No overlap | TTFT + handoff p99 | 0 / 81 | 1.555 |
| Overlap | TTFT + handoff p99 | 10 / 81 | 1.440 |
| No overlap | TBT p99 | 71 / 81 | 0.853 |
| Overlap | TBT p99 | 72 / 81 | 0.845 |
| No overlap | E2E p99 | 70 / 81 | 0.869 |
| Overlap | E2E p99 | 71 / 81 | 0.869 |

Overlap mainly improves the handoff path. It has only a small effect on median E2E in this moderate workload matrix, because many cases already benefit from PD even without overlap.

## Split Sensitivity Under Overlap

| Split | E2E win share | Median E2E ratio | Median TBT ratio | Median TTFT + handoff ratio |
| --- | ---: | ---: | ---: | ---: |
| 2:6 | 66.7% | 0.933 | 0.927 | 2.978 |
| 4:4 | 96.3% | 0.838 | 0.829 | 1.416 |
| 6:2 | 100.0% | 0.824 | 0.824 | 1.161 |

The best-split counts by E2E remain unchanged:

| Split | Best-count |
| --- | ---: |
| 2:6 | 1 |
| 4:4 | 9 |
| 6:2 | 17 |

## Interpretation

The overlap experiment supports two points:

1. KV handoff matters: overlap reduces the handoff penalty.
2. Resource split still matters after overlap: 6:2 remains best most often in this prompt/output range.

This suggests that optimized KV transfer helps, but it does not remove the need for workload-aware prompt/decode resource allocation.

## Files

| File | Purpose |
| --- | --- |
| `pd_disaggregation_deliverables/raw_csv/core_split_overlap_matrix_summary.csv` | Full aggregated overlap core split result |
| `pd_disaggregation_deliverables/tables/core_split_overlap_analysis/overlap_metric_comparison.csv` | No-overlap vs overlap metric comparison |
| `pd_disaggregation_deliverables/tables/core_split_overlap_analysis/overlap_split_comparison.csv` | No-overlap vs overlap split comparison |
| `pd_disaggregation_deliverables/figures/core_split_overlap_analysis/` | Overlap split plots and heatmaps |
