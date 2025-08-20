#!/usr/bin/env python3
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

import cv2
import numpy as np
from PIL import Image

import SABER_reader2


def normalize_to_uint8(arr: np.ndarray, p_low: float, p_high: float) -> np.ndarray:
    """Min-max normalize using percentile clipping and map to [0, 255] uint8."""
    p_lo = np.percentile(arr, p_low)
    p_hi = np.percentile(arr, p_high)
    arr = np.clip(arr, p_lo, p_hi)
    # Guard against division by zero if p_lo == p_hi
    denom = (arr.max() - arr.min()) if arr.max() != arr.min() else 1.0
    arr = (arr - arr.min()) / denom * 255.0
    return arr.astype(np.uint8)


def process_single_run(zarr_path: str, run_idx: int, output_folder: str,
                       p_low: float, p_high: float, padding: int, verbose: bool = True):
    """
    Worker function that processes a single run and returns JSON entries for that run.
    Re-opens the zarr inside the worker (safer for multiprocessing).
    """
    zarr_root = SABER_reader2.SABERZarr(zarr_path)
    run = zarr_root.runs[run_idx]

    sub_output_folder = os.path.join(output_folder, run.run_name)
    os.makedirs(sub_output_folder, exist_ok=True)

    np_array = np.array(run.image_array)
    if verbose:
        print(f"[{run.run_name}] Image array shape: {np_array.shape}, "
              f"min: {np_array.min()}, max: {np_array.max()}")

    norm_img = normalize_to_uint8(np_array, p_low, p_high)

    # Save base image
    base_image_path = os.path.join(sub_output_folder, "image.png")
    Image.fromarray(norm_img).save(base_image_path)

    entries = []

    # Prepare a BGR version for drawing boxes (only when needed)
    for mask in run.masks:
        bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max = mask.bbox

        if (bbox_x_max - bbox_x_min) < 20 or (bbox_y_max - bbox_y_min) < 20 or mask.area < 400:
            continue

        # Apply padding and clamp
        h, w = norm_img.shape[:2]
        x_min = max(0, bbox_x_min - padding)
        y_min = max(0, bbox_y_min - padding)
        x_max = min(w, bbox_x_max + padding)
        y_max = min(h, bbox_y_max + padding)

        # # Masked image: keep pixels within bbox, zero elsewhere
        # masked = np.zeros_like(norm_img)
        # masked[y_min:y_max, x_min:x_max] = norm_img[y_min:y_max, x_min:x_max]

        # masked_path = os.path.join(sub_output_folder, f"{mask.mask_name}_masked.png")
        # Image.fromarray(masked).save(masked_path)

        # Bounded image with rectangle
        bounded = norm_img.copy()
        if bounded.ndim == 2 or (bounded.ndim == 3 and bounded.shape[2] == 1):
            bounded = cv2.cvtColor(bounded, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(bounded, (x_min, y_min), (x_max, y_max), (0, 0, 255), 6)

        rotation_ops = [
            (0, lambda img: img, "r0"),
            (90, lambda img: cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE), "r90"),
            (180, lambda img: cv2.rotate(img, cv2.ROTATE_180), "r180"),
            (270, lambda img: cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE), "r270"),
        ]
        flip_ops = [
            (None, ""),    # no flip → this covers the original
            (1, "fh"),     # horizontal flip
            (0, "fv"),     # vertical flip
        ]

        for _, rot_fn, rtag in rotation_ops:
            rotated = rot_fn(bounded)
            for flip_code, ftag in flip_ops:
                if flip_code is None:
                    aug = rotated
                else:
                    aug = cv2.flip(rotated, flip_code)
                aug_name = f"{mask.mask_name}_bounded_{rtag}{('_' + ftag) if ftag else ''}.png"
                aug_path = os.path.join(sub_output_folder, aug_name)
                cv2.imwrite(aug_path, aug)
                entries.append({
                    "image": aug_path,
                    "image_id": aug_path.replace("/", "_").replace(".png", ""),
                    "caption": [mask.description],
                })

    return entries


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract images and masked/bounded crops from SABER Zarr runs."
    )
    parser.add_argument(
        "--zarr-path",
        default="/hpc/projects/group.czii/jonathan.schwartz/sam2/language/final/10301_ais_ds.zarr",
        help="Path to the SABER Zarr root."
    )
    parser.add_argument(
        "--output-folder",
        default="output_images",
        help="Folder where images and labels.json will be written."
    )
    parser.add_argument(
        "--p-low", type=float, default=20.0,
        help="Lower percentile for clipping (default: 20)."
    )
    parser.add_argument(
        "--p-high", type=float, default=80.0,
        help="Upper percentile for clipping (default: 80)."
    )
    parser.add_argument(
        "--padding", type=int, default=20,
        help="Padding (in pixels) to expand each bounding box (default: 20)."
    )
    parser.add_argument(
        "--workers", type=int, default=0,
        help="Number of worker processes (0 = use os.cpu_count())."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print per-run image stats."
    )
    return parser.parse_args()


def main():
    args = parse_args()

    os.makedirs(args.output_folder, exist_ok=True)
    output_train_json = os.path.join(args.output_folder, "labels_train.json")
    output_val_json = os.path.join(args.output_folder, "labels_val.json")
    output_test_json = os.path.join(args.output_folder, "labels_test.json")

    # Discover runs (single pass) so we know how many jobs to schedule.
    root = SABER_reader2.SABERZarr(args.zarr_path)
    num_runs = len(root.runs)

    # Choose worker count
    max_workers = args.workers if args.workers > 0 else (os.cpu_count() or 1)

    all_entries = []

    # Parallelize over run indices
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = []
        for run_idx in range(num_runs):
            futures.append(
                ex.submit(
                    process_single_run,
                    args.zarr_path,
                    run_idx,
                    args.output_folder,
                    args.p_low,
                    args.p_high,
                    args.padding,
                    args.verbose,
                )
            )

        # Collect results as they complete; preserve original order by sorting later if needed
        # Here we just extend as completed; JSON order isn't critical, but you can reorder if desired.
        for fut in as_completed(futures):
            entries = fut.result()
            all_entries.extend(entries)

    all_entries = np.array(all_entries)
    np.random.seed(42)
    np.random.shuffle(all_entries)
    # Split entries into train/val/test sets
    train_entries, val_entries, test_entries = np.split(all_entries, [int(0.8 * len(all_entries)), int(0.9 * len(all_entries))])
    # For all train entries, we modify the "caption" to be the first element in the list
    for entry in train_entries:
        entry["caption"] = entry["caption"][0]
    # Write JSON files
    with open(output_train_json, 'w') as f:
        json.dump(train_entries.tolist(), f, indent=4)
    with open(output_val_json, 'w') as f:
        json.dump(val_entries.tolist(), f, indent=4)
    with open(output_test_json, 'w') as f:
        json.dump(test_entries.tolist(), f, indent=4)
    print(f"Wrote {len(all_entries)} entries to {output_train_json}, {output_val_json}, and {output_test_json}")


if __name__ == "__main__":
    main()
