#!/usr/bin/env bash
# One-shot Linux (VM) build + run of the A4 baseline.
# Run from anywhere inside a copy of the A4-baseline folder:
#     bash A4-baseline/scripts/vm_run.sh
# Results are written to A4-baseline/results/baseline/raw/ of this copy.
set -euo pipefail

A4_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS3_DIR="${NS3_DIR:-$HOME/ns-3-a4}"
NS3_TAG="${NS3_TAG:-ns-3.44}"
RUNS="${RUNS:-30}"
SAMPLES="${SAMPLES:-3334}"
JOBS="${JOBS:-$(nproc)}"

echo "== 1/5 packages"
if ! command -v g++ >/dev/null || ! command -v cmake >/dev/null || ! command -v git >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y g++ cmake ninja-build python3 git
fi
g++ --version | head -1

echo "== 2/5 ns-3 ($NS3_TAG) in $NS3_DIR"
if [ ! -d "$NS3_DIR" ]; then
    git clone --depth 1 --branch "$NS3_TAG" https://gitlab.com/nsnam/ns-3-dev.git "$NS3_DIR"
fi
cp "$A4_DIR/src/beam-ra-sim.cc" "$NS3_DIR/scratch/beam-ra-sim.cc"

echo "== 3/5 build (core module only)"
cd "$NS3_DIR"
./ns3 configure -d optimized --enable-modules=core --disable-examples --disable-tests \
    --disable-python-bindings
./ns3 build
EXE="$(find "$NS3_DIR/build/scratch" -maxdepth 1 -type f -name '*beam-ra-sim*' -perm -u+x | head -1)"
[ -n "$EXE" ] || { echo "beam-ra-sim executable not found"; exit 1; }
echo "executable: $EXE"

echo "== 4/5 self-test"
"$EXE" --selfTest=true

echo "== 5/5 experiment matrix: 3 patterns x 21 M x $RUNS runs x $SAMPLES samples, $JOBS jobs"
cd "$A4_DIR"
time python3 scripts/run_baseline.py --exe "$EXE" --runs "$RUNS" --samples "$SAMPLES" --jobs "$JOBS"
{
    echo "ns3_tag=$NS3_TAG"
    echo "ns3_commit=$(git -C "$NS3_DIR" rev-parse --short HEAD)"
    echo "compiler=$(g++ --version | head -1)"
    echo "os=$(. /etc/os-release && echo "$PRETTY_NAME")"
    echo "runs=$RUNS samples=$SAMPLES jobs=$JOBS date=$(date -Iseconds)"
} > results/baseline/raw/environment.txt
echo
echo "DONE. Copy these files back to Windows A4-baseline/results/baseline/raw/:"
ls -l results/baseline/raw/
