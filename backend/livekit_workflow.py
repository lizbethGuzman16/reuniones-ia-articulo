from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from typing import Any

from livekit import api

from backend.vincora_services import SupabaseREST, VincoraServiceError, _utc_now


def room_name_for(meeting_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", meeting_id).strip("-")
    if not safe:
        raise VincoraServiceError("El identificador de reunión no es válido")
    return f"vincora-{safe}"[:128]


def meeting_id_from_room(room_name: str) -> str | None:
    return room_name[len("vincora-") :] if room_name.startswith("vincora-") else None


@dataclass(frozen=True, slots=True)
class LiveKitSettings:
    url: str
    api_key: str
    api_secret: str
    endpoint: str
    access_key: str
    secret: str
    region: str
    bucket: str

    @classmethod
    def from_env(cls) -> "LiveKitSettings":
        values = {
            "url": os.getenv("LIVEKIT_URL", "").strip(),
            "api_key": os.getenv("LIVEKIT_API_KEY", "").strip(),
            "api_secret": os.getenv("LIVEKIT_API_SECRET", "").strip(),
            "endpoint": os.getenv("SUPABASE_S3_ENDPOINT", "").strip(),
            "access_key": os.getenv("SUPABASE_S3_ACCESS_KEY_ID", "").strip(),
            "secret": os.getenv("SUPABASE_S3_SECRET_ACCESS_KEY", "").strip(),
            "region": os.getenv("SUPABASE_S3_REGION", "").strip(),
            "bucket": (
                os.getenv("SUPABASE_RECORDING_BUCKET", "").strip()
                or os.getenv("SUPABASE_S3_BUCKET", "").strip()
            ),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise VincoraServiceError(
                "Falta configuración LiveKit/S3: " + ", ".join(missing)
            )
        return cls(**values)

    def storage(self) -> Any:
        return api.S3Upload(
            access_key=self.access_key,
            secret=self.secret,
            region=self.region,
            endpoint=self.endpoint,
            bucket=self.bucket,
            force_path_style=True,
        )


def components_ready() -> dict[str, bool]:
    try:
        LiveKitSettings.from_env()
        return {"livekit": True, "storage": True}
    except VincoraServiceError:
        return {
            "livekit": all(
                os.getenv(name, "").strip()
                for name in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
            ),
            "storage": False,
        }


def _existing(
    store: SupabaseREST,
    meeting_id: str,
    kind: str,
    identity: str | None = None,
) -> dict[str, Any] | None:
    filters: dict[str, Any] = {"reunion_id": meeting_id, "tipo": kind}
    if identity is not None:
        filters["participante_identity"] = identity
    rows = store.select("grabaciones", filters=filters, order="creado_en.desc", limit=1)
    if rows and rows[0].get("estado") not in {"error", "abortada"}:
        return rows[0]
    return None


async def start_room_recording(meeting_id: str) -> dict[str, Any]:
    settings = LiveKitSettings.from_env()
    store = SupabaseREST(bucket=settings.bucket)
    current = _existing(store, meeting_id, "reunion")
    if current:
        return current
    room_name = room_name_for(meeting_id)
    path = f"reuniones/{meeting_id}/reunion-{uuid.uuid4().hex}.mp4"
    livekit = api.LiveKitAPI(settings.url, settings.api_key, settings.api_secret)
    try:
        await livekit.room.create_room(api.CreateRoomRequest(name=room_name))
        info = await livekit.egress.start_room_composite_egress(
            api.RoomCompositeEgressRequest(
                room_name=room_name,
                layout="grid",
                file_outputs=[
                    api.EncodedFileOutput(
                        file_type=api.EncodedFileType.MP4,
                        filepath=path,
                        s3=settings.storage(),
                    )
                ],
            )
        )
    finally:
        await livekit.aclose()
    rows = store.insert(
        "grabaciones",
        {
            "reunion_id": meeting_id,
            "egress_id": info.egress_id,
            "tipo": "reunion",
            "ruta_objeto": path,
            "estado": "iniciada",
            "actualizado_en": _utc_now(),
        },
    )
    return rows[0] if rows else {"egress_id": info.egress_id, "ruta_objeto": path}


async def start_participant_recording(
    meeting_id: str, identity: str, participant_name: str
) -> dict[str, Any]:
    settings = LiveKitSettings.from_env()
    store = SupabaseREST(bucket=settings.bucket)
    current = _existing(store, meeting_id, "participante", identity)
    if current:
        return current
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", identity)[:80]
    path = f"reuniones/{meeting_id}/participantes/{safe}-{uuid.uuid4().hex}.ogg"
    livekit = api.LiveKitAPI(settings.url, settings.api_key, settings.api_secret)
    try:
        info = await livekit.egress.start_participant_egress(
            api.ParticipantEgressRequest(
                room_name=room_name_for(meeting_id),
                identity=identity,
                file_outputs=[
                    api.EncodedFileOutput(
                        file_type=api.EncodedFileType.OGG,
                        filepath=path,
                        s3=settings.storage(),
                    )
                ],
            )
        )
    finally:
        await livekit.aclose()
    rows = store.insert(
        "grabaciones",
        {
            "reunion_id": meeting_id,
            "egress_id": info.egress_id,
            "tipo": "participante",
            "participante_identity": identity,
            "participante_nombre": participant_name,
            "ruta_objeto": path,
            "estado": "iniciada",
            "actualizado_en": _utc_now(),
        },
    )
    return rows[0] if rows else {"egress_id": info.egress_id, "ruta_objeto": path}


def finish_egress(info: Any) -> dict[str, Any] | None:
    egress_id = str(getattr(info, "egress_id", "") or "")
    if not egress_id:
        return None
    status = getattr(info, "status", None)
    # Valores protobuf de LiveKit EgressStatus 1.x:
    # 3=EGRESS_COMPLETE, 5=EGRESS_ABORTED; los demás no son éxito.
    if int(status) == 3:
        state = "completada"
    elif int(status) == 5:
        state = "abortada"
    else:
        state = "error"
    store = SupabaseREST()
    rows = store.update(
        "grabaciones",
        {
            "estado": state,
            "error": str(getattr(info, "error", "") or "") or None,
            "actualizado_en": _utc_now(),
        },
        filters={"egress_id": egress_id},
    )
    return {
        "egress_id": egress_id,
        "reunion_id": meeting_id_from_room(
            str(getattr(info, "room_name", "") or "")
        ),
        "estado": state,
        "registro": rows[0] if rows else None,
    }
