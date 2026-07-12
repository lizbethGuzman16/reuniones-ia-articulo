from __future__ import annotations

import json
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ml.common import TOKEN_RE, load_splits
from ml.config import DATA_PROCESSED, DATA_RAW, FIGURES_DIR, LABEL_NAMES, LABEL_ORDER, TABLES_DIR


def save_bar(values, labels, title, ylabel, path):
    plt.figure(figsize=(9, 5))
    plt.bar(labels, values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def run_eda() -> dict[str, object]:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    splits = load_splits(DATA_RAW)
    combined = pd.concat(splits.values(), ignore_index=True)
    combined["num_caracteres"] = combined["Utterance"].str.len()
    combined["num_palabras"] = combined["Utterance"].map(lambda x: len(TOKEN_RE.findall(x)))
    combined.to_csv(DATA_PROCESSED / "mrda_clean.csv", index=False)

    class_table = (
        combined.groupby(["split", "Dialogue_Act"]).size().unstack(fill_value=0).reindex(columns=LABEL_ORDER)
    )
    class_table.rename(columns=LABEL_NAMES).to_csv(TABLES_DIR / "eda_distribucion_clases.csv")

    desc = combined[["num_caracteres", "num_palabras"]].describe().T.reset_index(names="variable")
    desc.to_csv(TABLES_DIR / "eda_estadisticos_descriptivos.csv", index=False)

    overall = combined["Dialogue_Act"].value_counts().reindex(LABEL_ORDER)
    save_bar(overall.values, [LABEL_NAMES[x] for x in LABEL_ORDER], "Distribución de clases del corpus MRDA", "Número de intervenciones", FIGURES_DIR / "eda_distribucion_clases.png")

    plt.figure(figsize=(9, 5))
    clipped = combined["num_palabras"].clip(upper=combined["num_palabras"].quantile(0.99))
    plt.hist(clipped, bins=35)
    plt.title("Distribución de longitud de las intervenciones")
    plt.xlabel("Número de palabras")
    plt.ylabel("Frecuencia")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "eda_longitud_textos.png", dpi=180)
    plt.close()

    matrix = class_table.div(class_table.sum(axis=1), axis=0).to_numpy()
    plt.figure(figsize=(9, 4))
    plt.imshow(matrix, aspect="auto")
    plt.colorbar(label="Proporción")
    plt.xticks(np.arange(len(LABEL_ORDER)), [LABEL_NAMES[x] for x in LABEL_ORDER], rotation=20, ha="right")
    plt.yticks(np.arange(len(class_table.index)), class_table.index)
    plt.title("Mapa de calor: proporción de clases por partición")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            plt.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "eda_heatmap_clases_split.png", dpi=180)
    plt.close()

    stop = {"the", "a", "an", "and", "or", "to", "of", "in", "is", "it", "that", "i", "you", "we", "so", "um", "uh"}
    words = Counter(tok for text in combined["Utterance"] for tok in TOKEN_RE.findall(text) if tok not in stop)
    top = words.most_common(20)
    save_bar([v for _, v in top], [k for k, _ in top], "Palabras más frecuentes (sin palabras funcionales básicas)", "Frecuencia", FIGURES_DIR / "eda_palabras_frecuentes.png")

    summary = {
        "dataset": "ICSI Meeting Recorder Dialogue Act (MRDA) dentro de SILICONE",
        "total_registros": int(len(combined)),
        "registros_por_split": {k: int(len(v)) for k, v in splits.items()},
        "reuniones_unicas": int(combined["Dialogue_ID"].nunique()),
        "hablantes_unicos": int(combined["Speaker"].nunique()),
        "duplicados_utterance_id": int(combined["Utterance_ID"].duplicated().sum()),
        "textos_vacios": int((combined["Utterance"].str.len() == 0).sum()),
        "nulos": {k: int(v) for k, v in combined.isna().sum().items()},
        "clases": {LABEL_NAMES[k]: int(v) for k, v in overall.items()},
        "palabras_promedio": float(combined["num_palabras"].mean()),
        "palabras_mediana": float(combined["num_palabras"].median()),
    }
    (TABLES_DIR / "eda_resumen.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run_eda(), ensure_ascii=False, indent=2))
