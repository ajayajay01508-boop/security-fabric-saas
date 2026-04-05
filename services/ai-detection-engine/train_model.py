#!/usr/bin/env python3
"""
Train and export the threat detection model.

Usage:
    python train_model.py                      # train + save pkl
    python train_model.py --export-onnx        # also export ONNX
    python train_model.py --samples 50000      # more training data

The script generates synthetic labelled network traffic data,
trains a GradientBoostingClassifier, evaluates it, and saves
the model to models/detector.pkl (and optionally models/detector.onnx).
"""
import argparse
import os
import pickle
import time
import random
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_fscore_support
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

os.makedirs("models", exist_ok=True)

SUSPICIOUS_PORTS = {22, 23, 3389, 445, 1433, 3306, 5432, 6379, 27017, 9200, 4444, 1337}
RISKY_PROTOCOLS  = {"telnet", "ftp"}   # encoded as 1/0

FEATURE_NAMES = [
    "bytes_sent", "bytes_received", "packets", "duration_ms",
    "source_port", "destination_port",
    "is_suspicious_port", "is_risky_protocol",
    "bytes_per_packet", "port_ratio",
]


def generate_sample(is_threat: bool) -> list[float]:
    """Synthesise a single labelled network event feature vector."""
    if is_threat:
        dst_port    = random.choice([4444, 1337, 23, 22, 445, 3389, 6379, 27017, 1433])
        protocol_id = random.choice([0, 1])  # 1=risky
        bytes_sent  = random.randint(1_000_000, 200_000_000)
        bytes_recv  = random.randint(100, 50_000)
        packets     = random.randint(5_000, 100_000)
        duration_ms = random.randint(100, 10_000)
    else:
        dst_port    = random.choice([80, 443, 8080, 8443, 53, 25, 587])
        protocol_id = 0
        bytes_sent  = random.randint(100, 500_000)
        bytes_recv  = random.randint(500, 2_000_000)
        packets     = random.randint(1, 500)
        duration_ms = random.randint(10, 2_000)

    src_port   = random.randint(1024, 65535)
    is_susp    = 1 if dst_port in SUSPICIOUS_PORTS else 0
    bpp        = bytes_sent / max(packets, 1)
    port_ratio = src_port / max(dst_port, 1)

    return [
        bytes_sent, bytes_recv, packets, duration_ms,
        src_port, dst_port, is_susp, protocol_id,
        bpp, port_ratio,
    ]


def build_dataset(n_samples: int, threat_ratio: float = 0.35):
    """Generate n_samples with ~threat_ratio positive class."""
    n_threats  = int(n_samples * threat_ratio)
    n_benign   = n_samples - n_threats

    X = ([generate_sample(True)  for _ in range(n_threats)] +
         [generate_sample(False) for _ in range(n_benign)])
    y = [1] * n_threats + [0] * n_benign

    # Shuffle
    combined = list(zip(X, y))
    random.shuffle(combined)
    X, y = zip(*combined)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def train(n_samples: int = 20_000, export_onnx: bool = False):
    print(f"Generating {n_samples:,} synthetic training samples...")
    t0 = time.time()
    X, y = build_dataset(n_samples)
    print(f"  Dataset ready in {time.time()-t0:.2f}s  "
          f"(threats={y.sum():,}  benign={(y==0).sum():,})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Training GradientBoostingClassifier pipeline...")
    t0 = time.time()
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
            verbose=0,
        )),
    ])
    pipeline.fit(X_train, y_train)
    print(f"  Training complete in {time.time()-t0:.2f}s")

    # Evaluate
    y_pred      = pipeline.predict(X_test)
    y_proba     = pipeline.predict_proba(X_test)[:, 1]
    auc         = roc_auc_score(y_test, y_proba)
    p, r, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary")

    print(f"\n  Test set metrics:")
    print(f"    AUC-ROC   : {auc:.4f}")
    print(f"    Precision : {p:.4f}")
    print(f"    Recall    : {r:.4f}")
    print(f"    F1        : {f1:.4f}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['benign','threat'])}")

    # 5-fold CV
    cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="roc_auc", n_jobs=-1)
    print(f"  5-fold CV AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Save pickle
    pkl_path = "models/detector.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump(pipeline, f)
    size_kb = os.path.getsize(pkl_path) / 1024
    print(f"\n  Model saved → {pkl_path} ({size_kb:.1f} KB)")

    # Optional ONNX export
    if export_onnx:
        try:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType
            initial_type = [("float_input", FloatTensorType([None, X.shape[1]]))]
            onnx_model = convert_sklearn(pipeline, initial_types=initial_type)
            onnx_path = "models/detector.onnx"
            with open(onnx_path, "wb") as f:
                f.write(onnx_model.SerializeToString())
            size_kb = os.path.getsize(onnx_path) / 1024
            print(f"  ONNX model saved → {onnx_path} ({size_kb:.1f} KB)")
        except ImportError:
            print("  (skl2onnx not installed — skipping ONNX export)")

    # Quick inference test
    sample = np.array([generate_sample(True)], dtype=np.float32)
    t0 = time.time()
    for _ in range(1000):
        pipeline.predict_proba(sample)
    inf_ms = (time.time() - t0)
    print(f"  Inference speed: {int(1000/inf_ms):,} predictions/sec")

    return pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Security Fabric threat detector")
    parser.add_argument("--samples",     type=int,  default=20_000, help="Training samples (default 20000)")
    parser.add_argument("--export-onnx", action="store_true",       help="Also export to ONNX format")
    args = parser.parse_args()

    model = train(n_samples=args.samples, export_onnx=args.export_onnx)
    print("\nDone! Use MODEL_PATH=models/detector.pkl in your .env")
