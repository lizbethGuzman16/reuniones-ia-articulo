from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from livekit import api as livekit_api

from backend.livekit_workflow import (
    components_ready,
    finish_egress,
    meeting_id_from_room,
    room_name_for,
    start_participant_recording,
    start_room_recording,
)
from backend.model_service import load_artifacts, predict_texts
from backend.vincora_services import (
    AudioSource,
    ProcessingService,
    SupabaseREST,
    VincoraServiceError,
    integration_status,
)

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


class LiveKitTokenRequest(BaseModel):
    meeting_id: str = Field(min_length=1, max_length=100)
    participant_id: str = Field(min_length=1, max_length=100)
    participant_name: str = Field(min_length=1, max_length=120)


class LiveKitEndRoomRequest(BaseModel):
    meeting_id: str = Field(min_length=1, max_length=100)
    generate_report: bool = True
    notify_when_ready: bool = True


def _require_internal_key(value: str) -> None:
    expected = os.getenv("VINCORA_INTERNAL_API_KEY", "").strip()
    if not expected or not secrets.compare_digest(value, expected):
        raise HTTPException(status_code=401, detail="Solicitud no autorizada")


def _run_meeting_process(meeting_id: str) -> dict[str, Any]:
    store = SupabaseREST()
    recordings = store.select(
        "grabaciones",
        columns=(
            "tipo,participante_identity,participante_nombre,ruta_objeto,estado"
        ),
        filters={"reunion_id": meeting_id, "estado": "completada"},
        order="creado_en.asc",
    )
    participant_recordings = [
        item for item in recordings if item.get("tipo") == "participante"
    ]
    selected = participant_recordings or [
        item for item in recordings if item.get("tipo") == "reunion"
    ]
    if not selected:
        raise VincoraServiceError(
            "La grabación todavía no terminó de transferirse"
        )
    sources = [
        AudioSource(
            item["ruta_objeto"],
            speaker_hint=(
                item.get("participante_nombre")
                or item.get("participante_identity")
                or "No especificado"
            ),
            stored=True,
        )
        for item in selected
    ]
    return ProcessingService(supabase=store).run(meeting_id, sources)


async def _process_when_recording_is_ready(meeting_id: str) -> None:
    for _ in range(30):
        try:
            await asyncio.to_thread(_run_meeting_process, meeting_id)
            return
        except VincoraServiceError as exc:
            if "todavía no terminó" not in str(exc):
                logger.exception("meeting_process_failed", extra={"meeting_id": meeting_id})
                return
        except Exception:
            logger.exception("meeting_process_failed", extra={"meeting_id": meeting_id})
            return
        await asyncio.sleep(4)
    logger.error("meeting_recording_timeout", extra={"meeting_id": meeting_id})


@app.post("/livekit/token")
async def livekit_token(
    payload: LiveKitTokenRequest,
    x_vincora_internal_key: str = Header(default=""),
) -> dict[str, str]:
    """Genera tokens LiveKit únicamente para el frontend autenticado de VINCORA."""
    livekit_url = os.getenv("LIVEKIT_URL", "").strip()
    api_key = os.getenv("LIVEKIT_API_KEY", "").strip()
    api_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
    internal_key = os.getenv("VINCORA_INTERNAL_API_KEY", "").strip()
    if not all((livekit_url, api_key, api_secret, internal_key)):
        raise HTTPException(status_code=503, detail="LiveKit no está configurado completamente.")
    if not secrets.compare_digest(x_vincora_internal_key, internal_key):
        raise HTTPException(status_code=401, detail="Solicitud no autorizada.")
    room_name = room_name_for(payload.meeting_id)
    identity = f"{payload.participant_id}-{secrets.token_hex(4)}"[:128]
    token = (
        livekit_api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(payload.participant_name)
        .with_grants(
            livekit_api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )
    recording_state = "not_configured"
    ready = components_ready()
    if ready["livekit"] and ready["storage"]:
        try:
            recording = await start_room_recording(payload.meeting_id)
            recording_state = str(recording.get("estado") or "iniciada")
        except Exception:
            recording_state = "error"
            logger.exception(
                "room_egress_start_failed", extra={"meeting_id": payload.meeting_id}
            )
    return {
        "server_url": livekit_url,
        "participant_token": token,
        "room_name": room_name,
        "recording_state": recording_state,
    }


@app.post("/livekit/end-room")
async def livekit_end_room(
    payload: LiveKitEndRoomRequest,
    background_tasks: BackgroundTasks,
    x_vincora_internal_key: str = Header(default=""),
) -> dict[str, Any]:
    livekit_url = os.getenv("LIVEKIT_URL", "").strip()
    api_key = os.getenv("LIVEKIT_API_KEY", "").strip()
    api_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
    internal_key = os.getenv("VINCORA_INTERNAL_API_KEY", "").strip()
    if not all((livekit_url, api_key, api_secret, internal_key)):
        raise HTTPException(status_code=503, detail="LiveKit no está configurado completamente.")
    if not secrets.compare_digest(x_vincora_internal_key, internal_key):
        raise HTTPException(status_code=401, detail="Solicitud no autorizada.")
    room_name = room_name_for(payload.meeting_id)
    livekit = livekit_api.LiveKitAPI(livekit_url, api_key, api_secret)
    try:
        await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=room_name))
    finally:
        await livekit.aclose()
    processing_state = "not_requested"
    if payload.generate_report:
        background_tasks.add_task(
            _process_when_recording_is_ready, payload.meeting_id
        )
        processing_state = "queued"
    return {
        "status": "ended",
        "room_name": room_name,
        "processing_state": processing_state,
        "notify_when_ready": payload.notify_when_ready,
    }


@app.post("/livekit/webhook")
async def livekit_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    api_key = os.getenv("LIVEKIT_API_KEY", "").strip()
    api_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise HTTPException(status_code=503, detail="LiveKit no configurado.")
    try:
        body = (await request.body()).decode("utf-8")
        event = livekit_api.WebhookReceiver(
            livekit_api.TokenVerifier(api_key, api_secret)
        ).receive(body, request.headers.get("Authorization", ""))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Webhook no válido.") from exc
    if event.event == "participant_joined" and event.room and event.participant:
        meeting_id = meeting_id_from_room(event.room.name)
        if meeting_id:
            try:
                await start_participant_recording(
                    meeting_id,
                    event.participant.identity,
                    event.participant.name or event.participant.identity,
                )
            except Exception:
                logger.exception(
                    "participant_egress_failed", extra={"meeting_id": meeting_id}
                )
    elif event.event == "egress_ended" and event.egress_info:
        try:
            result = finish_egress(event.egress_info)
            if result and result["estado"] == "completada":
                meeting_id = result.get("reunion_id")
                record = result.get("registro") or {}
                if meeting_id and record.get("tipo") == "reunion":
                    background_tasks.add_task(
                        _process_when_recording_is_ready, meeting_id
                    )
        except Exception:
            logger.exception("egress_end_failed")
    return {"accepted": True, "event": event.event}


@app.post("/vincora/meetings/{meeting_id}/process")
async def start_meeting_process(
    meeting_id: str,
    background_tasks: BackgroundTasks,
    x_vincora_internal_key: str = Header(default=""),
) -> dict[str, str]:
    _require_internal_key(x_vincora_internal_key)
    background_tasks.add_task(_process_when_recording_is_ready, meeting_id)
    return {"reunion_id": meeting_id, "estado": "encolado"}


@app.get("/vincora/meetings/{meeting_id}/status")
def meeting_process_status(
    meeting_id: str,
    x_vincora_internal_key: str = Header(default=""),
) -> dict[str, Any]:
    _require_internal_key(x_vincora_internal_key)
    try:
        store = SupabaseREST()
        processes = store.select(
            "procesamientos_reunion",
            filters={"reunion_id": meeting_id},
            order="actualizado_en.desc",
            limit=1,
        )
        reports = store.select(
            "informes_reunion",
            filters={"reunion_id": meeting_id},
            order="actualizado_en.desc",
            limit=1,
        )
        recordings = store.select(
            "grabaciones",
            columns="tipo,participante_nombre,estado,ruta_objeto",
            filters={"reunion_id": meeting_id},
            order="creado_en.asc",
        )
        segments = store.select(
            "segmentos_reunion",
            columns="texto",
            filters={"reunion_id": meeting_id},
        )
        counts = {"temas": 0, "acuerdos": 0, "tareas": 0, "decisiones": 0}
        if reports:
            report_id = reports[0]["id"]
            for key, table in (
                ("temas", "temas_tratados"),
                ("acuerdos", "acuerdos"),
                ("tareas", "tareas_detectadas"),
                ("decisiones", "decisiones"),
            ):
                counts[key] = len(
                    store.select(
                        table, columns="id", filters={"informe_id": report_id}
                    )
                )
        return {
            "reunion_id": meeting_id,
            "procesamiento": processes[0] if processes else None,
            "informe": reports[0] if reports else None,
            "conteos": counts,
            "grabaciones": recordings,
            "segmentos": len(segments),
            "palabras": sum(len(str(row.get("texto") or "").split()) for row in segments),
        }
    except VincoraServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/vincora/meetings/{meeting_id}/transcript")
def meeting_transcript(
    meeting_id: str,
    x_vincora_internal_key: str = Header(default=""),
) -> dict[str, Any]:
    _require_internal_key(x_vincora_internal_key)
    try:
        rows = SupabaseREST().select(
            "segmentos_reunion",
            columns=(
                "id,hablante,texto,inicio_segundos,fin_segundos,origen"
            ),
            filters={"reunion_id": meeting_id},
            order="inicio_segundos.asc",
        )
        return {"reunion_id": meeting_id, "segmentos": rows}
    except VincoraServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict[str, Any]:
    service_status = integration_status()
    service_status.update(components_ready())
    return {
        "status": "ok",
        "service": "reuniones-ia-api",
        "version": "1.1.0",
        "components": service_status,
    }


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
