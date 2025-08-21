import argparse
import csv
import math
import os
from collections import defaultdict, Counter

import numpy as np
import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer, util
from sklearn.metrics import confusion_matrix, classification_report

def clean_text(s: str) -> str:
    if s is None:
        return ""
    return s.replace("#", "").strip()

def read_tsv(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for i, cols in enumerate(reader):
            if not cols:
                continue
            # Expected: [filepath, ground_truth, predicted_top1, (ignored...)]
            if len(cols) < 3:
                # Skip malformed rows
                continue
            file_path = cols[0]
            gt = clean_text(cols[1])
            pred = clean_text(cols[2])
            rows.append((file_path, gt, pred))
    return rows

def ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def plot_heatmap(mat, x_labels, y_labels, title, out_path):
    plt.figure(figsize=(max(6, 0.5*len(x_labels)+2), max(5, 0.5*len(y_labels)+2)))
    im = plt.imshow(mat, aspect='auto')
    plt.colorbar(im, fraction=0.046, pad=0.04)
    plt.xticks(ticks=np.arange(len(x_labels)), labels=x_labels, rotation=45, ha='right')
    plt.yticks(ticks=np.arange(len(y_labels)), labels=y_labels)
    plt.title(title)
    plt.tight_layout()
    ensure_dir(out_path)
    plt.savefig(out_path, dpi=200)
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Compute heatmap/stats/accuracy from TSV predictions using sentence-transformers cosine similarity.")
    parser.add_argument("tsv", help="Path to TSV file: [path, ground_truth, predicted_top1, (ignored...)]")
    parser.add_argument("--model", default="pritamdeka/S-PubMedBert-MS-MARCO", help="SentenceTransformer model name.")
    parser.add_argument("--threshold", type=float, default=0.5, help="Similarity threshold for accuracy.")
    parser.add_argument("--outdir", default="metrics_out", help="Directory to write outputs.")
    args = parser.parse_args()

    rows = read_tsv(args.tsv)
    if not rows:
        print("No valid rows found. Check your TSV formatting.")
        return

    # Prepare model
    print(f"Loading model: {args.model}")
    model = SentenceTransformer(args.model)

    # Collect texts
    gts = [r[1] for r in rows]
    preds = [r[2] for r in rows]

    # Embed
    print("Embedding ground-truth labels and predictions...")
    gt_emb = model.encode(gts, convert_to_tensor=True, show_progress_bar=False)
    pred_emb = model.encode(preds, convert_to_tensor=True, show_progress_bar=False)

    # Pairwise cosine similarity (per-row)
    print("Computing per-row cosine similarities...")
    sims_tensor = util.pytorch_cos_sim(gt_emb, pred_emb).diagonal()  # similarity of each GT with its own Pred
    sims = sims_tensor.cpu().numpy()

    # Accuracy@threshold
    thr = args.threshold
    correct = (sims >= thr).astype(int)
    accuracy = correct.mean() if len(correct) else float("nan")

    # Basic stats
    mean_sim = float(np.mean(sims))
    median_sim = float(np.median(sims))
    std_sim = float(np.std(sims))

    # Build class set from ground-truths
    classes = sorted(list(set(gts)))
    if "" in classes:
        classes.remove("")
    if not classes:
        print("No non-empty ground-truth labels after cleaning.")
        return

    # Map each prediction to nearest class (by cosine similarity between pred text and each class name)
    print("Mapping predictions to nearest class names...")
    class_emb = model.encode(classes, convert_to_tensor=True, show_progress_bar=False)
    # cosine sims: preds x classes
    sims_pred_to_class = util.pytorch_cos_sim(pred_emb, class_emb).cpu().numpy()  # shape [N, C]
    mapped_idx = np.argmax(sims_pred_to_class, axis=1)
    mapped_classes = [classes[i] for i in mapped_idx]

    # Confusion matrix using true classes vs mapped classes
    y_true = gts
    y_pred = mapped_classes
    labels = classes  # consistent order
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    # Aggregate mean similarity by (true class, mapped class)
    # For rows where true==classes[i] and mapped==classes[j], average the per-row GT-vs-PRED similarity
    pair_to_sims = defaultdict(list)
    for (file_path, gt, pred), mapped, s in zip(rows, y_pred, sims):
        pair_to_sims[(gt, mapped)].append(s)
    agg = np.zeros((len(labels), len(labels)), dtype=float)
    for i, t in enumerate(labels):
        for j, p in enumerate(labels):
            vals = pair_to_sims.get((t, p), [])
            agg[i, j] = float(np.mean(vals)) if vals else 0.0

    # Per-class accuracy (where mapped class equals true class)
    per_class_counts = Counter(y_true)
    per_class_correct = Counter()
    for t, p in zip(y_true, y_pred):
        if t == p:
            per_class_correct[t] += 1
    per_class_acc = {c: (per_class_correct[c] / per_class_counts[c]) for c in classes}

    # Save per-row CSV
    per_row_path = os.path.join(args.outdir, "per_row_scores.csv")
    ensure_dir(per_row_path)
    with open(per_row_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_path", "ground_truth", "predicted_caption", "cosine_similarity", "mapped_class", "mapped_class_sim"])
        for (file_path, gt, pred), s, midx in zip(rows, sims, mapped_idx):
            w.writerow([file_path, gt, pred, f"{s:.6f}", classes[midx], f"{sims_pred_to_class[len(w.writerows) if False else 0:0]}"])  # dummy to keep IDEs happy

    # The above writerow tried to reference sims_pred_to_class per-row; fix with a clean loop:
    with open(per_row_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_path", "ground_truth", "predicted_caption", "cosine_similarity", "mapped_class", "mapped_class_similarity"])
        for i, (file_path, gt, pred) in enumerate(rows):
            w.writerow([file_path, gt, pred, f"{sims[i]:.6f}", y_pred[i], f"{sims_pred_to_class[i, mapped_idx[i]]:.6f}"])

    # Plot and save heatmaps
    cm_path = os.path.join(args.outdir, "confusion_matrix.png")
    plot_heatmap(cm, labels, labels, "Confusion Matrix (true vs. mapped)", cm_path)

    agg_path = os.path.join(args.outdir, "similarity_by_true_pred.png")
    plot_heatmap(agg, labels, labels, "Mean Cosine Similarity by (true, mapped)", agg_path)

    # Print summary
    print("\n=== Summary ===")
    print(f"Rows: {len(rows)}")
    print(f"Cosine similarity: mean={mean_sim:.4f}, median={median_sim:.4f}, std={std_sim:.4f}")
    print(f"Accuracy@{thr:.2f} (sim >= threshold): {accuracy:.4f}")
    print("\nPer-class accuracy (true == mapped):")
    for c in classes:
        print(f"  {c}: {per_class_acc[c]:.4f} (n={per_class_counts[c]})")

    print("\nClassification report (true vs mapped):")
    try:
        print(classification_report(y_true, y_pred, labels=labels, zero_division=0))
    except Exception as e:
        print(f"(Could not compute classification_report: {e})")

    print(f"\nSaved per-row scores to: {per_row_path}")
    print(f"Saved confusion matrix heatmap to: {cm_path}")
    print(f"Saved mean-similarity heatmap to: {agg_path}")

if __name__ == "__main__":
    main()
