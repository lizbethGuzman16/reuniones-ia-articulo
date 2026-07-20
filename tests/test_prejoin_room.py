from frontend.prejoin_room import build_prejoin_html


def test_prejoin_join_uses_iframe_safe_navigation() -> None:
    html = build_prejoin_html(
        logo="data:image/svg+xml;base64,AA==",
        meeting={"id": "meeting-1", "tema": "Revisión"},
        participant_name="Ana",
        participant_count=1,
        session_token="signed-session",
    )

    assert "function navigateApp(query)" in html
    assert "window.parent.history" not in html
    assert "window.location.ancestorOrigins" in html
    assert "document.referrer||window.location.href" not in html
    assert "navigateApp('?videollamada=" in html
    assert "window.open(url,'_blank','noopener')" in html
    assert '"sessionToken": "signed-session"' in html
    assert "base.searchParams.set('session_token',cfg.sessionToken)" in html
