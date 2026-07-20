from __future__ import annotations

import json

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import torch

from ml.common import build_vocab, compute_metrics, encode_texts, labels_to_ids, load_splits, model_size_mb, timed_prediction, set_seed
from ml.config import CFG, DATA_RAW, FIGURES_DIR, LABEL_ORDER, MODELS_DIR, TABLES_DIR
from ml.models import MODEL_NAMES, TfidfMLP, create_sequence_model
from ml.train_all import train_sequence, slug


def evaluate_existing(name: str, test_df: pd.DataFrame, vocab: dict[str, int] | None = None) -> dict[str, object]:
    y_test = labels_to_ids(test_df["Dialogue_Act"])
    history = pd.read_csv(TABLES_DIR / f"historial_{slug(name)}.csv")
    train_seconds = float("nan")
    if name == "MLP-TFIDF":
        vectorizer = joblib.load(MODELS_DIR / "tfidf_vectorizer.joblib")
        x = torch.tensor(vectorizer.transform(test_df["Utterance"]).toarray(), dtype=torch.float32)
        model = TfidfMLP(len(vectorizer.get_feature_names_out()), len(LABEL_ORDER), hidden_dim=128, dropout=0.3)
        path = MODELS_DIR / "mlp_tfidf.pt"
    else:
        assert vocab is not None
        x = torch.tensor(encode_texts(test_df["Utterance"], vocab), dtype=torch.long)
        model = create_sequence_model(name, len(vocab), len(LABEL_ORDER))
        path = MODELS_DIR / f"{slug(name)}.pt"
    model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
    pred, probs, infer_seconds = timed_prediction(model, x)
    metrics = compute_metrics(y_test, pred, probs)
    return {
        "modelo": name,
        **metrics,
        "tiempo_entrenamiento_seg": train_seconds,
        "tiempo_inferencia_seg": infer_seconds,
        "milisegundos_por_registro": infer_seconds / len(y_test) * 1000,
        "tamano_modelo_mb": model_size_mb(path),
        "parametros": sum(p.numel() for p in model.parameters()),
        "epocas": int(history["epoch"].max()),
    }


def main() -> pd.DataFrame:
    set_seed()
    splits = load_splits(DATA_RAW)
    train_df, dev_df, test_df = splits["train"], splits["dev"], splits["test"]
    parts = []
    for label, group in train_df.groupby("Dialogue_Act"):
        count = max(1, min(len(group), int(round(CFG.train_sample_size * len(group) / len(train_df)))))
        parts.append(group.sample(count, random_state=CFG.seed))
    train_sample = pd.concat(parts, ignore_index=True).sample(frac=1, random_state=CFG.seed).reset_index(drop=True)
    vocab = json.loads((MODELS_DIR / "vocab.json").read_text(encoding="utf-8"))
    rows = [
        evaluate_existing(name, test_df, None if name == "MLP-TFIDF" else vocab)
        for name in MODEL_NAMES
    ]
    comparison = pd.DataFrame(rows).sort_values(["f1_macro", "accuracy"], ascending=False).reset_index(drop=True)
    comparison.to_csv(TABLES_DIR / "comparacion_modelos.csv", index=False)
    best_name = str(comparison.iloc[0]["modelo"])
    source = MODELS_DIR / ("mlp_tfidf.pt" if best_name == "MLP-TFIDF" else f"{slug(best_name)}.pt")
    source_h5 = MODELS_DIR / ("mlp_tfidf.h5" if best_name == "MLP-TFIDF" else f"{slug(best_name)}.h5")
    (MODELS_DIR / "best_model.pt").write_bytes(source.read_bytes())
    (MODELS_DIR / "best_model.h5").write_bytes(source_h5.read_bytes())
    metadata = {
        "model_name": best_name,
        "type": "tfidf" if best_name == "MLP-TFIDF" else "sequence",
        "framework": "PyTorch",
        "serialization": "state_dict almacenado en HDF5 mediante h5py; no es un modelo Keras",
        "vectorizer_library": "scikit-learn TfidfVectorizer serializado con joblib" if best_name == "MLP-TFIDF" else None,
        "input_dim": len(joblib.load(MODELS_DIR / "tfidf_vectorizer.joblib").get_feature_names_out()) if best_name == "MLP-TFIDF" else None,
        "vocab_size": len(vocab) if best_name != "MLP-TFIDF" else None,
        "seq_len": CFG.seq_len,
        "labels": LABEL_ORDER,
    }
    (MODELS_DIR / "best_model_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    plt.figure(figsize=(9, 5))
    ordered = comparison.sort_values("f1_macro")
    plt.barh(ordered["modelo"], ordered["f1_macro"])
    plt.xlabel("F1 macro")
    plt.title("Comparación de desempeño de los seis modelos")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "comparacion_f1_modelos.png", dpi=180)
    plt.close()
    print(comparison.to_string(index=False))
    return comparison


if __name__ == "__main__":
    main()
