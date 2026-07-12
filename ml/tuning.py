from __future__ import annotations

import itertools
import time

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score
from sklearn.utils.class_weight import compute_class_weight
from torch import nn

from ml.common import build_vocab, encode_texts, labels_to_ids, load_splits, set_seed
from ml.config import CFG, DATA_RAW, LABEL_ORDER, TABLES_DIR
from ml.models import CNNBiLSTMClassifier


def stratified_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    if not n or n >= len(df):
        return df.copy()
    return df.groupby("Dialogue_Act", group_keys=False).apply(
        lambda x: x.sample(max(1, min(len(x), int(n * len(x) / len(df)))), random_state=CFG.seed)
    ).sample(frac=1, random_state=CFG.seed).reset_index(drop=True)


def run_tuning() -> pd.DataFrame:
    set_seed()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    splits = load_splits(DATA_RAW)
    train = stratified_sample(splits["train"], CFG.tuning_sample_size)
    dev = splits["dev"].sample(min(5000, len(splits["dev"])), random_state=CFG.seed)
    vocab = build_vocab(train["Utterance"], max_vocab=8000)
    xtr = torch.tensor(encode_texts(train["Utterance"], vocab, seq_len=40), dtype=torch.long)
    ytr_np = labels_to_ids(train["Dialogue_Act"])
    ytr = torch.tensor(ytr_np, dtype=torch.long)
    class_weights = compute_class_weight(class_weight="balanced", classes=np.arange(len(LABEL_ORDER)), y=ytr_np)
    class_weights_t = torch.tensor(class_weights, dtype=torch.float32)
    xdv = torch.tensor(encode_texts(dev["Utterance"], vocab, seq_len=40), dtype=torch.long)
    ydv = labels_to_ids(dev["Dialogue_Act"])
    candidates = list(itertools.product([32, 48], [32, 48], [0.2, 0.35], [5e-4, 1e-3]))[: CFG.tuning_trials]
    rows = []
    for trial, (embedding_dim, hidden_dim, dropout, lr) in enumerate(candidates, start=1):
        model = CNNBiLSTMClassifier(len(vocab), len(LABEL_ORDER), embedding_dim=embedding_dim, channels=hidden_dim, hidden_dim=hidden_dim, dropout=dropout)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.CrossEntropyLoss(weight=class_weights_t)
        loader = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(xtr, ytr), batch_size=256, shuffle=True)
        started = time.perf_counter()
        for _epoch in range(2):
            model.train()
            for xb, yb in loader:
                optimizer.zero_grad()
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                optimizer.step()
        model.eval()
        with torch.no_grad(): pred = model(xdv).argmax(1).numpy()
        rows.append({
            "trial": trial,
            "embedding_dim": embedding_dim,
            "hidden_dim": hidden_dim,
            "dropout": dropout,
            "learning_rate": lr,
            "accuracy_validacion": float(accuracy_score(ydv, pred)),
            "f1_macro_validacion": float(f1_score(ydv, pred, average="macro", zero_division=0)),
            "tiempo_seg": time.perf_counter() - started,
        })
    results = pd.DataFrame(rows).sort_values("f1_macro_validacion", ascending=False).reset_index(drop=True)
    results.to_csv(TABLES_DIR / "tuning_cnn_bilstm.csv", index=False)
    results.iloc[[0]].to_csv(TABLES_DIR / "tuning_mejores_hiperparametros.csv", index=False)
    return results


if __name__ == "__main__":
    print(run_tuning().to_string(index=False))
