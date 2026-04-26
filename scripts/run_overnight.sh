#!/usr/bin/env bash
# Overnight experiment runner — overlap only, bandwidth fixed at 25 GB/s
#
# Experiment A: output=16,512 × prompt=128,256,512 × rate=20,50,100 × split=2:6,4:4,6:2
# Experiment B: rate=10,30,70,150 × prompt=128,512 × output=64,128,256 × split=2:6,4:4,6:2

set -e
cd "$(dirname "$0")/.."

PYTHON=python3
BW=25
DURATION=10
PREFIX="overlap_mixed_pool_a100_bw"

echo "============================================"
echo " Step 1: Generate traces"
echo "============================================"

# Experiment A
$PYTHON scripts/generate_param_traces.py \
    --prompts 128,256,512 \
    --outputs 16,512 \
    --rates 20,50,100 \
    --duration $DURATION

# Experiment B
$PYTHON scripts/generate_param_traces.py \
    --prompts 128,512 \
    --outputs 64,128,256 \
    --rates 10,30,70,150 \
    --duration $DURATION

echo ""
echo "============================================"
echo " Step 2: Experiment A — output=16,512"
echo "============================================"

# 2:6 — also runs baseline (shared across splits)
$PYTHON scripts/run_param_sweep.py \
    --prompts 128,256,512 --outputs 16,512 --rates 20,50,100 \
    --bandwidths $BW --duration $DURATION \
    --prompt-instances 2 --token-instances 6 \
    --pd-scheduler-prefix "$PREFIX" \
    --systems baseline,pd \
    --runlog results/overnight_A_2_6_runlog.csv

# 4:4
$PYTHON scripts/run_param_sweep.py \
    --prompts 128,256,512 --outputs 16,512 --rates 20,50,100 \
    --bandwidths $BW --duration $DURATION \
    --prompt-instances 4 --token-instances 4 \
    --pd-scheduler-prefix "$PREFIX" \
    --systems pd \
    --runlog results/overnight_A_4_4_runlog.csv

# 6:2
$PYTHON scripts/run_param_sweep.py \
    --prompts 128,256,512 --outputs 16,512 --rates 20,50,100 \
    --bandwidths $BW --duration $DURATION \
    --prompt-instances 6 --token-instances 2 \
    --pd-scheduler-prefix "$PREFIX" \
    --systems pd \
    --runlog results/overnight_A_6_2_runlog.csv

echo ""
echo "============================================"
echo " Step 3: Experiment B — fine-grained rate"
echo "          output=64,128,256"
echo "============================================"

# 2:6 — also runs baseline
$PYTHON scripts/run_param_sweep.py \
    --prompts 128,512 --outputs 64,128,256 --rates 10,30,70,150 \
    --bandwidths $BW --duration $DURATION \
    --prompt-instances 2 --token-instances 6 \
    --pd-scheduler-prefix "$PREFIX" \
    --systems baseline,pd \
    --runlog results/overnight_B_2_6_runlog.csv

# 4:4
$PYTHON scripts/run_param_sweep.py \
    --prompts 128,512 --outputs 64,128,256 --rates 10,30,70,150 \
    --bandwidths $BW --duration $DURATION \
    --prompt-instances 4 --token-instances 4 \
    --pd-scheduler-prefix "$PREFIX" \
    --systems pd \
    --runlog results/overnight_B_4_4_runlog.csv

# 6:2
$PYTHON scripts/run_param_sweep.py \
    --prompts 128,512 --outputs 64,128,256 --rates 10,30,70,150 \
    --bandwidths $BW --duration $DURATION \
    --prompt-instances 6 --token-instances 2 \
    --pd-scheduler-prefix "$PREFIX" \
    --systems pd \
    --runlog results/overnight_B_6_2_runlog.csv

echo ""
echo "============================================"
echo " Step 4: Aggregate with teammate's script"
echo "============================================"

WORKLOADS_A=$(python3 -c "
ws = []
for p in [128,256,512]:
    for o in [16,512]:
        for r in [20,50,100]:
            ws.append(f'{p}:{o}:{r}')
print(','.join(ws))")

WORKLOADS_B=$(python3 -c "
ws = []
for p in [128,512]:
    for o in [64,128,256]:
        for r in [10,30,70,150]:
            ws.append(f'{p}:{o}:{r}')
print(','.join(ws))")

$PYTHON scripts/aggregate_resource_splits.py \
    --workloads "$WORKLOADS_A" \
    --splits 2:6,4:4,6:2 \
    --duration $DURATION \
    --bandwidth $BW \
    --scheduler-prefix "$PREFIX" \
    --output results/overnight_A_split_summary.csv

$PYTHON scripts/aggregate_resource_splits.py \
    --workloads "$WORKLOADS_B" \
    --splits 2:6,4:4,6:2 \
    --duration $DURATION \
    --bandwidth $BW \
    --scheduler-prefix "$PREFIX" \
    --output results/overnight_B_split_summary.csv

echo ""
echo "============================================"
echo " Done! Output CSVs:"
echo "   results/overnight_A_split_summary.csv  (output=16,512)"
echo "   results/overnight_B_split_summary.csv  (fine-grained rate, o64+o256)"
echo "============================================"
