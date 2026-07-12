from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon

from ml.config import TABLES_DIR


def holm_adjust(p_values: list[float]) -> list[float]:
    n = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(n, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        value = min(1.0, (n - rank) * p_values[idx])
        running = max(running, value)
        adjusted[idx] = running
    return adjusted.tolist()


def run_statistical_tests() -> tuple[pd.DataFrame, pd.DataFrame]:
    path = TABLES_DIR / "validacion_cruzada_5_folds.csv"
    if not path.exists():
        raise FileNotFoundError("Primero ejecute ml/cross_validation.py")
    cv = pd.read_csv(path)
    pivot = cv.pivot(index="fold", columns="modelo", values="f1_macro").dropna()
    samples = [pivot[col].to_numpy() for col in pivot.columns]
    statistic, p_value = friedmanchisquare(*samples)
    friedman = pd.DataFrame([{
        "prueba": "Friedman",
        "metrica": "F1 macro",
        "estadistico": float(statistic),
        "p_value": float(p_value),
        "alpha": 0.05,
        "diferencia_significativa": bool(p_value < 0.05),
        "n_folds": len(pivot),
        "n_modelos": len(pivot.columns),
    }])
    friedman.to_csv(TABLES_DIR / "prueba_friedman.csv", index=False)

    pairs = []
    raw_p = []
    for a, b in itertools.combinations(pivot.columns, 2):
        try:
            stat, p = wilcoxon(pivot[a], pivot[b], zero_method="wilcox", alternative="two-sided")
        except ValueError:
            stat, p = 0.0, 1.0
        pairs.append({"modelo_a": a, "modelo_b": b, "estadistico": float(stat), "p_value": float(p), "mediana_diferencia": float(np.median(pivot[a] - pivot[b]))})
        raw_p.append(float(p))
    adjusted = holm_adjust(raw_p)
    for row, p_adj in zip(pairs, adjusted):
        row["p_value_holm"] = p_adj
        row["diferencia_significativa"] = bool(p_adj < 0.05)
    wilcoxon_df = pd.DataFrame(pairs).sort_values("p_value_holm")
    wilcoxon_df.to_csv(TABLES_DIR / "wilcoxon_holm.csv", index=False)
    return friedman, wilcoxon_df


if __name__ == "__main__":
    f, w = run_statistical_tests()
    print(f.to_string(index=False))
    print(w.to_string(index=False))
