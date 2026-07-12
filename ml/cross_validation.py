from __future__ import annotations

import time

import numpy as np
import pandas as pd
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.utils.class_weight import compute_class_weight
from torch import nn

from ml.common import build_vocab, encode_texts, labels_to_ids, load_splits, set_seed
from ml.config import CFG, DATA_RAW, LABEL_ORDER, TABLES_DIR
from ml.models import TfidfMLP, create_sequence_model


def balanced_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    if not n or n >= len(df):
        return df.copy()
    proportions = df["Dialogue_Act"].value_counts(normalize=True)
    parts = []
    for label, prop in proportions.items():
        count = max(10, int(round(n * prop)))
        part = df[df["Dialogue_Act"] == label].sample(min(count, (df["Dialogue_Act"] == label).sum()), random_state=CFG.seed)
        parts.append(part)
    return pd.concat(parts).sample(frac=1, random_state=CFG.seed).reset_index(drop=True).head(n)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def train_mlp_fold(train_text: list[str], train_y: np.ndarray, val_text: list[str], val_y: np.ndarray) -> tuple[np.ndarray, float]:
    vectorizer = TfidfVectorizer(max_features=2500, ngram_range=(1, 2), min_df=2)
    xtr = vectorizer.fit_transform(train_text)
    xva = vectorizer.transform(val_text)
    model = TfidfMLP(xtr.shape[1], len(LABEL_ORDER), hidden_dim=64, dropout=0.25)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    weights = torch.tensor(compute_class_weight(class_weight="balanced", classes=np.arange(len(LABEL_ORDER)), y=train_y), dtype=torch.float32)
    criterion = nn.CrossEntropyLoss(weight=weights)
    idx = np.arange(len(train_y))
    started = time.perf_counter()
    for _ in range(2):
        np.random.default_rng(CFG.seed).shuffle(idx)
        model.train()
        for start in range(0, len(idx), 256):
            batch = idx[start : start + 256]
            xb = torch.tensor(xtr[batch].toarray(), dtype=torch.float32)
            yb = torch.tensor(train_y[batch], dtype=torch.long)
            optimizer.zero_grad(); logits = model(xb); loss = criterion(logits, yb); loss.backward(); optimizer.step()
    model.eval()
    with torch.no_grad():
        pred = model(torch.tensor(xva.toarray(), dtype=torch.float32)).argmax(1).numpy()
    return pred, time.perf_counter() - started


def train_sequence_fold(name: str, train_text: list[str], train_y: np.ndarray, val_text: list[str], val_y: np.ndarray) -> tuple[np.ndarray, float]:
    vocab = build_vocab(train_text, max_vocab=6000)
    xtr = torch.tensor(encode_texts(train_text, vocab, seq_len=32), dtype=torch.long)
    xva = torch.tensor(encode_texts(val_text, vocab, seq_len=32), dtype=torch.long)
    ytr = torch.tensor(train_y, dtype=torch.long)
    model = create_sequence_model(name, len(vocab), len(LABEL_ORDER), embedding_dim=32, hidden_dim=32) if name in {"LSTM", "BiLSTM-Atencion"} else create_sequence_model(name, len(vocab), len(LABEL_ORDER), embedding_dim=32)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    weights = torch.tensor(compute_class_weight(class_weight="balanced", classes=np.arange(len(LABEL_ORDER)), y=train_y), dtype=torch.float32)
    criterion = nn.CrossEntropyLoss(weight=weights)
    loader = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(xtr, ytr), batch_size=256, shuffle=True)
    started = time.perf_counter()
    for _ in range(2):
        model.train()
        for xb, yb in loader:
            optimizer.zero_grad(); logits = model(xb); loss = criterion(logits, yb); loss.backward(); optimizer.step()
    model.eval()
    with torch.no_grad():
        pred = model(xva).argmax(1).numpy()
    return pred, time.perf_counter() - started


def run_cross_validation() -> pd.DataFrame:
    set_seed()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    data = load_splits(DATA_RAW)["train"]
    data = balanced_sample(data, CFG.cv_sample_size)
    y = labels_to_ids(data["Dialogue_Act"])
    groups = data["Dialogue_ID"].astype(str).to_numpy()
    splitter = StratifiedGroupKFold(n_splits=CFG.cv_folds, shuffle=True, random_state=CFG.seed)
    output_path = TABLES_DIR / "validacion_cruzada_5_folds.csv"
    rows = []
    if output_path.exists():
        rows = pd.read_csv(output_path).to_dict("records")
    completed = {(int(r["fold"]), str(r["modelo"])) for r in rows}
    models = ["MLP-TFIDF", "CNN-1D", "LSTM", "CNN-BiLSTM", "BiLSTM-Atencion"]
    texts = data["Utterance"].tolist()
    for fold, (train_idx, val_idx) in enumerate(splitter.split(texts, y, groups), start=1):
        train_text = [texts[i] for i in train_idx]
        val_text = [texts[i] for i in val_idx]
        train_y, val_y = y[train_idx], y[val_idx]
        for model_name in models:
            if (fold, model_name) in completed:
                continue
            if model_name == "MLP-TFIDF":
                pred, seconds = train_mlp_fold(train_text, train_y, val_text, val_y)
            else:
                pred, seconds = train_sequence_fold(model_name, train_text, train_y, val_text, val_y)
            row = {"fold": fold, "modelo": model_name, **evaluate(val_y, pred), "tiempo_seg": seconds, "n_train": len(train_idx), "n_validacion": len(val_idx)}
            rows.append(row)
            pd.DataFrame(rows).to_csv(output_path, index=False)
            print(f"fold={fold} modelo={model_name} f1={row['f1_macro']:.4f}", flush=True)
    results = pd.DataFrame(rows)
    summary = results.groupby("modelo").agg({"accuracy": ["mean", "std"], "f1_macro": ["mean", "std"], "precision_macro": "mean", "recall_macro": "mean", "tiempo_seg": "mean"})
    summary.columns = ["_".join(x).rstrip("_") for x in summary.columns]
    summary.reset_index().to_csv(TABLES_DIR / "validacion_cruzada_resumen.csv", index=False)
    return results


if __name__ == "__main__":
    print(run_cross_validation().to_string(index=False))
