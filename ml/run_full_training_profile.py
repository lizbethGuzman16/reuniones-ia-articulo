from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def package_versions() -> dict[str, str]:
    names = ["numpy", "pandas", "scikit-learn", "scipy", "h5py", "joblib", "torch", "matplotlib"]
    versions: dict[str, str] = {"python": sys.version, "platform": platform.platform()}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def run_step(command: list[str], env: dict[str, str], log_file: Path) -> None:
    started = datetime.now(timezone.utc).isoformat()
    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"\n\n## {started} :: {' '.join(command)}\n")
        log.flush()
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise SystemExit(f"Fallo {' '.join(command)}. Revise {log_file}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ejecuta el perfil completo MRDA sin sobrescribir los resultados vigentes."
    )
    parser.add_argument("--run-id", default=datetime.now().strftime("full_train_%Y%m%d_%H%M%S"))
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Copia modelos y reportes a las carpetas principales solo si todo el flujo termina correctamente.",
    )
    args = parser.parse_args()

    run_dir = ROOT / "runs" / args.run_id
    models_dir = run_dir / "models"
    reports_dir = run_dir / "reports"
    processed_dir = run_dir / "data" / "processed"
    for path in (models_dir, reports_dir / "figures", reports_dir / "tables", processed_dir):
        path.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "TRAIN_PROFILE": "full_official_train",
            "TRAIN_SAMPLE_SIZE": "full",
            "CV_SAMPLE_SIZE": "full",
            "TUNING_SAMPLE_SIZE": "full",
            "MODELS_DIR": str(models_dir),
            "REPORTS_DIR": str(reports_dir),
            "DATA_PROCESSED_DIR": str(processed_dir),
        }
    )

    config = {
        "profile": "full_official_train",
        "description": "Usa los 83 943 registros oficiales de entrenamiento MRDA/SILICONE.",
        "run_dir": str(run_dir),
        "seed": env.get("ML_SEED", "42"),
        "train_sample_size": "full",
        "cv_sample_size": "full",
        "tuning_sample_size": "full",
        "promote_after_success": bool(args.promote),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "training_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (run_dir / "library_versions.json").write_text(json.dumps(package_versions(), indent=2), encoding="utf-8")

    log_file = run_dir / "training.log"
    steps = [
        [sys.executable, "-m", "ml.eda"],
        [sys.executable, "-m", "ml.train_all"],
        [sys.executable, "-m", "ml.cross_validation"],
        [sys.executable, "-m", "ml.tuning"],
        [sys.executable, "-m", "ml.statistical_tests"],
    ]
    for step in steps:
        run_step(step, env, log_file)

    (run_dir / "COMPLETED.json").write_text(
        json.dumps({"completed_at_utc": datetime.now(timezone.utc).isoformat(), "run_dir": str(run_dir)}, indent=2),
        encoding="utf-8",
    )

    if args.promote:
        shutil.copytree(models_dir, ROOT / "models", dirs_exist_ok=True)
        shutil.copytree(reports_dir, ROOT / "reports", dirs_exist_ok=True)

    print(f"Perfil completo terminado en: {run_dir}")


if __name__ == "__main__":
    main()
