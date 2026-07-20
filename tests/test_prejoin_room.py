from frontend.prejoin_room import build_prejoin_html


def test_prejoin_join_uses_iframe_safe_navigation() -> None:
    html = build_prejoin_html(
        logo="data:image/svg+xml;base64,AA==",
        meeting={"id": "meeting-1", "tema": "Revisión"},
        participant_name="Ana",
        participant_count=1,
    )

    assert "function navigateApp(query)" in html
    assert "window.parent.location.href" not in html
    assert "window.parent.history" not in html
    assert "navigateApp('?videollamada=" in html
    assert "window.open(base.toString(),'_blank','noopener')" in html
