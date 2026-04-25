# Prefill-Decode Disaggregation Study

This fork adds a simulator-based parametric study for:

```text
When Does Prefill-Decode Disaggregation Help?
```

The study uses SplitwiseSim to compare a coupled baseline against prefill-decode disaggregation across prompt length, output length, request rate, KV transfer bandwidth, and prompt/decode resource split.

## Main Result

Prefill-decode disaggregation is not a universal latency win. In the main A100-only sweep, it improves:

| Metric | PD better | Median PD / baseline |
| --- | ---: | ---: |
| TTFT + handoff p99 | 8 / 144 | 1.675 |
| TBT p99 | 109 / 144 | 0.941 |
| E2E p99 | 90 / 144 | 0.962 |

The key trade-off is that PD often improves decode-token latency and sometimes end-to-end latency, but KV-cache transfer usually hurts the handoff path between prefill and decode. The underlying CSV column is named `effective_ttft`, but it is best interpreted as `TTFT + handoff overhead`, not pure user-visible TTFT.

## Core Resource-Split Result

A focused follow-up experiment fixes KV bandwidth at 25 GB/s and sweeps:

```text
prompt = 128, 256, 512
output = 64, 128, 256
rate = 20, 50, 100 RPS
prompt:decode split = 2:6, 4:4, 6:2
```

In this matrix, PD improves E2E p99 in 70/81 cases without overlap and 71/81 cases with overlap. The prefill-heavy 6:2 split is best most often, winning 17/27 workload points by E2E. This shows that PD performance depends strongly on matching resource split to the workload's prefill demand, decode demand, and KV handoff cost.

## Where To Look

| Path | Contents |
| --- | --- |
| `report_draft.md` | Main report draft |
| `experiment_status.md` | Experiment status and reproduction commands |
| `pd_disaggregation_deliverables/` | Report-ready tables, figures, raw CSV summaries, and docs |
| `scripts/` | Trace generation, sweep, aggregation, and plotting scripts |
| `configs/orchestrator_repo/schedulers/mixed_pool_a100_bw*.yml` | A100-only PD scheduler configs with varied KV bandwidth |

Large raw simulator outputs and generated traces are intentionally not committed.
