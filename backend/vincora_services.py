"""Servicios de infraestructura para el procesamiento verificable de VINCORA.

Las rutas externas usadas aquí son las oficiales de PostgREST/Storage de
Supabase y las APIs ``audio/transcriptions`` y ``responses`` de OpenAI.  Las
tablas asumidas por :class:`ProcessingService` son ``procesamientos_reunion``
y ``segmentos_reunion``; los nombres se pueden cambiar al construir el
servicio sin modificar el resto de la aplicación.

Variables de entorno:

* ``SUPABASE_URL``
* ``SUPABASE_SERVICE_KEY`` (también acepta ``SUPABASE_SERVICE_ROLE_KEY``)
* ``SUPABASE_BUCKET`` (también acepta ``SUPABASE_STORAGE_BUCKET``)
* ``OPENAI_API_KEY``
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import quote

import requests


class VincoraServiceError(RuntimeError):
    """Error controlado al comunicarse con Supabase u OpenAI."""


class EvidenceValidationError(ValueError):
    """La respuesta contiene una afirmación sin evidencia comprobable."""


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.getenv(candidate, "").strip()
        if value:
            return value
    alternatives = ", ".join((name, *aliases))
    raise VincoraServiceError(f"Falta configurar la variable: {alternatives}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def integration_status() -> dict[str, bool]:
    return {
        "supabase": bool(
            os.getenv("SUPABASE_URL", "").strip()
            and (
                os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
                or os.getenv("SUPABASE_SERVICE_KEY", "").strip()
            )
        ),
        "openai": bool(os.getenv("OPENAI_API_KEY", "").strip()),
    }


class SupabaseREST:
    """Cliente mínimo y sin SDK para PostgREST y Storage de Supabase."""

    def __init__(
        self,
        url: str | None = None,
        service_key: str | None = None,
        bucket: str | None = None,
        *,
        session: requests.Session | None = None,
        timeout: tuple[float, float] = (10.0, 60.0),
    ) -> None:
        self.url = (url or _required_env("SUPABASE_URL")).rstrip("/")
        self.service_key = service_key or _required_env(
            "SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY"
        )
        self.bucket = bucket or next(
            (
                value
                for value in (
                    os.getenv("SUPABASE_BUCKET", "").strip(),
                    os.getenv("SUPABASE_RECORDING_BUCKET", "").strip(),
                    os.getenv("SUPABASE_S3_BUCKET", "").strip(),
                    os.getenv("SUPABASE_STORAGE_BUCKET", "").strip(),
                )
                if value
            ),
            "",
        )
        self.session = session or requests.Session()
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any = None,
        data: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        request_headers = self.headers | dict(headers or {})
        try:
            response = self.session.request(
                method,
                f"{self.url}{path}",
                params=params,
                json=json_body,
                data=data,
                headers=request_headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise VincoraServiceError(
                f"No fue posible conectar con Supabase ({method} {path})."
            ) from exc
        if not response.ok:
            detail = response.text[:500].strip()
            raise VincoraServiceError(
                f"Supabase respondió {response.status_code} en {method} {path}: {detail}"
            )
        if response.status_code == 204 or not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.content

    @staticmethod
    def _filters(filters: Mapping[str, Any] | None) -> dict[str, str]:
        encoded: dict[str, str] = {}
        for column, value in (filters or {}).items():
            if isinstance(value, tuple) and len(value) == 2:
                operator, operand = value
                encoded[column] = f"{operator}.{operand}"
            elif value is None:
                encoded[column] = "is.null"
            elif isinstance(value, (list, tuple, set)):
                members = ",".join(str(member) for member in value)
                encoded[column] = f"in.({members})"
            elif isinstance(value, bool):
                encoded[column] = f"eq.{str(value).lower()}"
            else:
                encoded[column] = f"eq.{value}"
        return encoded

    def select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: Mapping[str, Any] | None = None,
        order: str | None = None,
        limit: int | None = None,
        single: bool = False,
    ) -> Any:
        params: dict[str, Any] = {"select": columns} | self._filters(filters)
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = max(0, int(limit))
        headers = {"Accept": "application/vnd.pgrst.object+json"} if single else None
        return self._request(
            "GET", f"/rest/v1/{quote(table, safe='')}", params=params, headers=headers
        )

    def insert(self, table: str, rows: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> Any:
        return self._request(
            "POST",
            f"/rest/v1/{quote(table, safe='')}",
            json_body=rows,
            headers={"Prefer": "return=representation"},
        )

    def update(
        self,
        table: str,
        values: Mapping[str, Any],
        *,
        filters: Mapping[str, Any],
    ) -> Any:
        if not filters:
            raise ValueError("update requiere al menos un filtro")
        return self._request(
            "PATCH",
            f"/rest/v1/{quote(table, safe='')}",
            params=self._filters(filters),
            json_body=values,
            headers={"Prefer": "return=representation"},
        )

    def upsert(
        self,
        table: str,
        rows: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        on_conflict: str | None = None,
    ) -> Any:
        params = {"on_conflict": on_conflict} if on_conflict else None
        return self._request(
            "POST",
            f"/rest/v1/{quote(table, safe='')}",
            params=params,
            json_body=rows,
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
        )

    def delete(self, table: str, *, filters: Mapping[str, Any]) -> Any:
        """Elimina filas, pero nunca permite un DELETE sin filtros."""
        if not filters:
            raise ValueError("delete requiere al menos un filtro")
        return self._request(
            "DELETE",
            f"/rest/v1/{quote(table, safe='')}",
            params=self._filters(filters),
            headers={"Prefer": "return=representation"},
        )

    def upload_bytes(
        self,
        object_path: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
        upsert: bool = True,
    ) -> Any:
        if not self.bucket:
            raise VincoraServiceError("Falta configurar SUPABASE_BUCKET")
        path = "/".join(quote(part, safe="") for part in object_path.strip("/").split("/"))
        return self._request(
            "POST",
            f"/storage/v1/object/{quote(self.bucket, safe='')}/{path}",
            data=content,
            headers={"Content-Type": content_type, "x-upsert": str(upsert).lower()},
        )

    def download_bytes(self, object_path: str) -> bytes:
        if not self.bucket:
            raise VincoraServiceError("Falta configurar SUPABASE_BUCKET")
        path = "/".join(quote(part, safe="") for part in object_path.strip("/").split("/"))
        result = self._request(
            "GET",
            f"/storage/v1/object/authenticated/{quote(self.bucket, safe='')}/{path}",
        )
        if not isinstance(result, bytes):
            raise VincoraServiceError("Supabase Storage no devolvió un archivo")
        return result


MINUTES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "resumen": {"type": "string"},
        "temas": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "titulo": {"type": "string"},
                    "descripcion": {"type": "string"},
                    "evidencias": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"$ref": "#/$defs/evidencia"},
                    },
                },
                "required": ["titulo", "descripcion", "evidencias"],
            },
        },
        "acuerdos": {"type": "array", "items": {"$ref": "#/$defs/accion"}},
        "tareas": {"type": "array", "items": {"$ref": "#/$defs/accion"}},
        "decisiones": {"type": "array", "items": {"$ref": "#/$defs/decision"}},
    },
    "required": ["resumen", "temas", "acuerdos", "tareas", "decisiones"],
    "$defs": {
        "evidencia": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "segmento_id": {"type": "string"},
                "cita": {"type": "string", "minLength": 1},
            },
            "required": ["segmento_id", "cita"],
        },
        "accion": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "descripcion": {"type": "string"},
                "responsable": {"type": "string"},
                "fecha_limite": {"type": "string"},
                "evidencias": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"$ref": "#/$defs/evidencia"},
                },
            },
            "required": ["descripcion", "responsable", "fecha_limite", "evidencias"],
        },
        "decision": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "descripcion": {"type": "string"},
                "evidencias": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"$ref": "#/$defs/evidencia"},
                },
            },
            "required": ["descripcion", "evidencias"],
        },
    },
}


class OpenAIREST:
    """Cliente de OpenAI que usa ``requests`` y no depende del SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        session: requests.Session | None = None,
        timeout: tuple[float, float] = (10.0, 180.0),
    ) -> None:
        self.api_key = api_key or _required_env("OPENAI_API_KEY")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.transcription_model = os.getenv(
            "OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-transcribe-diarize"
        )
        self.generation_model = os.getenv("OPENAI_GENERATION_MODEL", "gpt-4.1-mini")

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _checked(self, response: requests.Response, operation: str) -> requests.Response:
        if response.ok:
            return response
        detail = response.text[:500].strip()
        raise VincoraServiceError(
            f"OpenAI respondió {response.status_code} al {operation}: {detail}"
        )

    def transcribe_bytes(
        self,
        content: bytes,
        *,
        filename: str = "audio.webm",
        content_type: str | None = None,
        language: str = "es",
        prompt: str | None = None,
    ) -> list[dict[str, Any]]:
        mime = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        data: dict[str, str] = {
            "model": self.transcription_model,
            "language": language,
            "response_format": "diarized_json",
            "chunking_strategy": "auto",
        }
        if prompt:
            data["prompt"] = prompt
        try:
            response = self.session.post(
                f"{self.base_url}/audio/transcriptions",
                headers=self.headers,
                data=data,
                files={"file": (filename, content, mime)},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise VincoraServiceError("No fue posible enviar el audio a OpenAI") from exc
        payload = self._checked(response, "transcribir audio").json()
        segments = payload.get("segments")
        if not isinstance(segments, list):
            text = str(payload.get("text", "")).strip()
            segments = [{"speaker": "No especificado", "start": 0, "end": 0, "text": text}]
        return [segment for segment in segments if str(segment.get("text", "")).strip()]

    def transcribe_file(
        self, path: str | Path, *, language: str = "es", prompt: str | None = None
    ) -> list[dict[str, Any]]:
        audio_path = Path(path)
        return self.transcribe_bytes(
            audio_path.read_bytes(),
            filename=audio_path.name,
            language=language,
            prompt=prompt,
        )

    def generate_minutes(
        self,
        segments: Sequence[Mapping[str, Any]],
        *,
        meeting_type: str = "general",
    ) -> dict[str, Any]:
        transcript = [
            {
                "segmento_id": str(segment["id"]),
                "hablante": str(segment.get("hablante", "No especificado")),
                "inicio_segundos": float(segment.get("inicio_segundos", 0)),
                "fin_segundos": float(segment.get("fin_segundos", 0)),
                "texto": str(segment["texto"]),
            }
            for segment in segments
        ]
        instructions = (
            "Convierte la transcripción de una reunión en un acta verificable. "
            "No infieras ni completes datos ausentes. Usa 'No especificado' para "
            "responsable o fecha si no aparecen literalmente. Cada acuerdo, tarea y "
            "decisión debe tener al menos una cita textual exacta y el segmento_id del "
            "que procede. No uses conocimiento externo."
        )
        body = {
            "model": self.generation_model,
            "instructions": instructions,
            "input": json.dumps(
                {"tipo_reunion": meeting_type, "segmentos": transcript},
                ensure_ascii=False,
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "acta_vincora",
                    "strict": True,
                    "schema": MINUTES_SCHEMA,
                }
            },
        }
        try:
            response = self.session.post(
                f"{self.base_url}/responses",
                headers=self.headers | {"Content-Type": "application/json"},
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise VincoraServiceError("No fue posible generar el acta con OpenAI") from exc
        payload = self._checked(response, "generar el acta").json()
        text = payload.get("output_text") or self._find_output_text(payload)
        if not text:
            raise VincoraServiceError("OpenAI no devolvió el JSON del acta")
        try:
            result = json.loads(text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise VincoraServiceError("OpenAI devolvió un acta que no es JSON válido") from exc
        return validate_minutes(result, segments)

    def answer_assistant(self, messages: Sequence[Mapping[str, str]], *, language: str = "es") -> str:
        """Responde al asistente general sin exponer la clave al frontend."""
        clean = [
            {"role": str(item.get("role") or "user"), "content": str(item.get("content") or "")[:6000]}
            for item in messages[-12:]
            if str(item.get("content") or "").strip()
        ]
        body = {
            "model": self.generation_model,
            "instructions": (
                "Eres el asistente de VINCORA Meet. Ayuda a redactar, organizar reuniones, "
                "tareas y resúmenes. No afirmes haber consultado reuniones o usuarios si esa "
                "información no está en la conversación. Responde de forma breve en "
                + ("inglés." if language == "en" else "español.")
            ),
            "input": clean,
        }
        try:
            response = self.session.post(
                f"{self.base_url}/responses",
                headers=self.headers | {"Content-Type": "application/json"},
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise VincoraServiceError("No fue posible consultar el asistente") from exc
        payload = self._checked(response, "responder con el asistente").json()
        text = payload.get("output_text") or self._find_output_text(payload)
        if not text:
            raise VincoraServiceError("OpenAI no devolvió una respuesta")
        return str(text).strip()

    @staticmethod
    def _find_output_text(payload: Mapping[str, Any]) -> str:
        for output in payload.get("output", []):
            for content in output.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    return str(content["text"])
        return ""


def _normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def validate_minutes(
    minutes: Mapping[str, Any], segments: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Rechaza afirmaciones cuya cita no exista literalmente en el segmento."""

    required = {"resumen", "temas", "acuerdos", "tareas", "decisiones"}
    missing = required.difference(minutes)
    if missing:
        raise EvidenceValidationError(f"Faltan campos del acta: {', '.join(sorted(missing))}")
    source_by_id = {str(segment["id"]): segment for segment in segments}
    validated = json.loads(json.dumps(minutes, ensure_ascii=False))
    for category in ("temas", "acuerdos", "tareas", "decisiones"):
        items = validated.get(category)
        if not isinstance(items, list):
            raise EvidenceValidationError(f"{category} debe ser una lista")
        for item in items:
            evidence_items = item.get("evidencias") if isinstance(item, dict) else None
            if not isinstance(evidence_items, list) or not evidence_items:
                raise EvidenceValidationError(f"Un elemento de {category} no tiene evidencia")
            canonical_evidence: list[dict[str, Any]] = []
            for evidence in evidence_items:
                segment_id = str(evidence.get("segmento_id", ""))
                quote_text = str(evidence.get("cita", "")).strip()
                source = source_by_id.get(segment_id)
                if source is None:
                    raise EvidenceValidationError(
                        f"La evidencia de {category} apunta a un segmento inexistente"
                    )
                if not quote_text or _normalized_text(quote_text) not in _normalized_text(
                    str(source.get("texto", ""))
                ):
                    raise EvidenceValidationError(
                        f"La cita de {category} no aparece en el segmento {segment_id}"
                    )
                canonical_evidence.append(
                    {
                        "segmento_id": segment_id,
                        "cita": quote_text,
                        "hablante": str(source.get("hablante", "No especificado")),
                        "inicio_segundos": float(source.get("inicio_segundos", 0)),
                        "fin_segundos": float(source.get("fin_segundos", 0)),
                    }
                )
            if category in {"acuerdos", "tareas"}:
                context = " ".join(
                    f"{evidence['cita']} {evidence['hablante']}"
                    for evidence in canonical_evidence
                )
                normalized_context = _normalized_text(context)
                for field in ("responsable", "fecha_limite"):
                    value = str(item.get(field, "")).strip()
                    if not value:
                        raise EvidenceValidationError(
                            f"{field} no puede quedar vacío; use 'No especificado'"
                        )
                    if (
                        _normalized_text(value) != "no especificado"
                        and _normalized_text(value) not in normalized_context
                    ):
                        raise EvidenceValidationError(
                            f"{field} no está respaldado por la evidencia"
                        )
            item["evidencias"] = canonical_evidence
    return validated


@dataclass(frozen=True)
class AudioSource:
    """Audio local o almacenado en el bucket configurado de Supabase."""

    source: str | Path
    speaker_hint: str | None = None
    offset_seconds: float = 0.0
    stored: bool = False


class ProcessingService:
    """Orquesta transcripción, persistencia y generación del acta verificable."""

    def __init__(
        self,
        supabase: SupabaseREST | None = None,
        openai: OpenAIREST | None = None,
        *,
        processing_table: str = "procesamientos_reunion",
        segments_table: str = "segmentos_reunion",
    ) -> None:
        self.supabase = supabase or SupabaseREST()
        self.openai = openai or OpenAIREST()
        self.processing_table = processing_table
        self.segments_table = segments_table

    def _state(
        self,
        meeting_id: str,
        state: str,
        progress: int,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        self.supabase.upsert(
            self.processing_table,
            {
                "reunion_id": meeting_id,
                "estado": state,
                "progreso": max(0, min(100, int(progress))),
                "detalle": dict(detail or {}),
                "actualizado_en": _utc_now(),
            },
            on_conflict="reunion_id",
        )

    def _read_audio(self, source: AudioSource) -> tuple[bytes, str]:
        if source.stored:
            object_path = str(source.source)
            return self.supabase.download_bytes(object_path), Path(object_path).name
        path = Path(source.source)
        return path.read_bytes(), path.name

    def run(
        self,
        meeting_id: str,
        audio_sources: Iterable[AudioSource | str | Path],
        *,
        meeting_type: str = "general",
        language: str = "es",
    ) -> dict[str, Any]:
        sources = [
            source if isinstance(source, AudioSource) else AudioSource(source)
            for source in audio_sources
        ]
        if not sources:
            raise ValueError("Se requiere al menos un audio para procesar la reunión")
        segments: list[dict[str, Any]] = []
        try:
            self._state(meeting_id, "transcribiendo", 5, {"audios": len(sources)})
            for index, source in enumerate(sources, start=1):
                content, filename = self._read_audio(source)
                raw_segments = self.openai.transcribe_bytes(
                    content, filename=filename, language=language
                )
                for raw in raw_segments:
                    speaker = str(raw.get("speaker") or source.speaker_hint or "No especificado")
                    text = str(raw.get("text", "")).strip()
                    if not text:
                        continue
                    segments.append(
                        {
                            "id": str(uuid.uuid4()),
                            "reunion_id": meeting_id,
                            "hablante": speaker,
                            "texto": text,
                            "inicio_segundos": float(raw.get("start", 0))
                            + source.offset_seconds,
                            "fin_segundos": float(raw.get("end", raw.get("start", 0)))
                            + source.offset_seconds,
                            "origen": str(source.source),
                            "creado_en": _utc_now(),
                        }
                    )
                progress = 5 + round(45 * index / len(sources))
                self._state(
                    meeting_id,
                    "transcribiendo",
                    progress,
                    {"audio_actual": index, "audios": len(sources)},
                )
            if not segments:
                raise VincoraServiceError("La transcripción no produjo segmentos con texto")
            self.supabase.upsert(self.segments_table, segments, on_conflict="id")
            self._state(
                meeting_id,
                "analizando",
                70,
                {"segmentos": len(segments)},
            )
            minutes = self.openai.generate_minutes(segments, meeting_type=meeting_type)
            report_rows = self.supabase.upsert(
                "informes_reunion",
                {
                    "reunion_id": meeting_id,
                    "estado": "borrador",
                    "resumen": minutes["resumen"],
                    "contenido": minutes,
                    "modelo": self.openai.generation_model,
                    "actualizado_en": _utc_now(),
                },
                on_conflict="reunion_id",
            )
            if not report_rows:
                raise VincoraServiceError("No se pudo guardar el informe generado")
            report_id = str(report_rows[0]["id"])
            tables = {
                "temas": "temas_tratados",
                "acuerdos": "acuerdos",
                "tareas": "tareas_detectadas",
                "decisiones": "decisiones",
            }
            for category, table in tables.items():
                self.supabase.delete(table, filters={"informe_id": report_id})
                rows = []
                for item in minutes[category]:
                    row = {
                        "informe_id": report_id,
                        "descripcion": item.get("descripcion") or item.get("titulo"),
                        "evidencias": item["evidencias"],
                        "estado": "detectado",
                    }
                    if category in {"acuerdos", "tareas"}:
                        row["responsable"] = item["responsable"]
                        row["fecha_limite"] = item["fecha_limite"]
                    rows.append(row)
                if rows:
                    self.supabase.insert(table, rows)
            result = {
                "reunion_id": meeting_id,
                "estado": "completado",
                "segmentos": segments,
                "acta": minutes,
                "informe_id": report_id,
            }
            self._state(
                meeting_id,
                "completado",
                100,
                {
                    "segmentos": len(segments),
                    "acuerdos": len(minutes["acuerdos"]),
                    "tareas": len(minutes["tareas"]),
                    "decisiones": len(minutes["decisiones"]),
                    "acta": minutes,
                },
            )
            return result
        except Exception as exc:
            try:
                self._state(
                    meeting_id,
                    "error",
                    0,
                    {"mensaje": str(exc)[:500]},
                )
            except Exception:
                pass
            raise
