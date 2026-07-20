from __future__ import annotations

import pytest

from backend.vincora_services import (
    EvidenceValidationError,
    OpenAIREST,
    SupabaseREST,
    validate_minutes,
)


SEGMENTS = [
    {
        "id": "seg-1",
        "hablante": "Ana García",
        "texto": "Yo terminaré el prototipo el viernes.",
        "inicio_segundos": 12.5,
        "fin_segundos": 15.0,
    }
]


def _minutes() -> dict:
    evidence = [{"segmento_id": "seg-1", "cita": "terminaré el prototipo el viernes"}]
    return {
        "resumen": "Ana asumió una entrega.",
        "temas": [
            {
                "titulo": "Prototipo",
                "descripcion": "Entrega del prototipo.",
                "evidencias": evidence,
            }
        ],
        "acuerdos": [
            {
                "descripcion": "Terminar el prototipo.",
                "responsable": "Ana García",
                "fecha_limite": "viernes",
                "evidencias": evidence,
            }
        ],
        "tareas": [],
        "decisiones": [],
    }


def test_minutes_keep_canonical_evidence_from_the_transcript() -> None:
    result = validate_minutes(_minutes(), SEGMENTS)
    evidence = result["acuerdos"][0]["evidencias"][0]
    assert evidence["hablante"] == "Ana García"
    assert evidence["inicio_segundos"] == 12.5
    assert evidence["fin_segundos"] == 15.0


def test_minutes_reject_a_quote_that_is_not_in_the_transcript() -> None:
    minutes = _minutes()
    minutes["acuerdos"][0]["evidencias"][0]["cita"] = "Se aprobó el presupuesto"
    with pytest.raises(EvidenceValidationError, match="no aparece"):
        validate_minutes(minutes, SEGMENTS)


def test_minutes_reject_an_ungrounded_responsible_person() -> None:
    minutes = _minutes()
    minutes["acuerdos"][0]["responsable"] = "Luis Torres"
    with pytest.raises(EvidenceValidationError, match="no está respaldado"):
        validate_minutes(minutes, SEGMENTS)


class _StorageResponse:
    ok = True
    status_code = 200
    content = b"audio"
    headers = {"content-type": "audio/ogg"}
    text = ""


class _StorageSession:
    def __init__(self) -> None:
        self.url = ""

    def request(self, method: str, url: str, **_: object) -> _StorageResponse:
        assert method == "GET"
        self.url = url
        return _StorageResponse()


def test_private_recording_download_uses_authenticated_storage_route() -> None:
    session = _StorageSession()
    client = SupabaseREST(
        "https://project.supabase.co",
        "service-role-test",
        "grabaciones-reuniones",
        session=session,
    )
    assert client.download_bytes("reuniones/1/audio.ogg") == b"audio"
    assert "/storage/v1/object/authenticated/grabaciones-reuniones/" in session.url


class _OpenAIResponse:
    ok = True
    status_code = 200
    text = ""

    def json(self) -> dict:
        return {"output_text": "Respuesta comprobada"}


class _OpenAISession:
    def __init__(self) -> None:
        self.body = None

    def post(self, url: str, **kwargs: object) -> _OpenAIResponse:
        assert url.endswith("/responses")
        self.body = kwargs.get("json")
        return _OpenAIResponse()


def test_global_assistant_uses_responses_api_and_requested_language() -> None:
    session = _OpenAISession()
    client = OpenAIREST("test-key", session=session)
    answer = client.answer_assistant([{"role": "user", "content": "Hello"}], language="en")
    assert answer == "Respuesta comprobada"
    assert session.body["input"][-1]["content"] == "Hello"
    assert "inglés" in session.body["instructions"]
