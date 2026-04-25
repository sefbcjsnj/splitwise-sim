# When Does Prefill-Decode Disaggregation Help?

## Abstract

This project uses SplitwiseSim to study when prefill-decode (PD) disaggregation improves LLM serving latency. We compare a coupled baseline against a PD architecture over prompt length, output length, request rate, and KV-cache transfer bandwidth. The main result is that PD is not a universal win: it frequently improves decode token latency and often improves end-to-end latency, but it introduces a KV-cache handoff delay between prefill and decode.

In the main A100-only sweep, PD improves p99 time-between-tokens (TBT) in 109/144 cases and p99 end-to-end latency in 90/144 cases. However, it improves p99 TTFT plus handoff overhead in only 8/144 cases. This suggests that PD is most useful when decode-side batching or resource isolation compensates for the extra KV transfer path, and least useful when handoff delay, bandwidth, or the prompt/decode resource split dominate the workload.

## Research Questions

RQ1. How does workload shape affect PD disaggregation?

RQ2. How sensitive is PD disaggregation to KV-cache transfer bandwidth?

RQ3. How does request rate change the crossover point where PD becomes useful?

RQ4. How important is the prompt/decode resource split?

## Experimental Setup

All experiments are simulator-based and run locally using SplitwiseSim. The fixed base setup is:

| Component | Setting |
| --- | --- |
| Model | Llama-2-70B |
| Hardware | A100-only |
| Total servers | 8 |
| Baseline | Coupled serving with `token_jsq` |
| PD | `mixed_pool` with A100 prompt and A100 decode processors |
| Main PD split | 4 prompt instances, 4 decode/token instances |
| Performance model | SplitwiseSim DB model |
| Arrival process | Synthetic Poisson arrivals |

The main sweep varies:

| Variable | Values |
| --- | --- |
| Prompt length | 128, 512, 1024, 2048 tokens |
| Output length | 16, 64, 256 tokens |
| Request rate | 20, 50, 100 RPS |
| KV transfer bandwidth | 50, 25, 12.5, 3.125 GB/s |

This gives 144 complete PD/baseline pairs. Additional checks include a smaller output-512 validation at 20 RPS, a resource-split sweep over 2:6, 4:4, and 6:2 prompt/decode splits, a 30-second validation for two representative cases, and a three-trace-seed robustness check for one favorable and one unfavorable workload.

## Metrics

The primary metrics are p99 TTFT plus handoff overhead, p99 TBT, and p99 end-to-end latency. Ratios are reported as:

```text
PD / baseline
```

A ratio below 1.0 means PD is better.

One important simulator detail is that SplitwiseSim's raw `ttft_times` is recorded at prompt completion. In this simulator, the prompt task generates the first output token, and KV transfer happens between the prompt task and the remaining decode/token task. Therefore this study also reports a stricter derived metric:

```text
effective_ttft = ttft_times + nth_token_overheads
```

The CSV column is called `effective_ttft`, but conceptually it should be read as `TTFT + handoff overhead` or `first decode-token readiness`, not pure user-visible TTFT. It exposes the PD handoff penalty from KV transfer and token-side queueing.

## Results

### 1. PD Improves Decode Latency More Often Than The Handoff Path

Across the 144-point main sweep:

| Metric | PD better | Share | Median PD/baseline |
| --- | ---: | ---: | ---: |
| TTFT + handoff p99 | 8/144 | 5.6% | 1.675 |
| TBT p99 | 109/144 | 75.7% | 0.941 |
| E2E p99 | 90/144 | 62.5% | 0.962 |

The strongest conclusion is that PD helps decode-side behavior much more reliably than the prefill-to-decode handoff path. This matches the intuition that separating prefill and decode can improve decode batching and reduce phase interference, but also introduces KV transfer delay.

Recommended figures:

| Figure | Path |
| --- | --- |
| E2E ratio lines | `results/report_assets/figures/main_e2e_ratio_lines.png` |
| TTFT + handoff ratio lines | `results/report_assets/figures/main_effective_ttft_ratio_lines.png` |
| TBT ratio lines | `results/report_assets/figures/main_tbt_ratio_lines.png` |

### 2. The Best Region Is Short-to-Medium Output Under High Load

The best observed E2E case is:

| Prompt | Output | Rate | Bandwidth | E2E ratio |
| ---: | ---: | ---: | ---: | ---: |
| 128 | 64 | 100 RPS | 50 GB/s | 0.671 |

This means PD reduces p99 end-to-end latency by about 33% in this case. At 25 GB/s, the same workload remains robustly favorable in the trace-seed check, with mean E2E ratio 0.664 over three different arrival traces.

The worst observed E2E case is:

| Prompt | Output | Rate | Bandwidth | E2E ratio |
| ---: | ---: | ---: | ---: | ---: |
| 2048 | 256 | 100 RPS | 12.5 GB/s | 1.942 |

This means PD nearly doubles p99 end-to-end latency in this case. The related 25 GB/s robustness case also remains unfavorable across all three trace seeds, with mean E2E ratio 1.729.

Recommended figures:

| Figure | Path |
| --- | --- |
| E2E heatmap, output 64, 100 RPS | `results/report_assets/figures/heatmap_e2e_o64_r100.png` |
| E2E heatmap, output 256, 100 RPS | `results/report_assets/figures/heatmap_e2e_o256_r100.png` |

### 3. KV Transfer Bandwidth Primarily Hurts The Handoff Path

Bandwidth sensitivity is clearest in the TTFT + handoff metric. PD has to move KV state from prefill workers to decode workers, so lower bandwidth directly increases the delay before decode-side token generation can continue. This is why the handoff-adjusted metric is worse in most PD cases even when TBT or E2E improves.

Recommended figures:

| Figure | Path |
| --- | --- |
| TTFT + handoff heatmap, output 64, 100 RPS | `results/report_assets/figures/heatmap_effective_ttft_o64_r100.png` |
| TTFT + handoff heatmap, output 256, 100 RPS | `results/report_assets/figures/heatmap_effective_ttft_o256_r100.png` |

### 4. Resource Split Is a First-Order Parameter

The resource split sweep shows that a fixed 4:4 prompt/decode allocation is not always optimal.

| Workload | Best split | E2E ratio | TTFT + handoff ratio |
| --- | --- | ---: | ---: |
| p128 o16 r100 | 6:2 | 0.706 | 1.265 |
| p512 o64 r100 | 6:2 | 0.797 | 1.354 |
| p1024 o64 r100 | 6:2 | 1.004 | 1.038 |
| p2048 o256 r100 | 4:4 | 1.518 | 1.606 |

This result matters because PD can look bad simply because the prompt/decode pool ratio is wrong. A practical deployment would need either workload-aware provisioning or an adaptive scheduler.

Recommended figure:

| Figure | Path |
| --- | --- |
| Resource split E2E sensitivity | `results/report_assets/figures/resource_split_e2e.png` |

## Robustness Checks

For a favorable representative point, p128 o64 r100 bw25, PD wins in all three independently generated arrival traces:

| Workload | Mean E2E ratio | Range | Wins |
| --- | ---: | ---: | ---: |
| p128 o64 r100 bw25 | 0.664 | 0.650-0.673 | 3/3 |

For an unfavorable representative point, p2048 o256 r100 bw25, PD loses in all three arrival traces:

| Workload | Mean E2E ratio | Range | Wins |
| --- | ---: | ---: | ---: |
| p2048 o256 r100 bw25 | 1.729 | 1.412-1.956 | 0/3 |

This does not prove full statistical generality, but it supports that the main favorable/unfavorable regimes are not single-trace artifacts.

## Limitations

This is a simulator study, not a direct measurement on production GPU clusters. The performance model is only as accurate as SplitwiseSim's database model.

The main sweep uses 10-second traces to keep local CPU simulation fast. Selected 30-second checks were added, but a final paper version could expand trace duration.

The main matrix covers output lengths up to 256 tokens. Output 512 was tested only as a smaller validation at 20 RPS because long-output/high-load simulations are slower.

The study fixes the main PD allocation to 4:4 except in the resource split sweep. A stronger follow-up would search the best split for every workload.

## Conclusion

Prefill-decode disaggregation helps when decode-side isolation and batching reduce TBT and end-to-end tail latency enough to offset KV transfer overhead. It is not automatically beneficial. In this A100-only SplitwiseSim study, PD often improves TBT and E2E latency, especially for short-to-medium output under high load, but it rarely improves the TTFT + handoff metric. The practical lesson is that PD should be evaluated as a workload-, network-, and allocation-dependent design rather than a universally better serving architecture.

## Reproduction

Main commands:

```powershell
C:\ProgramData\anaconda3\envs\splitwise-sim\python.exe scripts\generate_param_traces.py --prompts 128,512,1024,2048 --outputs 16,64,256 --rates 20,50,100 --duration 10 --seed 21
C:\ProgramData\anaconda3\envs\splitwise-sim\python.exe scripts\run_param_sweep.py --prompts 128,512,1024,2048 --outputs 16,64,256 --rates 20,50,100 --bandwidths 50,25,12.5,3.125 --duration 10
C:\ProgramData\anaconda3\envs\splitwise-sim\python.exe scripts\aggregate_param_results.py --prompts 128,512,1024,2048 --outputs 16,64,256 --rates 20,50,100 --bandwidths 50,25,12.5,3.125 --duration 10 --output results\main_o16_o64_o256_pairs.csv
C:\ProgramData\anaconda3\envs\splitwise-sim\python.exe scripts\create_report_assets.py
```

Report-ready assets are in:

```text
results/report_assets/
```
