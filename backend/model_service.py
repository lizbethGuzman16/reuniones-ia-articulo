from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import h5py
import joblib
import numpy as np
import torch

from ml.common import encode_texts
from ml.config import LABEL_NAMES, LABEL_ORDER
from ml.models import TfidfMLP, create_sequence_model

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"


@lru_cache(maxsize=1)
def load_artifacts() -> dict[str, object]:
    metadata_path = MODELS / "best_model_metadata.json"
    h5_path = MODELS / "best_model.h5"
    pt_path = MODELS / "best_model.pt"
    if not metadata_path.exists() or not (h5_path.exists() or pt_path.exists()):
        raise FileNotFoundError("No existe el modelo entrenado. Ejecute el experimento científico.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    model_name = str(metadata["model_name"])
    if metadata["type"] == "tfidf":
        vectorizer = joblib.load(MODELS / "tfidf_vectorizer.joblib")
        model = TfidfMLP(len(vectorizer.get_feature_names_out()), len(LABEL_ORDER), hidden_dim=128, dropout=0.3)
        artifacts: dict[str, object] = {"vectorizer": vectorizer}
    else:
        vocab = json.loads((MODELS / "vocab.json").read_text(encoding="utf-8"))
        model = create_sequence_model(model_name, len(vocab), len(LABEL_ORDER))
        artifacts = {"vocab": vocab}
    if h5_path.exists():
        state_dict: dict[str, torch.Tensor] = {}
        with h5py.File(h5_path, "r") as handle:
            group = handle["state_dict"]
            for name in group.keys():
                state_dict[name] = torch.tensor(group[name][...])
        model.load_state_dict(state_dict)
        artifact_file = h5_path.name
    else:
        model.load_state_dict(torch.load(pt_path, map_location="cpu", weights_only=True))
        artifact_file = pt_path.name
    model.eval()
    artifacts.update({"model": model, "metadata": metadata, "artifact_file": artifact_file})
    return artifacts


def predict_texts(texts: list[str]) -> list[dict[str, object]]:
    artifacts = load_artifacts()
    model = artifacts["model"]
    metadata = artifacts["metadata"]
    if metadata["type"] == "tfidf":
        matrix = artifacts["vectorizer"].transform(texts).toarray()
        inputs = torch.tensor(matrix, dtype=torch.float32)
    else:
        inputs = torch.tensor(encode_texts(texts, artifacts["vocab"], int(metadata.get("seq_len", 40))), dtype=torch.long)
    with torch.no_grad():
        probabilities = torch.softmax(model(inputs), dim=1).cpu().numpy()
    results = []
    for text, probs in zip(texts, probabilities):
        idx = int(np.argmax(probs))
        label = LABEL_ORDER[idx]
        results.append({
            "text": text,
            "label_code": label,
            "label": LABEL_NAMES[label],
            "confidence": float(probs[idx]),
            "probabilities": {LABEL_NAMES[code]: float(probs[i]) for i, code in enumerate(LABEL_ORDER)},
            "model": metadata["model_name"],
            "artifact_file": artifacts["artifact_file"],
        })
    return results
