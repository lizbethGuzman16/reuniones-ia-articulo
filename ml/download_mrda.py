"""Descarga reproducible de MRDA desde el repositorio público SILICONE.

No genera datos sintéticos. Los tres CSV se descargan desde el repositorio
público de los autores del benchmark y se validan por esquema y conteo.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

FILES = {
    "mrda_train.csv": {
        "url": "https://raw.githubusercontent.com/eusip/SILICONE-benchmark/main/mrda/train.csv",
        "sha256": "d7a963aac70eb80d315b76b9e71d82a7888532ef8c6752c84487e34dfce3b7eb",
        "rows": 83943,
    },
    "mrda_dev.csv": {
        "url": "https://raw.githubusercontent.com/eusip/SILICONE-benchmark/main/mrda/dev.csv",
        "sha256": "dc795c60b3825645a20dbb0700e279271fc52eef4bc297564a0227f608a19619",
        "rows": 9815,
    },
    "mrda_test.csv": {
        "url": "https://raw.githubusercontent.com/eusip/SILICONE-benchmark/main/mrda/test.csv",
        "sha256": "8426417d316cb0aa57f13e46e866e8964eed71f719212ab1da1c3cbaa23ea414",
        "rows": 15470,
    },
}
REQUIRED_COLUMNS = {
    "Utterance_ID", "Dialogue_Act", "Channel_ID", "Speaker", "Dialogue_ID", "Utterance"
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "dataset": "ICSI MRDA mediante SILICONE benchmark",
        "license": "CC BY-NC-SA 4.0 según la ficha pública de SILICONE",
        "files": {},
    }
    for filename, meta in FILES.items():
        target = RAW / filename
        if not target.exists() or sha256(target) != meta["sha256"]:
            print(f"Descargando {filename}...")
            urllib.request.urlretrieve(str(meta["url"]), target)
        frame = pd.read_csv(target)
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"{filename}: faltan columnas {sorted(missing)}")
        if len(frame) != meta["rows"]:
            raise ValueError(f"{filename}: se esperaban {meta['rows']} filas y se obtuvieron {len(frame)}")
        calculated = sha256(target)
        if calculated != meta["sha256"]:
            raise ValueError(f"{filename}: SHA-256 distinto al archivo verificado del experimento")
        manifest["files"][filename] = {
            "url": meta["url"],
            "rows": len(frame),
            "sha256": calculated,
        }
        print(f"OK {filename}: {len(frame):,} filas")
    (RAW / "dataset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Descarga y verificación completadas.")


if __name__ == "__main__":
    main()
