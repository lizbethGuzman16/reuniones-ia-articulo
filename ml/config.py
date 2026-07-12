from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _path_env(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).resolve()


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in {"0", "none", "full", "all"}:
        return 0
    return int(value)


DATA_RAW = _path_env("DATA_RAW_DIR", ROOT / "data" / "raw")
DATA_PROCESSED = _path_env("DATA_PROCESSED_DIR", ROOT / "data" / "processed")
MODELS_DIR = _path_env("MODELS_DIR", ROOT / "models")
REPORTS_DIR = _path_env("REPORTS_DIR", ROOT / "reports")
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"

LABEL_NAMES = {
    "s": "Declaración",
    "d": "Pregunta declarativa",
    "b": "Retroalimentación breve",
    "f": "Continuación / seguimiento",
    "q": "Pregunta",
}
LABEL_ORDER = ["s", "d", "b", "f", "q"]

@dataclass(frozen=True)
class ExperimentConfig:
    seed: int = _int_env("ML_SEED", 42)
    max_vocab: int = _int_env("MAX_VOCAB", 12000)
    seq_len: int = _int_env("SEQ_LEN", 40)
    embedding_dim: int = _int_env("EMBEDDING_DIM", 48)
    hidden_dim: int = _int_env("HIDDEN_DIM", 48)
    batch_size: int = _int_env("BATCH_SIZE", 256)
    epochs: int = _int_env("EPOCHS", 2)
    learning_rate: float = float(os.getenv("LEARNING_RATE", "0.001"))
    tfidf_features: int = _int_env("TFIDF_FEATURES", 2500)
    train_sample_size: int = _int_env("TRAIN_SAMPLE_SIZE", 30000)
    cv_folds: int = _int_env("CV_FOLDS", 5)
    cv_sample_size: int = _int_env("CV_SAMPLE_SIZE", 8000)
    cv_epochs: int = _int_env("CV_EPOCHS", 1)
    tuning_trials: int = _int_env("TUNING_TRIALS", 4)
    tuning_sample_size: int = _int_env("TUNING_SAMPLE_SIZE", 20000)

CFG = ExperimentConfig()
