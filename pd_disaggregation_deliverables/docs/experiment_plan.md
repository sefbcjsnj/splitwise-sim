# Experiment Plan: When Does Prefill-Decode Disaggregation Help?

## 1. Goal

This project studies when prefill-decode disaggregation (PD disaggregation) improves LLM serving performance, and when its benefits are offset by KV cache transfer overhead or poor prompt/decode resource allocation.

The central question is:

> Under what workload, network, and traffic conditions does PD disaggregation outperform a coupled baseline?

We will use SplitwiseSim as a fast, low-cost simulator. The study should be framed as a simulator-based parametric study, not as a full production serving-system reproduction.

## 2. Main Research Questions

1. How does workload shape affect PD disaggregation?

   We vary prompt length and output length. The hypothesis is that PD helps most when prompts are long and outputs are short-to-medium, because prefill isolation reduces head-of-line blocking. PD may help less, or hurt, when output length dominates and decode resources become the bottleneck.

2. How sensitive is PD disaggregation to KV transfer bandwidth?

   We vary network bandwidth. The hypothesis is that low bandwidth increases KV transfer time and can erase TTFT or E2E gains from phase separation.

3. How does request rate change the crossover point?

   We vary request arrival rate. The hypothesis is that at low load, PD overhead may not be worthwhile, while at high load, dedicated prefill/decode pools can improve batching and reduce interference.

4. How important is the prompt/decode resource split?

   We vary the number of prompt and token instances. The hypothesis is that PD must be provisioned carefully; a bad prompt/token ratio can make PD look worse even when the architecture could help.

## 3. Systems Compared

### Coupled Baseline

All requests run prefill and decode on the same instance pool.

Recommended SplitwiseSim settings:

```powershell
applications.0.scheduler=token_jsq
start_state=baseline
cluster=half_half
cluster.servers.0.count=<num_a100>
cluster.servers.1.count=0
performance_model=db
applications.0.model_architecture=llama2-70b
applications.0.model_size=llama2-70b-fp16
```

### PD Disaggregated

Prefill and decode run on separate instance pools, with KV cache transfer between them.

Recommended A100-only settings:

```powershell
applications.0.scheduler=<mixed_pool_bandwidth_config>
start_state=splitwise
start_state.split_type=homogeneous
cluster=half_half
cluster.servers.0.count=<num_a100>
cluster.servers.1.count=0
start_state.prompt.num_instances=<num_prompt_instances>
start_state.token.num_instances=<num_token_instances>
performance_model=db
applications.0.model_architecture=llama2-70b
applications.0.model_size=llama2-70b-fp16
```

Note: SplitwiseSim's default `mixed_pool` config uses H100 for prompt and A100 for token. For an A100-only study, create separate scheduler YAML files that point both prompt and token processors to `a100-80gb`.

## 4. Independent Variables

Primary sweep:

| Variable | Values |
| --- | --- |
| Prompt length | 128, 512, 1024, 2048 tokens |
| Output length | 16, 64, 256, 512 tokens |
| KV transfer bandwidth | 50, 25, 12.5, 3.125 GB/s |
| Request rate | 20, 50, 100 RPS |

This gives 4 x 4 x 4 x 3 = 192 workload/network points.

For each point, run both coupled baseline and PD disaggregated. That gives 384 simulation runs for the main experiment.

Secondary resource-split sweep:

Use a smaller subset of representative workloads and vary prompt/token allocation:

| Total A100 servers | Prompt:Token splits |
| --- | --- |
| 8 | 2:6, 4:4, 6:2 |
| 16 | 4:12, 8:8, 12:4 |

This tests whether PD wins only under the right resource allocation.

## 5. Controlled Variables

Use these defaults unless explicitly varied:

| Controlled variable | Setting |
| --- | --- |
| Model | `llama2-70b` |
| Model size | `llama2-70b-fp16` |
| Hardware | DGX-A100, using `a100-80gb` processors |
| Performance model | `performance_model=db` |
| Arrival process | Poisson arrivals |
| Scheduler baseline | `token_jsq` |
| Scheduler PD | A100-only `mixed_pool` variants |
| Seed | Start with `seed=0`; optionally repeat with 1, 2 |

## 6. Metrics

SplitwiseSim already outputs most metrics needed in `summary.csv` and `detailed/0.csv`.

Primary metrics:

| Metric | SplitwiseSim field |
| --- | --- |
| TTFT | `ttft_times_*` |
| TBT / TPOT approximation | `tbt_times_*` |
| End-to-end latency | `response_times_*` |
| Queue time | `queue_times_*` |
| KV transfer overhead | `nth_token_overheads_*` and `request_nodes.csv` |

Use p50, p90, and p99 for TTFT, TBT, and E2E latency.

Derived metrics:

| Derived metric | Definition |
| --- | --- |
| TTFT improvement | `baseline_ttft_p99 / pd_ttft_p99` |
| E2E improvement | `baseline_e2e_p99 / pd_e2e_p99` |
| TBT ratio | `pd_tbt_p99 / baseline_tbt_p99` |
| Goodput | Highest RPS satisfying TTFT/TBT/E2E SLOs |
| Crossover boundary | Parameter region where PD ratio crosses 1.0 |

## 7. Experiment Phases

### Phase 0: Local Sanity Check

Confirm the environment and run one tiny baseline and one tiny PD case.

Baseline:

```powershell
conda activate splitwise-sim
cd C:\Users\Administrator\Desktop\splitwise\splitwise-sim

python run.py applications.0.model_architecture=llama2-70b applications.0.model_size=llama2-70b-fp16 applications.0.scheduler=token_jsq cluster=half_half cluster.servers.0.count=1 cluster.servers.1.count=0 start_state=baseline performance_model=db trace.filename=test_trace seed=0
```

PD:

```powershell
python run.py applications.0.model_architecture=llama2-70b applications.0.model_size=llama2-70b-fp16 applications.0.scheduler=mixed_pool cluster=half_half cluster.servers.0.count=1 cluster.servers.1.count=1 start_state=splitwise start_state.split_type=heterogeneous performance_model=db trace.filename=test_trace seed=0
```

The second command uses the default H100/A100 mixed setup only as a quick sanity check. The real A100-only experiment needs new scheduler configs.

### Phase 1: Create Synthetic Traces

Generate trace CSVs under `splitwise-sim/traces/`.

Each trace should contain:

```text
request_id,request_type,application_id,arrival_timestamp,batch_size,prompt_size,token_size
```

Use:

```text
request_type = 2
application_id = 0
batch_size = 1
arrival_timestamp = cumulative exponential inter-arrival times
```

Suggested filename format:

```text
param_p{prompt}_o{output}_r{rps}.csv
```

Example:

```text
param_p1024_o64_r50.csv
```

### Phase 2: Add Bandwidth Scheduler Configs

Create A100-only PD scheduler configs:

```text
configs/orchestrator_repo/schedulers/mixed_pool_a100_bw50.yml
configs/orchestrator_repo/schedulers/mixed_pool_a100_bw25.yml
configs/orchestrator_repo/schedulers/mixed_pool_a100_bw12_5.yml
configs/orchestrator_repo/schedulers/mixed_pool_a100_bw3_125.yml
```

Each should set:

```yaml
_target_: scheduler.MixedPoolScheduler
overheads: {}
executor_overheads:
  submit_task: 0
  submit_flow: 0
  finish_request: 0
prompt_processors: ["a100-80gb"]
token_processors: ["a100-80gb"]
prompt_max_pending_batch_tokens: 8192
token_max_pending_batch_tokens: 2048
transfer_bandwidth: <bandwidth>
```

### Phase 3: Main Sweep

For each trace and bandwidth:

1. Run baseline once.
2. Run PD with fixed prompt/token split.
3. Collect `summary.csv` and `detailed/0.csv`.

Recommended starting resource size:

```text
Total A100 servers: 8
Baseline: 8 coupled instances
PD: 4 prompt instances, 4 token instances
```

Example baseline command:

```powershell
python run.py applications.0.model_architecture=llama2-70b applications.0.model_size=llama2-70b-fp16 applications.0.scheduler=token_jsq cluster=half_half cluster.servers.0.count=8 cluster.servers.1.count=0 start_state=baseline performance_model=db trace.filename=param_p1024_o64_r50 seed=0
```

Example PD command:

```powershell
python run.py applications.0.model_architecture=llama2-70b applications.0.model_size=llama2-70b-fp16 applications.0.scheduler=mixed_pool_a100_bw25 cluster=half_half cluster.servers.0.count=8 cluster.servers.1.count=0 start_state=splitwise start_state.split_type=homogeneous start_state.prompt.num_instances=4 start_state.token.num_instances=4 performance_model=db trace.filename=param_p1024_o64_r50 seed=0
```

### Phase 4: Resource Split Sweep

Pick representative cases:

```text
Short prompt / short output: p128_o16
Long prompt / short output: p2048_o16
Long prompt / long output: p2048_o512
```

For each, sweep prompt/token split:

```text
2:6, 4:4, 6:2 for 8 total A100 servers
```

This answers whether PD needs careful provisioning to help.

### Phase 5: Analysis and Plots

Recommended plots:

1. Heatmap: prompt length x bandwidth, colored by `PD / baseline` TTFT p99.
2. Heatmap: output length x bandwidth, colored by `PD / baseline` E2E p99.
3. Line plot: request rate vs TTFT/TBT/E2E ratio.
4. Resource split plot: prompt/token split vs TTFT p99 and TBT p99.
5. Crossover plot: region where PD is better than baseline.

Suggested interpretation rule:

```text
PD helps TTFT if pd_ttft_p99 < baseline_ttft_p99.
PD helps E2E if pd_response_p99 < baseline_response_p99.
PD is SLO-good if TTFT, TBT, and E2E all satisfy chosen SLO thresholds.
```

## 8. Expected Findings

Expected pattern:

1. PD helps most for long prompts and short outputs.
2. PD becomes less useful as output length increases, because decode dominates.
3. Low bandwidth shifts the crossover boundary toward longer prompts or higher load.
4. High request rates make phase separation more valuable, but only if decode resources are not under-provisioned.
5. Prompt/token split is a first-order parameter; fixed 1:1 allocation may hide PD's best case.

## 9. Local Run Status

The local machine already has:

```text
Repository: C:\Users\Administrator\Desktop\splitwise\splitwise-sim
Conda environment: splitwise-sim
Performance database: data/perf_model.csv
Supported model in database: llama2-70b
Supported hardware in database: a100-80gb, h100-80gb, h100-80gb-pcap
```

Small baseline and PD sanity runs with `llama2-70b` have already succeeded locally.

## 10. Next Implementation Tasks

1. Add synthetic trace generation script.
2. Add A100-only bandwidth scheduler YAML configs.
3. Add a sweep runner script for baseline and PD experiments.
4. Add a result aggregation script.
5. Add plotting notebook or plotting script for crossover figures.
