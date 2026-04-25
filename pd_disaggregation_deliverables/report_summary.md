# Report Assets Summary

## Coverage

The main sweep contains 144 complete PD/baseline pairs over prompt length, output length, request rate, and KV transfer bandwidth.

Fixed setup: Llama-2-70B, A100-only, 8 total servers, coupled baseline with `token_jsq`, and PD with a 4:4 prompt/decode split unless otherwise noted.

## Key Results

- TTFT + handoff p99 improved in 8/144 cases (5.6%). Median PD/baseline ratio: 1.675.
- TBT p99 improved in 109/144 cases (75.7%). Median PD/baseline ratio: 0.941.
- E2E p99 improved in 90/144 cases (62.5%). Median PD/baseline ratio: 0.962.

This supports the main trade-off: PD often improves decode-token latency and sometimes end-to-end latency, but KV transfer usually worsens the handoff path between prefill and decode. The underlying CSV column is named `effective_ttft`, but it should be read as TTFT plus handoff overhead, not pure user-visible TTFT.

## Best and Worst E2E Cases

Best E2E case: prompt=128, output=64, rate=100 RPS, bandwidth=50 GB/s, E2E ratio=0.671.
Worst E2E case: prompt=2048, output=256, rate=100 RPS, bandwidth=12.5 GB/s, E2E ratio=1.942.

## Robustness

- p128_o64_r100_bw25: E2E mean=0.664, range=[0.650, 0.673], wins=3/3 seeds.
- p2048_o256_r100_bw25: E2E mean=1.729, range=[1.412, 1.956], wins=0/3 seeds.

## Output 512 Validation

- prompt=128, rate=20 RPS, bandwidth=25 GB/s: E2E ratio=0.971, TTFT + handoff ratio=1.178.
- prompt=512, rate=20 RPS, bandwidth=25 GB/s: E2E ratio=0.937, TTFT + handoff ratio=1.678.
- prompt=1024, rate=20 RPS, bandwidth=25 GB/s: E2E ratio=0.888, TTFT + handoff ratio=2.402.
- prompt=2048, rate=20 RPS, bandwidth=25 GB/s: E2E ratio=0.976, TTFT + handoff ratio=3.030.

## Selected Figures

- `figures\main_e2e_ratio_lines.png`
- `figures\main_effective_ttft_ratio_lines.png`
- `figures\main_tbt_ratio_lines.png`
- `figures\heatmap_e2e_o64_r100.png`
- `figures\heatmap_effective_ttft_o64_r100.png`
- `figures\heatmap_e2e_o256_r100.png`
- `figures\heatmap_effective_ttft_o256_r100.png`
- `figures\resource_split_e2e.png`
- `figures\resource_split_effective_ttft.png`
- `figures\output512_e2e_lines.png`

## Recommended Report Claim

In this simulator study, prefill-decode disaggregation is not a universal latency win. It is most useful when decode batching/resource isolation reduces TBT enough to compensate for KV transfer. It is least favorable when KV handoff delay, low bandwidth, or poorly matched prompt/decode resource splits dominate.
