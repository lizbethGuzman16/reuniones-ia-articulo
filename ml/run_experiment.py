from __future__ import annotations

import json
import time

from ml.cross_validation import run_cross_validation
from ml.eda import run_eda
from ml.statistical_tests import run_statistical_tests
from ml.train_all import run_training
from ml.tuning import run_tuning
from ml.config import REPORTS_DIR


def main() -> None:
    started = time.perf_counter()
    eda = run_eda()
    comparison = run_training()
    cv = run_cross_validation()
    tuning = run_tuning()
    friedman, wilcoxon = run_statistical_tests()
    manifest = {
        "estado": "completado",
        "duracion_total_seg": time.perf_counter() - started,
        "eda": eda,
        "mejor_modelo": comparison.iloc[0].to_dict(),
        "filas_validacion_cruzada": len(cv),
        "mejor_tuning": tuning.iloc[0].to_dict(),
        "friedman": friedman.iloc[0].to_dict(),
        "comparaciones_wilcoxon": len(wilcoxon),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "manifest_experimento.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, default=float))


if __name__ == "__main__":
    main()
