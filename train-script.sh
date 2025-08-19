set -eux

cd /work
uv venv
source .venv/bin/activate

torchrun --standalone --nprocs_per_node=gpu train.py
