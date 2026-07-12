from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.model_service import load_artifacts, predict_texts

ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_H5_PATH = ROOT_DIR / "models" / "best_model.h5"
MODEL_PT_PATH = ROOT_DIR / "models" / "best_model.pt"
METADATA_PATH = ROOT_DIR / "models" / "best_model_metadata.json"
REPORTS_DIR = ROOT_DIR / "reports"
TABLES_DIR = REPORTS_DIR / "tables"

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("reuniones_ia_api")

app = FastAPI(
    title="API de Clasificación de Actos de Diálogo en Reuniones",
    version="1.0.0",
    description="Consume el mejor modelo entrenado con el corpus público MRDA.",
)
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000, description="Intervención transcrita de una reunión")


class BatchPredictionRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=100)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "reuniones-ia-api", "version": "1.0.0"}


@app.get("/model/status")
def model_status() -> dict[str, object]:
    available = (MODEL_H5_PATH.exists() or MODEL_PT_PATH.exists()) and METADATA_PATH.exists()
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8")) if available else None
    cache_info = load_artifacts.cache_info()
    return {
        "available": available,
        "model_file": MODEL_H5_PATH.name if MODEL_H5_PATH.exists() else MODEL_PT_PATH.name,
        "h5_available": MODEL_H5_PATH.exists(),
        "pt_backup_available": MODEL_PT_PATH.exists(),
        "metadata": metadata,
        "loader_cache": {
            "maxsize": cache_info.maxsize,
            "currsize": cache_info.currsize,
            "hits": cache_info.hits,
            "misses": cache_info.misses,
        },
        "message": "Modelo disponible para inferencia." if available else "No existe un modelo entrenado.",
    }


@app.post("/predict")
def predict(payload: PredictionRequest) -> dict[str, object]:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="El texto no puede estar vacio.")
    try:
        result = predict_texts([text])[0]
        logger.info(
            "prediction_completed",
            extra={"model": result.get("model"), "artifact_file": result.get("artifact_file"), "text_length": len(text)},
        )
        return result
    except FileNotFoundError as exc:
        logger.exception("prediction_model_missing")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("prediction_failed")
        raise HTTPException(status_code=500, detail="No se pudo ejecutar la inferencia.") from exc


@app.post("/predict/batch")
def predict_batch(payload: BatchPredictionRequest) -> dict[str, object]:
    cleaned = [text.strip() for text in payload.texts if text.strip()]
    if not cleaned:
        raise HTTPException(status_code=422, detail="No se recibieron textos válidos.")
    try:
        return {"count": len(cleaned), "predictions": predict_texts(cleaned)}
    except FileNotFoundError as exc:
        logger.exception("batch_prediction_model_missing")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("batch_prediction_failed")
        raise HTTPException(status_code=500, detail="No se pudo ejecutar la inferencia por lotes.") from exc


@app.get("/metrics")
def metrics() -> dict[str, object]:
    path = TABLES_DIR / "comparacion_modelos.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No existe la tabla de resultados.")
    frame = pd.read_csv(path)
    return {"best_model": frame.iloc[0].to_dict(), "models": frame.to_dict(orient="records")}


@app.get("/reports")
def reports() -> dict[str, object]:
    allowed = {".pdf", ".docx", ".xlsx"}
    files = [p.name for p in REPORTS_DIR.iterdir() if p.is_file() and p.suffix.lower() in allowed]
    return {"files": sorted(files)}


@app.get("/reports/{filename}")
def download_report(filename: str):
    safe_name = Path(filename).name
    path = REPORTS_DIR / safe_name
    if not path.exists() or path.suffix.lower() not in {".pdf", ".docx", ".xlsx"}:
        raise HTTPException(status_code=404, detail="Reporte no encontrado.")
    return FileResponse(path, filename=safe_name)
