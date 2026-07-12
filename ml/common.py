from __future__ import annotations

import json
import random
import re
import time
from collections import Counter
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize

from ml.config import CFG, LABEL_NAMES, LABEL_ORDER

TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")


def set_seed(seed: int = CFG.seed) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))


def clean_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.lower().replace("==", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_splits(raw_dir: Path) -> dict[str, pd.DataFrame]:
    splits: dict[str, pd.DataFrame] = {}
    for name in ("train", "dev", "test"):
        path = raw_dir / f"mrda_{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"No se encontró {path}")
        df = pd.read_csv(path)
        required = {"Utterance", "Dialogue_Act", "Dialogue_ID", "Speaker"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"Faltan columnas en {path.name}: {sorted(missing)}")
        df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")], errors="ignore")
        df["Utterance"] = df["Utterance"].map(clean_text)
        df = df[df["Dialogue_Act"].isin(LABEL_ORDER)].copy()
        df = df[df["Utterance"].str.len() > 0].drop_duplicates(
            subset=["Utterance_ID"], keep="first"
        )
        df["split"] = name
        splits[name] = df.reset_index(drop=True)
    return splits


def build_vocab(texts: Iterable[str], max_vocab: int = CFG.max_vocab) -> dict[str, int]:
    counter = Counter(token for text in texts for token in TOKEN_RE.findall(text))
    vocab = {"<PAD>": 0, "<UNK>": 1}
    for idx, (token, _) in enumerate(counter.most_common(max_vocab - 2), start=2):
        vocab[token] = idx
    return vocab


def encode_texts(texts: Iterable[str], vocab: dict[str, int], seq_len: int = CFG.seq_len) -> np.ndarray:
    texts = list(texts)
    encoded = np.zeros((len(texts), seq_len), dtype=np.int64)
    for row_idx, text in enumerate(texts):
        ids = [vocab.get(tok, 1) for tok in TOKEN_RE.findall(text)[:seq_len]]
        if ids:
            encoded[row_idx, : len(ids)] = ids
    return encoded


def labels_to_ids(labels: Iterable[str]) -> np.ndarray:
    mapping = {label: idx for idx, label in enumerate(LABEL_ORDER)}
    return np.asarray([mapping[label] for label in labels], dtype=np.int64)


def ids_to_labels(ids: Iterable[int]) -> list[str]:
    return [LABEL_ORDER[int(idx)] for idx in ids]


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }
    try:
        y_bin = label_binarize(y_true, classes=np.arange(len(LABEL_ORDER)))
        metrics["roc_auc_macro_ovr"] = float(
            roc_auc_score(y_bin, probabilities, average="macro", multi_class="ovr")
        )
    except ValueError:
        metrics["roc_auc_macro_ovr"] = float("nan")
    return metrics


def classification_report_frame(y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    report = classification_report(
        y_true,
        y_pred,
        labels=np.arange(len(LABEL_ORDER)),
        target_names=[LABEL_NAMES[x] for x in LABEL_ORDER],
        output_dict=True,
        zero_division=0,
    )
    return pd.DataFrame(report).T.reset_index(names="clase")


def save_state_dict_h5(model: torch.nn.Module, path: Path, metadata: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        handle.attrs["format"] = "PyTorch state_dict serialized in HDF5"
        handle.attrs["metadata_json"] = json.dumps(metadata, ensure_ascii=False)
        group = handle.create_group("state_dict")
        for name, tensor in model.state_dict().items():
            group.create_dataset(name, data=tensor.detach().cpu().numpy())


def model_size_mb(path: Path) -> float:
    return round(path.stat().st_size / (1024 * 1024), 4) if path.exists() else float("nan")


def timed_prediction(model: torch.nn.Module, x: torch.Tensor, batch_size: int = CFG.batch_size) -> tuple[np.ndarray, np.ndarray, float]:
    model.eval()
    outputs: list[np.ndarray] = []
    started = time.perf_counter()
    with torch.no_grad():
        for start in range(0, len(x), batch_size):
            logits = model(x[start : start + batch_size])
            probs = torch.softmax(logits, dim=1).cpu().numpy()
            outputs.append(probs)
    elapsed = time.perf_counter() - started
    probabilities = np.vstack(outputs)
    return probabilities.argmax(axis=1), probabilities, elapsed
