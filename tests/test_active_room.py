from frontend.active_room import build_active_room_html


def _render(recording_state: str) -> str:
    return build_active_room_html(
        logo="data:image/svg+xml;base64,AA==",
        meeting={"id": "meeting-1", "tema": "Revisión"},
        connection={
            "participant_token": "token",
            "server_url": "wss://example.livekit.cloud",
            "recording_state": recording_state,
        },
        user={"nombre": "Ana", "is_organizer": True},
    )


def test_active_room_receives_real_server_recording_state() -> None:
    html = _render("iniciada")
    assert '"recordingState": "iniciada"' in html
    assert "recordingActive" in html
    assert 'id="end-recording"' in html


def test_active_room_does_not_claim_recording_when_egress_is_unavailable() -> None:
    html = _render("not_configured")
    assert '"recordingState": "not_configured"' in html
    assert "Grabación no configurada" in html


def test_active_room_uses_iframe_safe_navigation() -> None:
    html = _render("iniciada")
    assert "function navigateApp(query)" in html
    assert "window.parent.location.href" not in html
    assert "window.parent.history" not in html
    assert "navigateApp('?finalizar_reunion=" in html
