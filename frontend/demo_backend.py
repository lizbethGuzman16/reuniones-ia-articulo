"""Backend local para demostraciones y capturas.

Los nombres de usuarios y descripciones de tareas provienen de los scripts SQL
incluidos en el proyecto original. Los UUID, fechas y asignaciones se generan de
forma determinista para poder ejecutar la interfaz sin conexión a Supabase.
"""
from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEMO_ADMIN_ID = "00000000-0000-4000-8000-000000000001"
DEMO_ADMIN_EMAIL = "juanaureliodelacruzgamarra@gmail.com"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _fixed_uuid(index: int) -> str:
    return f"00000000-0000-4000-8000-{index:012d}"


def _load_users_from_original_sql() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    sql_path = root / "docs" / "querys para supabase" / "query3.txt"
    text = sql_path.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(
        r"\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\)"
    )
    now = datetime(2026, 7, 1, 14, 0, tzinfo=timezone.utc)
    users: list[dict[str, Any]] = []
    for i, match in enumerate(pattern.finditer(text), start=10):
        nombre, correo, password_hash, nivel, estado = match.groups()
        users.append(
            {
                "id": _fixed_uuid(i),
                "nombre": nombre,
                "correo": correo,
                "password_hash": password_hash,
                "nivel_suscripcion": nivel,
                "estado_suscripcion": estado,
                "fecha_creacion": _iso(now + timedelta(days=i - 10)),
            }
        )
    return users


def _load_task_descriptions() -> list[str]:
    root = Path(__file__).resolve().parents[1]
    sql_path = root / "docs" / "querys para supabase" / "insert_sample_tasks.sql"
    text = sql_path.read_text(encoding="utf-8", errors="ignore")
    block = text.split("v_descripciones text[] := ARRAY[", 1)[1].split("];", 1)[0]
    return re.findall(r"'([^']+)'", block)


def build_demo_data() -> dict[str, list[dict[str, Any]]]:
    users = _load_users_from_original_sql()
    now = datetime(2026, 7, 12, 15, 0, tzinfo=timezone.utc)

    # Temas derivados de ejemplos y textos ya presentes en el proyecto original.
    meetings = [
        {
            "id": _fixed_uuid(101),
            "creador_id": users[0]["id"],
            "tema": "Ventas Q4",
            "fecha_inicio": _iso(now + timedelta(days=1, hours=1)),
            "duracion_minutos": 60,
            "proveedor": "zoom",
            "id_externo": "demo-zoom-001",
            "join_url": "https://zoom.example/demo-001",
            "start_url": "https://zoom.example/start-demo-001",
            "estado": "programada",
            "tipo": "virtual",
            "direccion": None,
            "fecha_creacion": _iso(now - timedelta(days=3)),
        },
        {
            "id": _fixed_uuid(102),
            "creador_id": users[1]["id"],
            "tema": "Capacitación para el equipo",
            "fecha_inicio": _iso(now - timedelta(days=5)),
            "duracion_minutos": 45,
            "proveedor": "presencial",
            "id_externo": None,
            "join_url": None,
            "start_url": None,
            "estado": "completada",
            "tipo": "presencial",
            "direccion": "Sala de reuniones",
            "fecha_creacion": _iso(now - timedelta(days=12)),
        },
        {
            "id": _fixed_uuid(103),
            "creador_id": users[2]["id"],
            "tema": "Seguimiento con stakeholders",
            "fecha_inicio": _iso(now + timedelta(days=4, hours=2)),
            "duracion_minutos": 50,
            "proveedor": "zoom",
            "id_externo": "demo-zoom-003",
            "join_url": "https://zoom.example/demo-003",
            "start_url": "https://zoom.example/start-demo-003",
            "estado": "programada",
            "tipo": "mixta",
            "direccion": "Sala A",
            "fecha_creacion": _iso(now - timedelta(days=1)),
        },
    ]

    participants: list[dict[str, Any]] = []
    participant_states = ["aceptado", "enviado", "aceptado", "rechazado", "enviado"]
    for i, user in enumerate(users, start=1):
        participants.append(
            {
                "id": _fixed_uuid(200 + i),
                "reunion_id": meetings[0]["id"],
                "usuario_id": user["id"],
                "correo": user["correo"],
                "rol": "organizador" if i == 1 else "participante",
                "estado_invitacion": participant_states[i - 1],
                "fecha_creacion": _iso(now - timedelta(days=2, hours=i)),
            }
        )

    descriptions = _load_task_descriptions()
    statuses = ["pendiente", "en_progreso", "completada"]
    tasks: list[dict[str, Any]] = []
    for i, description in enumerate(descriptions[:30], start=1):
        meeting = meetings[(i - 1) % len(meetings)]
        assigned = users[(i - 1) % len(users)]["correo"] if i % 5 else None
        due = now + timedelta(days=((i * 7) % 70) - 15)
        created = now - timedelta(days=(i * 3) % 60)
        tasks.append(
            {
                "id": _fixed_uuid(300 + i),
                "reunion_id": meeting["id"],
                "descripcion": description,
                "asignado_a_correo": assigned,
                "estado": statuses[(i - 1) % len(statuses)],
                "fecha_vencimiento": _iso(due),
                "fecha_creacion": _iso(created),
            }
        )

    summaries = [
        {
            "id": _fixed_uuid(501),
            "reunion_id": meetings[1]["id"],
            "resumen": (
                "Resumen de demostración local generado para comprobar la pantalla. "
                "No corresponde a una transcripción de producción."
            ),
            "fecha_creacion": _iso(now - timedelta(days=4, hours=2)),
        }
    ]

    # Métricas de ejecución local, claramente separadas de datos productivos.
    metrics: list[dict[str, Any]] = []
    endpoint_cycle = ["crear_reunion_chat", "resumen_virtual", "resumen_presencial"]
    for i in range(18):
        metrics.append(
            {
                "id": _fixed_uuid(600 + i),
                "endpoint": endpoint_cycle[i % len(endpoint_cycle)],
                "tiempo_respuesta": round(0.65 + (i % 7) * 0.31, 2),
                "estado": "error" if i in {5, 14} else "éxito",
                "fecha": _iso(now - timedelta(days=i // 3, hours=i % 5)),
                "codigo_estado": 500 if i in {5, 14} else 200,
                "reunion_id": meetings[i % len(meetings)]["id"],
                "tamano_respuesta": 820 + i * 17,
                "detalles": "Ejecución local de demostración",
            }
        )

    return {
        "usuarios": users,
        "reuniones": meetings,
        "participantes": participants,
        "tareas": tasks,
        "resumenes": summaries,
        "metricas_n8n": metrics,
    }


class DemoResponse:
    def __init__(self, payload: Any = None, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload, ensure_ascii=False, default=str)
        self.content = self.text.encode("utf-8")

    def json(self) -> Any:
        return deepcopy(self._payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"Respuesta local de demostración: HTTP {self.status_code}")


class DemoRequestsAdapter:
    def __init__(self, original_requests: Any):
        self._original = original_requests
        self._data = build_demo_data()

    @staticmethod
    def _table_from_url(url: str) -> str | None:
        if "/rest/v1/" not in url:
            return None
        return url.split("/rest/v1/", 1)[1].split("?", 1)[0].strip("/")

    @staticmethod
    def _decode_body(data: Any = None, json_body: Any = None) -> Any:
        if json_body is not None:
            return deepcopy(json_body)
        if data is None:
            return None
        if isinstance(data, (dict, list)):
            return deepcopy(data)
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)

    @staticmethod
    def _apply_filters(rows: list[dict[str, Any]], params: dict[str, Any] | None) -> list[dict[str, Any]]:
        params = params or {}
        result = [deepcopy(r) for r in rows]
        reserved = {"select", "order", "limit", "offset", "or"}
        for key, expression in params.items():
            if key in reserved or expression is None:
                continue
            expression = str(expression)
            if expression.startswith("eq."):
                value = expression[3:]
                result = [r for r in result if str(r.get(key)) == value]
            elif expression.startswith("in.(") and expression.endswith(")"):
                values = {v.strip().strip('"') for v in expression[4:-1].split(",")}
                result = [r for r in result if str(r.get(key)) in values]
            elif expression.startswith("ilike."):
                needle = expression[6:].replace("%", "").lower()
                result = [r for r in result if needle in str(r.get(key, "")).lower()]

        or_expr = params.get("or")
        if or_expr:
            clauses = str(or_expr).strip("() ").split(",")
            matched = []
            for row in result:
                for clause in clauses:
                    parts = clause.split(".", 2)
                    if len(parts) == 3 and parts[1] == "ilike":
                        field, _, value = parts
                        needle = value.replace("%", "").lower()
                        if needle in str(row.get(field, "")).lower():
                            matched.append(row)
                            break
            result = matched

        order = params.get("order")
        if order:
            field, *direction = str(order).split(".")
            reverse = direction and direction[0].lower() == "desc"
            result.sort(key=lambda r: str(r.get(field, "")), reverse=reverse)

        offset = int(params.get("offset", 0) or 0)
        limit = params.get("limit")
        if limit is not None:
            result = result[offset : offset + int(limit)]
        elif offset:
            result = result[offset:]
        return result

    def get(self, url: str, **kwargs: Any) -> DemoResponse:
        table = self._table_from_url(url)
        if table is None:
            return self._original.get(url, **kwargs)
        if table not in self._data:
            return DemoResponse({"message": f"Tabla no disponible: {table}"}, 404)
        rows = self._apply_filters(self._data[table], kwargs.get("params"))
        return DemoResponse(rows, 200)

    def post(self, url: str, **kwargs: Any) -> DemoResponse:
        table = self._table_from_url(url)
        if table is not None:
            body = self._decode_body(kwargs.get("data"), kwargs.get("json"))
            rows = body if isinstance(body, list) else [body]
            inserted = []
            for raw in rows:
                row = dict(raw or {})
                row.setdefault("id", str(uuid.uuid4()))
                row.setdefault("fecha_creacion", _iso(datetime.now(timezone.utc)))
                self._data.setdefault(table, []).append(row)
                inserted.append(deepcopy(row))
            return DemoResponse(inserted, 201)

        # Simulación de webhook n8n para la demostración local.
        if str(url).startswith("demo://create-meeting"):
            payload = kwargs.get("json") or {}
            message = str(payload.get("mensaje", ""))
            meeting = deepcopy(self._data["reuniones"][0])
            meeting["id"] = str(uuid.uuid4())
            meeting["tema"] = "Ventas Q4" if "ventas" in message.lower() else "Reunión creada en modo demostración"
            meeting["fecha_inicio"] = _iso(datetime.now(timezone.utc) + timedelta(days=1))
            self._data["reuniones"].append(meeting)
            return DemoResponse(
                {
                    "meeting": {
                        "tema": meeting["tema"],
                        "fecha": meeting["fecha_inicio"],
                        "tipo": meeting["tipo"],
                        "join_url": meeting["join_url"],
                        "destinatarios": [p["correo"] for p in self._data["participantes"][:2]],
                    }
                },
                200,
            )
        if str(url).startswith("demo://summary"):
            return DemoResponse({"resumen": "Resumen local de demostración"}, 200)
        return self._original.post(url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> DemoResponse:
        table = self._table_from_url(url)
        if table is None:
            return self._original.patch(url, **kwargs)
        updates = self._decode_body(kwargs.get("data"), kwargs.get("json")) or {}
        matches = self._apply_filters(self._data.get(table, []), kwargs.get("params"))
        match_ids = {str(r.get("id")) for r in matches}
        updated = []
        for row in self._data.get(table, []):
            if str(row.get("id")) in match_ids:
                row.update(updates)
                updated.append(deepcopy(row))
        return DemoResponse(updated, 200)

    def delete(self, url: str, **kwargs: Any) -> DemoResponse:
        table = self._table_from_url(url)
        if table is None:
            return self._original.delete(url, **kwargs)
        matches = self._apply_filters(self._data.get(table, []), kwargs.get("params"))
        match_ids = {str(r.get("id")) for r in matches}
        self._data[table] = [r for r in self._data.get(table, []) if str(r.get("id")) not in match_ids]
        return DemoResponse(matches, 200)


def install_demo_backend(requests_module: Any) -> DemoRequestsAdapter:
    # Devuelve un adaptador local sin modificar el módulo global requests.
    # Esto evita interferir con Streamlit durante cada rerun.
    return DemoRequestsAdapter(requests_module)
