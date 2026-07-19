"""Genera capturas reales del frontend Streamlit ejecutado en modo demo."""

import re
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


BASE_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = Path("capturas-reales")

PANTALLAS = [
    ("Inicio", "Buenos días", "01-inicio.png"),
    ("Chat", "Crear reunión por chat", "02-chat.png"),
    ("Usuarios", "Usuarios y permisos", "03-usuarios.png"),
    ("Reuniones", "Reuniones", "04-reuniones.png"),
    ("Tareas", "Gestión de Tareas", "05-tareas.png"),
    ("Resumen de reuniones", "Reunión finalizada", "06-resumenes.png"),
    ("Participantes", "Participantes de Reuniones", "07-participantes.png"),
    ("Métricas", "Métricas y Estadísticas", "08-metricas.png"),
]


def abrir_pantalla(page: Page, opcion: str, titulo: str, archivo: str) -> None:
    etiqueta = page.locator('label[data-testid="stRadioOption"]').filter(
        has_text=re.compile(rf"^{re.escape(opcion)}$")
    )
    etiqueta.wait_for(state="visible", timeout=30_000)
    etiqueta.click()

    heading = (
        page.get_by_role("heading", name=re.compile(r"^Buenos días"))
        if opcion == "Inicio"
        else page.get_by_role("heading", name=titulo, exact=True)
    )
    heading.wait_for(state="visible", timeout=45_000)
    page.wait_for_timeout(1_200)
    page.evaluate("window.scrollTo(0, 0)")
    main = page.locator('[data-testid="stMain"]')
    if main.count():
        main.evaluate("element => element.scrollTo(0, 0)")
    page.wait_for_timeout(300)

    if opcion == "Usuarios":
        # El signo "+" se dibuja con CSS y algunos navegadores lo incorporan
        # al nombre accesible del botón. Localizar por el texto estable evita
        # que la captura dependa de esa diferencia del motor de accesibilidad.
        page.get_by_role("button", name=re.compile(r"Invitar usuario$")).click()
        page.get_by_role(
            "heading", name="Invitar nuevo usuario", exact=True
        ).wait_for(state="visible", timeout=30_000)
        page.wait_for_timeout(300)
    elif opcion == "Reuniones":
        page.get_by_role("button", name=re.compile(r"Programar reunión$")).click()
        page.get_by_role(
            "heading", name="Programar nueva reunión", exact=True
        ).wait_for(state="visible", timeout=30_000)
        page.wait_for_timeout(300)

    page.screenshot(
        path=str(OUTPUT_DIR / archivo),
        full_page=False,
        animations="disabled",
    )

    if opcion == "Inicio":
        expect(page.get_by_text("Próximas reuniones", exact=True)).to_be_visible()
        expect(page.get_by_text("Resumen de esta semana", exact=True)).to_be_visible()
        expect(page.get_by_text("Informes recientes", exact=True)).to_be_visible()
        expect(page.get_by_text("Mis tareas", exact=True)).to_be_visible()
        page.locator(".st-key-home_action_schedule button").click()
        page.get_by_role("heading", name="Crear reunión por chat", exact=True).wait_for(
            state="visible", timeout=30_000
        )
        expect(page.locator('[data-testid="stChatInput"] textarea')).to_have_value(
            "Programa una reunión.", timeout=15_000
        )
    elif opcion == "Chat":
        page.get_by_role("button", name="Programar reunión para mañana", exact=True).click()
        entrada = page.locator('[data-testid="stChatInput"] textarea')
        expect(entrada).to_have_value(re.compile(r"Programa una reunión mañana"), timeout=15_000)
        page.get_by_role("button", name="Limpiar", exact=True).click()
        expect(entrada).to_have_value("", timeout=15_000)
    elif opcion == "Usuarios":
        expect(page.get_by_text("Permisos iniciales", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Enviar invitación", exact=True)).to_be_visible()
        page.keyboard.press("Escape")
    elif opcion == "Reuniones":
        expect(page.get_by_text("Asistente inteligente", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Programar reunión", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Bienvenido de nuevo", exact=True)).to_have_count(0)
        page.keyboard.press("Escape")
    elif opcion == "Resumen de reuniones":
        expect(page.get_by_text("Preparando tu informe inteligente", exact=True)).to_be_visible()
        expect(page.get_by_text("Grabación guardada", exact=True)).to_be_visible()
        expect(page.get_by_text("No disponible", exact=True).first).to_be_visible()
        expect(page.get_by_text("Ver transcripción preliminar", exact=True)).to_be_visible()


def capturar_login(page: Page) -> None:
    page.goto(f"{BASE_URL}?mostrar_login=1", wait_until="domcontentloaded", timeout=90_000)
    page.get_by_role(
        "heading", name="Bienvenido de nuevo", exact=True
    ).wait_for(state="visible", timeout=90_000)
    page.wait_for_timeout(1_200)
    page.screenshot(
        path=str(OUTPUT_DIR / "00-login.png"),
        full_page=False,
        animations="disabled",
    )


def capturar_sala_previa(page: Page) -> None:
    reunion_id = "00000000-0000-4000-8000-000000000101"
    page.goto(f"{BASE_URL}?sala_previa={reunion_id}", wait_until="domcontentloaded", timeout=90_000)
    frame = page.frame_locator('[data-testid="stIFrame"]')
    frame.get_by_role("heading", name="¿Preparado para unirte?", exact=True).wait_for(
        state="visible", timeout=90_000
    )
    frame.get_by_role("button", name="Permitir dispositivos", exact=True).click()
    frame.get_by_text("Grabación y transcripción con IA", exact=True).wait_for(
        state="visible", timeout=30_000
    )
    frame.get_by_label("Acepto la grabación y el procesamiento del audio.").check()
    expect(frame.get_by_role("button", name=re.compile(r"Unirse ahora"))).to_be_enabled()
    page.wait_for_timeout(1_000)
    page.screenshot(
        path=str(OUTPUT_DIR / "09-sala-previa.png"),
        full_page=False,
        animations="disabled",
    )


def capturar_videollamada(page: Page) -> None:
    reunion_id = "00000000-0000-4000-8000-000000000101"
    page.goto(f"{BASE_URL}?videollamada={reunion_id}", wait_until="domcontentloaded", timeout=90_000)
    frame = page.frame_locator('[data-testid="stIFrame"]')
    frame.get_by_text("VINCORA IA activa", exact=False).wait_for(state="visible", timeout=90_000)
    expect(frame.get_by_role("button", name=re.compile(r"Finalizar"))).to_be_visible()
    expect(frame.locator(".name").filter(has_text="Ana García")).to_be_visible()
    frame.get_by_role("button", name=re.compile(r"Finalizar")).click()
    frame.get_by_role("heading", name="¿Finalizar la reunión?", exact=True).wait_for(
        state="visible", timeout=30_000
    )
    expect(frame.get_by_role("button", name="Finalizar para todos", exact=True)).to_be_visible()
    page.wait_for_timeout(800)
    page.screenshot(
        path=str(OUTPUT_DIR / "10-videollamada-activa.png"),
        full_page=False,
        animations="disabled",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=1,
            color_scheme="light",
        )
        page = context.new_page()
        capturar_login(page)
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=90_000)
        page.get_by_role(
            "heading", name=re.compile(r"^Buenos días")
        ).wait_for(state="visible", timeout=90_000)

        for opcion, titulo, archivo in PANTALLAS:
            abrir_pantalla(page, opcion, titulo, archivo)

        capturar_sala_previa(page)
        capturar_videollamada(page)

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
