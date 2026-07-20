from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, roc_curve, auc
from sklearn.preprocessing import label_binarize
from sklearn.utils.class_weight import compute_class_weight
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
import joblib

from ml.common import (
    build_vocab,
    classification_report_frame,
    compute_metrics,
    encode_texts,
    labels_to_ids,
    load_splits,
    model_size_mb,
    save_state_dict_h5,
    set_seed,
    timed_prediction,
)
from ml.config import CFG, DATA_RAW, FIGURES_DIR, LABEL_NAMES, LABEL_ORDER, MODELS_DIR, TABLES_DIR
from ml.models import SEQUENCE_MODEL_NAMES, TfidfMLP, create_sequence_model


def class_weights_tensor(y: np.ndarray) -> torch.Tensor:
    weights = compute_class_weight(class_weight="balanced", classes=np.arange(len(LABEL_ORDER)), y=y)
    return torch.tensor(weights, dtype=torch.float32)


def train_tensor_model(model: nn.Module, x_train: torch.Tensor, y_train: torch.Tensor, x_val: torch.Tensor, y_val: torch.Tensor, epochs: int, lr: float, batch_size: int, class_weights: torch.Tensor) -> tuple[list[dict[str, float]], float]:
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    train_loader = DataLoader(TensorDataset(x_train, y_train), batch_size=batch_size, shuffle=True)
    history: list[dict[str, float]] = []
    started = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct = 0
        seen = 0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            running_loss += float(loss.item()) * len(xb)
            correct += int((logits.argmax(dim=1) == yb).sum())
            seen += len(xb)
        model.eval()
        with torch.no_grad():
            val_logits = model(x_val)
            val_loss = float(criterion(val_logits, y_val).item())
            val_acc = float((val_logits.argmax(dim=1) == y_val).float().mean().item())
        history.append({
            "epoch": epoch,
            "train_loss": running_loss / max(seen, 1),
            "train_accuracy": correct / max(seen, 1),
            "val_loss": val_loss,
            "val_accuracy": val_acc,
        })
    return history, time.perf_counter() - started


def save_confusion(y_true: np.ndarray, y_pred: np.ndarray, name: str) -> None:
    matrix = confusion_matrix(y_true, y_pred, labels=np.arange(len(LABEL_ORDER)))
    plt.figure(figsize=(7, 6))
    plt.imshow(matrix)
    plt.colorbar(label="Cantidad")
    plt.xticks(np.arange(len(LABEL_ORDER)), [LABEL_NAMES[x] for x in LABEL_ORDER], rotation=30, ha="right")
    plt.yticks(np.arange(len(LABEL_ORDER)), [LABEL_NAMES[x] for x in LABEL_ORDER])
    plt.xlabel("Predicción")
    plt.ylabel("Clase real")
    plt.title(f"Matriz de confusión - {name}")
    threshold = matrix.max() / 2 if matrix.size else 0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            plt.text(j, i, str(matrix[i, j]), ha="center", va="center", color="white" if matrix[i, j] > threshold else "black")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f"confusion_{slug(name)}.png", dpi=180)
    plt.close()
    pd.DataFrame(matrix, index=LABEL_ORDER, columns=LABEL_ORDER).to_csv(TABLES_DIR / f"confusion_{slug(name)}.csv")


def save_roc(y_true: np.ndarray, probabilities: np.ndarray, name: str) -> None:
    y_bin = label_binarize(y_true, classes=np.arange(len(LABEL_ORDER)))
    plt.figure(figsize=(8, 6))
    for idx, label in enumerate(LABEL_ORDER):
        fpr, tpr, _ = roc_curve(y_bin[:, idx], probabilities[:, idx])
        plt.plot(fpr, tpr, label=f"{LABEL_NAMES[label]} (AUC={auc(fpr, tpr):.3f})")
    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.xlabel("Tasa de falsos positivos")
    plt.ylabel("Tasa de verdaderos positivos")
    plt.title(f"Curvas ROC multiclase - {name}")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f"roc_{slug(name)}.png", dpi=180)
    plt.close()


def save_history(history: list[dict[str, float]], name: str) -> None:
    df = pd.DataFrame(history)
    df.to_csv(TABLES_DIR / f"historial_{slug(name)}.csv", index=False)
    plt.figure(figsize=(8, 5))
    plt.plot(df["epoch"], df["train_loss"], marker="o", label="Entrenamiento")
    plt.plot(df["epoch"], df["val_loss"], marker="o", label="Validación")
    plt.xlabel("Época")
    plt.ylabel("Pérdida")
    plt.title(f"Curva de pérdida - {name}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / f"loss_{slug(name)}.png", dpi=180)
    plt.close()


def slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_").replace("ó", "o").replace("ó", "o")


def train_mlp_tfidf(train_df: pd.DataFrame, dev_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[dict[str, object], TfidfMLP, TfidfVectorizer]:
    name = "MLP-TFIDF"
    vectorizer = TfidfVectorizer(max_features=CFG.tfidf_features, ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    x_train_sp = vectorizer.fit_transform(train_df["Utterance"])
    x_dev_sp = vectorizer.transform(dev_df["Utterance"])
    x_test_sp = vectorizer.transform(test_df["Utterance"])
    y_train = labels_to_ids(train_df["Dialogue_Act"])
    y_dev = labels_to_ids(dev_df["Dialogue_Act"])
    y_test = labels_to_ids(test_df["Dialogue_Act"])

    model = TfidfMLP(x_train_sp.shape[1], len(LABEL_ORDER), hidden_dim=128, dropout=0.3)
    optimizer = torch.optim.Adam(model.parameters(), lr=CFG.learning_rate)
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor(y_train))
    history = []
    started = time.perf_counter()
    indices = np.arange(len(y_train))
    rng = np.random.default_rng(CFG.seed)
    for epoch in range(1, CFG.epochs + 1):
        rng.shuffle(indices)
        model.train()
        total_loss = 0.0
        correct = 0
        for start in range(0, len(indices), CFG.batch_size):
            idx = indices[start : start + CFG.batch_size]
            xb = torch.tensor(x_train_sp[idx].toarray(), dtype=torch.float32)
            yb = torch.tensor(y_train[idx], dtype=torch.long)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * len(idx)
            correct += int((logits.argmax(1) == yb).sum())
        model.eval()
        with torch.no_grad():
            xdv = torch.tensor(x_dev_sp.toarray(), dtype=torch.float32)
            ydv = torch.tensor(y_dev, dtype=torch.long)
            dev_logits = model(xdv)
            dev_loss = float(criterion(dev_logits, ydv).item())
            dev_acc = float((dev_logits.argmax(1) == ydv).float().mean())
        history.append({"epoch": epoch, "train_loss": total_loss / len(y_train), "train_accuracy": correct / len(y_train), "val_loss": dev_loss, "val_accuracy": dev_acc})
    train_seconds = time.perf_counter() - started
    x_test = torch.tensor(x_test_sp.toarray(), dtype=torch.float32)
    pred, probs, infer_seconds = timed_prediction(model, x_test)
    metrics = compute_metrics(y_test, pred, probs)
    model_path = MODELS_DIR / "mlp_tfidf.pt"
    torch.save(model.state_dict(), model_path)
    joblib.dump(vectorizer, MODELS_DIR / "tfidf_vectorizer.joblib")
    metadata = {"model_name": name, "input_dim": x_train_sp.shape[1], "num_classes": len(LABEL_ORDER), "labels": LABEL_ORDER}
    save_state_dict_h5(model, MODELS_DIR / "mlp_tfidf.h5", metadata)
    save_confusion(y_test, pred, name)
    save_roc(y_test, probs, name)
    save_history(history, name)
    classification_report_frame(y_test, pred).to_csv(TABLES_DIR / f"reporte_{slug(name)}.csv", index=False)
    return {
        "modelo": name,
        **metrics,
        "tiempo_entrenamiento_seg": train_seconds,
        "tiempo_inferencia_seg": infer_seconds,
        "milisegundos_por_registro": infer_seconds / len(y_test) * 1000,
        "tamano_modelo_mb": model_size_mb(model_path),
        "parametros": sum(p.numel() for p in model.parameters()),
        "epocas": CFG.epochs,
    }, model, vectorizer


def train_sequence(name: str, train_df: pd.DataFrame, dev_df: pd.DataFrame, test_df: pd.DataFrame, vocab: dict[str, int]) -> tuple[dict[str, object], nn.Module]:
    x_train = torch.tensor(encode_texts(train_df["Utterance"], vocab), dtype=torch.long)
    x_dev = torch.tensor(encode_texts(dev_df["Utterance"], vocab), dtype=torch.long)
    x_test = torch.tensor(encode_texts(test_df["Utterance"], vocab), dtype=torch.long)
    y_train_np = labels_to_ids(train_df["Dialogue_Act"])
    y_dev_np = labels_to_ids(dev_df["Dialogue_Act"])
    y_test = labels_to_ids(test_df["Dialogue_Act"])
    y_train = torch.tensor(y_train_np, dtype=torch.long)
    y_dev = torch.tensor(y_dev_np, dtype=torch.long)

    model = create_sequence_model(name, len(vocab), len(LABEL_ORDER))
    history, train_seconds = train_tensor_model(model, x_train, y_train, x_dev, y_dev, CFG.epochs, CFG.learning_rate, CFG.batch_size, class_weights_tensor(y_train_np))
    pred, probs, infer_seconds = timed_prediction(model, x_test)
    metrics = compute_metrics(y_test, pred, probs)
    model_path = MODELS_DIR / f"{slug(name)}.pt"
    torch.save(model.state_dict(), model_path)
    metadata = {"model_name": name, "vocab_size": len(vocab), "num_classes": len(LABEL_ORDER), "labels": LABEL_ORDER, "seq_len": CFG.seq_len}
    save_state_dict_h5(model, MODELS_DIR / f"{slug(name)}.h5", metadata)
    save_confusion(y_test, pred, name)
    save_roc(y_test, probs, name)
    save_history(history, name)
    classification_report_frame(y_test, pred).to_csv(TABLES_DIR / f"reporte_{slug(name)}.csv", index=False)
    return {
        "modelo": name,
        **metrics,
        "tiempo_entrenamiento_seg": train_seconds,
        "tiempo_inferencia_seg": infer_seconds,
        "milisegundos_por_registro": infer_seconds / len(y_test) * 1000,
        "tamano_modelo_mb": model_size_mb(model_path),
        "parametros": sum(p.numel() for p in model.parameters()),
        "epocas": CFG.epochs,
    }, model


def run_training() -> pd.DataFrame:
    set_seed()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    splits = load_splits(DATA_RAW)
    train_df, dev_df, test_df = splits["train"], splits["dev"], splits["test"]
    if CFG.train_sample_size and CFG.train_sample_size < len(train_df):
        parts = []
        for label, group in train_df.groupby("Dialogue_Act"):
            count = max(1, min(len(group), int(round(CFG.train_sample_size * len(group) / len(train_df)))))
            parts.append(group.sample(count, random_state=CFG.seed))
        train_df = pd.concat(parts, ignore_index=True).sample(frac=1, random_state=CFG.seed).reset_index(drop=True)
    vocab = build_vocab(train_df["Utterance"])
    (MODELS_DIR / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")
    (MODELS_DIR / "labels.json").write_text(json.dumps({str(i): label for i, label in enumerate(LABEL_ORDER)}, ensure_ascii=False, indent=2), encoding="utf-8")

    rows: list[dict[str, object]] = []
    row, _, _ = train_mlp_tfidf(train_df, dev_df, test_df)
    rows.append(row)
    trained_models: dict[str, nn.Module] = {}
    for name in SEQUENCE_MODEL_NAMES:
        row, model = train_sequence(name, train_df, dev_df, test_df, vocab)
        rows.append(row)
        trained_models[name] = model

    comparison = pd.DataFrame(rows).sort_values(["f1_macro", "accuracy"], ascending=False).reset_index(drop=True)
    comparison.to_csv(TABLES_DIR / "comparacion_modelos.csv", index=False)
    best_name = str(comparison.iloc[0]["modelo"])
    base_metadata = {
        "framework": "PyTorch",
        "serialization": "state_dict almacenado en HDF5 mediante h5py; no es un modelo Keras",
    }
    if best_name == "MLP-TFIDF":
        source = MODELS_DIR / "mlp_tfidf.pt"
        source_h5 = MODELS_DIR / "mlp_tfidf.h5"
        metadata = {
            "model_name": best_name,
            "type": "tfidf",
            **base_metadata,
            "vectorizer_library": "scikit-learn TfidfVectorizer serializado con joblib",
            "input_dim": int(joblib.load(MODELS_DIR / "tfidf_vectorizer.joblib").transform(["test"]).shape[1]),
            "labels": LABEL_ORDER,
        }
    else:
        source = MODELS_DIR / f"{slug(best_name)}.pt"
        source_h5 = MODELS_DIR / f"{slug(best_name)}.h5"
        metadata = {
            "model_name": best_name,
            "type": "sequence",
            **base_metadata,
            "vocab_size": len(vocab),
            "seq_len": CFG.seq_len,
            "labels": LABEL_ORDER,
        }
    (MODELS_DIR / "best_model.pt").write_bytes(source.read_bytes())
    (MODELS_DIR / "best_model.h5").write_bytes(source_h5.read_bytes())
    (MODELS_DIR / "best_model_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    plt.figure(figsize=(9, 5))
    ordered = comparison.sort_values("f1_macro")
    plt.barh(ordered["modelo"], ordered["f1_macro"])
    plt.xlabel("F1 macro")
    plt.title("Comparación de desempeño de los seis modelos")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "comparacion_f1_modelos.png", dpi=180)
    plt.close()

    return comparison


if __name__ == "__main__":
    print(run_training().to_string(index=False))
