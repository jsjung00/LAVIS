set -eux

cd /work
uv venv --python=3.8
source .venv/bin/activate

uv pip install -e .

# single node training
torchrun \
  --standalone \
  --nproc_per_node=gpu \
  train.py --cfg-path lavis/projects/blip2/train/caption_coco_ft.yaml

# multinode training
# torchrun --nproc_per_node=8 --nnodes=3 train.py --cfg-path lavis/projects/blip2/train/caption_coco_ft.yaml
