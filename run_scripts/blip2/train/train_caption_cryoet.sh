export OMP_NUM_THREADS=16
python -m torch.distributed.run --nproc_per_node=2 train.py --cfg-path lavis/projects/blip2/train/caption_coco_ft_cryoet.yaml