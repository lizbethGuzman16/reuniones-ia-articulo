"""Genera capturas reales del frontend Streamlit ejecutado en modo demo."""

from pathlib import Path

from playwright.sync_api import Page, sync_playwright


BASE_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = Path("capturas-reales")

PANTALLAS = [
    ("💬 Chat", "💬 Crear reunión por chat", "01-chat.png"),
    ("🧑‍💼 Usuarios", "👥 Gestión de Usuarios", "02-usuarios.png"),
    ("📅 Reuniones", "📅 Reuniones", "03-reuniones.png"),
    ("✅ Tareas", "📋 Gestión de Tareas", "04-tareas.png"),
    ("📝 Resumen de reuniones", "📝 Resumen de reuniones", "05-resumenes.png"),
    ("👥 Participantes", "👥 Participantes de Reuniones", "06-participantes.png"),
    ("📊 Métricas", "📊 Métricas y Estadísticas", "07-metricas.png"),
]


def abrir_pantalla(page: Page, opcion: str, titulo: str, archivo: str) -> None:
    etiqueta = page.locator('label[data-testid="stRadioOption"]').filter(
        has_text=opcion
    )
    etiqueta.wait_for(state="visible", timeout=30_000)
    etiqueta.click()

    heading = page.get_by_role("heading", name=titulo, exact=True)
    heading.wait_for(state="visible", timeout=45_000)
    page.wait_for_timeout(1_200)
    page.screenshot(
        path=str(OUTPUT_DIR / archivo),
        full_page=False,
        animations="disabled",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=1,
            color_scheme="dark",
        )
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=90_000)
        page.get_by_role(
            "heading", name="💬 Crear reunión por chat", exact=True
        ).wait_for(state="visible", timeout=90_000)

        for opcion, titulo, archivo in PANTALLAS:
            abrir_pantalla(page, opcion, titulo, archivo)

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
