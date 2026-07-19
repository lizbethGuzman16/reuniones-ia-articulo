import os, json, requests
import base64
import calendar
import secrets
import time
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO
from html import escape
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from passlib.hash import bcrypt
import streamlit as st
from dotenv import load_dotenv
import altair as alt
try:
    from frontend.prejoin_room import build_prejoin_html
except ModuleNotFoundError:
    from prejoin_room import build_prejoin_html

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
N8N_URL = os.getenv("N8N_CREATE_MEETING_WEBHOOK_URL")
N8N_RESUMEN_VIRTUAL_URL = os.getenv("N8N_RESUMEN_VIRTUAL_WEBHOOK_URL")
N8N_RESUMEN_PRESENCIAL_URL = os.getenv("N8N_RESUMEN_PRESENCIAL_WEBHOOK_URL")
DEMO_MODE = os.getenv("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "si", "sí"}
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000").rstrip("/")
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "").split(",")
    if email.strip()
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = PROJECT_ROOT / "frontend" / "assets" / "icons"
BRAND_DIR = PROJECT_ROOT / "frontend" / "assets" / "branding"
LOGO_PATH = BRAND_DIR / "vincora-logo.png"
LOGIN_REFERENCE_PATH = BRAND_DIR / "vincora-login-reference.jpg"
GOOGLE_ICON_PATH = BRAND_DIR / "google-g.svg"

ICON_FILES = {
    "inicio": "home.svg",
    "chat": "message-circle.svg",
    "chat_sonrisa": "chat-smile.svg",
    "usuarios": "users-group.svg",
    "usuario": "users.svg",
    "usuario_configuracion": "user-cog.svg",
    "usuario_suspendido": "user-x.svg",
    "administracion": "user-plus.svg",
    "reuniones": "calendar.svg",
    "participantes": "users-group.svg",
    "tareas": "clipboard-check.svg",
    "resumen": "file-description.svg",
    "ia": "brain.svg",
    "metricas": "chart-bar.svg",
    "salir": "logout.svg",
    "grafico": "chart-line.svg",
    "buscar": "search.svg",
    "agregar": "plus.svg",
    "eliminar": "trash.svg",
    "guardar": "device-floppy.svg",
    "pdf": "file-type-pdf.svg",
    "actualizar": "refresh.svg",
    "procesar": "rocket.svg",
    "tiempo": "clock.svg",
    "web": "world.svg",
    "idea": "bulb.svg",
    "correcto": "check.svg",
    "alerta": "alert-triangle.svg",
    "lista": "list-details.svg",
    "filtro": "filter.svg",
    "actividad": "activity.svg",
    "datos": "database.svg",
    "correo": "mail.svg",
    "candado": "lock.svg",
    "ver": "eye.svg",
    "informacion": "info-circle.svg",
    "virtual": "video.svg",
    "presencial": "user-pin.svg",
    "mixta": "users-group.svg",
    "borrador": "eraser.svg",
    "adjuntar": "paperclip.svg",
    "microfono": "microphone.svg",
    "enviar": "arrow-up.svg",
    "calendario": "calendar.svg",
    "destellos": "sparkles.svg",
    "aplicaciones": "layout-grid.svg",
    "compartir": "screen-share.svg",
    "notificacion": "bell.svg",
    "mas": "dots-vertical.svg",
    "siguiente": "chevron-right.svg",
    "acuerdos": "heart-handshake.svg",
    "reporte_teal": "file-description.svg",
    "reporte_morado": "file-description.svg",
    "tarea_naranja": "clipboard-check.svg",
}


def icono_data_uri(nombre: str, color: str = "#2563EB") -> str:
    """Carga un SVG local de Tabler y lo incrusta como imagen autosuficiente."""
    ruta = ICON_DIR / ICON_FILES[nombre]
    svg = ruta.read_text(encoding="utf-8").replace("currentColor", color)
    codificado = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{codificado}"


ICONOS_AZULES = {nombre: icono_data_uri(nombre) for nombre in ICON_FILES}
LOGO_DATA_URI = "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
LOGIN_REFERENCE_DATA_URI = "data:image/jpeg;base64," + base64.b64encode(LOGIN_REFERENCE_PATH.read_bytes()).decode("ascii")
GOOGLE_ICON_DATA_URI = "data:image/svg+xml;base64," + base64.b64encode(GOOGLE_ICON_PATH.read_bytes()).decode("ascii")

if DEMO_MODE:
    from demo_backend import install_demo_backend

    SUPABASE_URL = "http://demo.local"
    SUPABASE_ANON_KEY = "demo-anon-key"
    N8N_URL = "demo://create-meeting"
    N8N_RESUMEN_VIRTUAL_URL = "demo://summary/virtual"
    N8N_RESUMEN_PRESENCIAL_URL = "demo://summary/presencial"
    requests = install_demo_backend(requests)

HEADERS = {
    "apikey": SUPABASE_ANON_KEY or "",
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
}

st.set_page_config(
    page_title="VINCORA Meet",
    page_icon=str(LOGO_PATH),
    layout="wide",
)

# -------- Estilos globales --------
ESTILOS_GLOBALES = """
<style>
/* Tema editorial claro aprobado: marfil, blanco cálido, azul y tipografía clásica. */
:root {
    --canvas: #FBF8F2;
    --surface: #FFFFFF;
    --surface-soft: #F7F2E9;
    --line: #E7DCCF;
    --ink: #171717;
    --muted: #667085;
    --blue: #2563EB;
    --blue-soft: #EEF4FF;
    --shadow: 0 10px 28px rgba(77, 58, 34, 0.08);
}

html, body, [class*="css"], [data-testid="stAppViewContainer"] * {
    font-family: "Segoe UI", Arial, sans-serif;
}

[data-testid="stAppViewContainer"] {
    color: var(--ink);
    background:
        radial-gradient(900px 480px at 86% -15%, rgba(255,255,255,0.94), transparent 64%),
        linear-gradient(135deg, #FCFAF6 0%, var(--canvas) 58%, #F8F3EB 100%);
}
[data-testid="stHeader"] {
    background: rgba(251, 248, 242, 0.92);
    backdrop-filter: blur(10px);
}
#MainMenu, footer,
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stToolbar"] { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; }

/* Titulares editoriales */
h1, h2, h3, .login-title {
    font-family: Georgia, "Times New Roman", serif !important;
    color: var(--ink) !important;
}
.page-title, .section-title {
    display: flex;
    align-items: center;
    color: var(--ink);
}
.page-title { gap: 14px; margin: 0 0 1rem 0; }
.page-title img {
    width: 46px;
    height: 46px;
    flex: 0 0 46px;
}
.section-title { gap: 10px; margin: 1rem 0 0.65rem 0; }
.section-title img {
    width: 29px;
    height: 29px;
    flex: 0 0 29px;
}
h1 {
    font-weight: 700 !important;
    letter-spacing: -1px;
    line-height: 1.08;
    background: none !important;
    -webkit-text-fill-color: var(--ink) !important;
}
h2, h3 { font-weight: 700 !important; letter-spacing: -0.35px; }
p, label, [data-testid="stMarkdownContainer"] { color: var(--ink); }

/* Botones */
.stButton > button, [data-testid="stFormSubmitButton"] button, .stDownloadButton > button {
    min-height: 2.65rem;
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--surface);
    color: var(--ink);
    font-weight: 650;
    padding: 0.55rem 1.1rem;
    box-shadow: 0 4px 14px rgba(77, 58, 34, 0.05);
    transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-1px);
    border-color: var(--blue);
    color: var(--blue);
    box-shadow: 0 8px 22px rgba(37, 99, 235, 0.13);
}
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background: var(--blue);
    border-color: var(--blue);
    color: #FFFFFF;
    font-weight: 700;
}

/* Entradas y selectores */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stDateInput input, .stTimeInput input {
    color: var(--ink) !important;
    border-radius: 12px !important;
    background: var(--surface) !important;
    border: 1px solid var(--line) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus,
.stNumberInput input:focus, .stDateInput input:focus, .stTimeInput input:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.13) !important;
}
[data-baseweb="select"] > div {
    color: var(--ink) !important;
    border-radius: 12px !important;
    background: var(--surface) !important;
    border-color: var(--line) !important;
}
[data-baseweb="popover"], [role="listbox"] { background: var(--surface) !important; }

/* Pestañas */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: var(--surface-soft);
    padding: 6px;
    border-radius: 14px;
    border: 1px solid var(--line);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 8px 18px;
    color: var(--muted);
    font-weight: 650;
}
.stTabs [aria-selected="true"] {
    color: var(--blue) !important;
    background: var(--surface) !important;
    box-shadow: 0 3px 10px rgba(77, 58, 34, 0.08);
}

/* Tarjetas, métricas y formularios */
[data-testid="stMetric"] {
    min-height: 132px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: var(--shadow);
}
[data-testid="stMetricLabel"] { color: var(--muted); }
[data-testid="stMetricValue"] {
    color: var(--ink);
    font-family: Georgia, "Times New Roman", serif !important;
    font-weight: 700;
}
[data-testid="stForm"], [data-testid="stExpander"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 255, 255, 0.84);
    border-color: var(--line) !important;
    border-radius: 16px !important;
    box-shadow: var(--shadow);
}

/* Tablas y dataframes */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: var(--shadow);
}

/* Chat */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.9);
    border: 1px solid var(--line);
    border-radius: 16px;
    margin-bottom: 8px;
    box-shadow: 0 5px 18px rgba(77, 58, 34, 0.05);
}
[data-testid="stChatInput"] > div {
    background: var(--surface) !important;
    border-color: var(--line) !important;
    border-radius: 14px !important;
    box-shadow: var(--shadow);
}

/* Alertas y datos estructurados */
[data-testid="stAlert"] {
    border: 1px solid #E3D3C0;
    border-radius: 13px;
    box-shadow: 0 5px 18px rgba(77, 58, 34, 0.05);
}
[data-testid="stJson"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 8px;
}

/* Navegación lateral */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FBF7F0 0%, #F6F0E7 100%);
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] [data-testid="stRadio"] > label { display: none; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    margin: 3px 0;
    border-radius: 12px;
    border: 1px solid transparent;
    color: var(--ink);
    cursor: pointer;
    transition: all .15s ease;
    width: 100%;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255,255,255,0.72);
    border-color: var(--line);
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: var(--blue-soft);
    border-color: #7AA2FF;
    color: #1D4ED8;
    font-weight: 700;
    box-shadow: 0 5px 16px rgba(37, 99, 235, 0.10);
}
[data-testid="stSidebar"] [role="radiogroup"] > label::before {
    content: "";
    width: 19px;
    height: 19px;
    flex: 0 0 19px;
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
}
[data-testid="stSidebar"] [role="radiogroup"] > label > div:has(input[type="radio"]) {
    display: none !important;
}
[data-testid="stSidebar"] [role="radiogroup"] input[type="radio"] {
    display: none !important;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(1)::before {
    background-image: url("__ICON_INICIO__");
}
[data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(2)::before {
    background-image: url("__ICON_CHAT__");
}
[data-testid="stSidebar"] [role="radiogroup"]:has(> label:nth-child(10)) > label:nth-child(3)::before {
    background-image: url("__ICON_ADMINISTRACION__");
}
[data-testid="stSidebar"] [role="radiogroup"]:has(> label:nth-child(10)) > label:nth-child(4)::before,
[data-testid="stSidebar"] [role="radiogroup"]:not(:has(> label:nth-child(10))) > label:nth-child(3)::before {
    background-image: url("__ICON_REUNIONES__");
}
[data-testid="stSidebar"] [role="radiogroup"]:has(> label:nth-child(10)) > label:nth-child(5)::before,
[data-testid="stSidebar"] [role="radiogroup"]:not(:has(> label:nth-child(10))) > label:nth-child(4)::before {
    background-image: url("__ICON_TAREAS__");
}
[data-testid="stSidebar"] [role="radiogroup"]:has(> label:nth-child(10)) > label:nth-child(6)::before,
[data-testid="stSidebar"] [role="radiogroup"]:not(:has(> label:nth-child(10))) > label:nth-child(5)::before {
    background-image: url("__ICON_RESUMEN__");
}
[data-testid="stSidebar"] [role="radiogroup"]:has(> label:nth-child(10)) > label:nth-child(7)::before,
[data-testid="stSidebar"] [role="radiogroup"]:not(:has(> label:nth-child(10))) > label:nth-child(6)::before {
    background-image: url("__ICON_PARTICIPANTES__");
}
[data-testid="stSidebar"] [role="radiogroup"]:has(> label:nth-child(10)) > label:nth-child(8)::before,
[data-testid="stSidebar"] [role="radiogroup"]:not(:has(> label:nth-child(10))) > label:nth-child(7)::before {
    background-image: url("__ICON_IA__");
}
[data-testid="stSidebar"] [role="radiogroup"]:has(> label:nth-child(10)) > label:nth-child(9)::before,
[data-testid="stSidebar"] [role="radiogroup"]:not(:has(> label:nth-child(10))) > label:nth-child(8)::before {
    background-image: url("__ICON_METRICAS__");
}
[data-testid="stSidebar"] [role="radiogroup"]:has(> label:nth-child(10)) > label:nth-child(10)::before,
[data-testid="stSidebar"] [role="radiogroup"]:not(:has(> label:nth-child(10))) > label:nth-child(9)::before {
    background-image: url("__ICON_SALIR__");
}

/* Marca del sistema en el sidebar */
.brand-box {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 12px; margin-bottom: 10px;
    border-radius: 14px;
    background: rgba(255,255,255,0.84);
    border: 1px solid var(--line);
    box-shadow: 0 6px 20px rgba(77, 58, 34, 0.05);
}
.brand-logo {
    width: 48px; height: 48px; border-radius: 13px;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
    background: #FFFFFF;
    border: 1px solid #DCE5F5;
    box-shadow: 0 7px 18px rgba(37, 99, 235, 0.14);
}
.brand-logo img { width: 44px; height: 41px; object-fit: cover; }
.brand-name { font-weight: 800; font-size: 16px; line-height: 1.15; color: var(--ink); }
.brand-sub  { max-width: 145px; font-size: 10.5px; line-height: 1.25; color: var(--muted); }

/* Perfil del usuario */
.user-chip {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; margin: 4px 0 14px 0;
    border-radius: 12px;
    background: rgba(255,255,255,0.84); border: 1px solid var(--line);
}
.user-avatar {
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 13px; color: #1E3A8A;
    background: #CFE0FF;
}
.user-name  { font-weight: 700; font-size: 13px; color: var(--ink); line-height: 1.2; }
.user-level { font-size: 11px; color: var(--muted); text-transform: capitalize; }

/* Layout principal VINCORA aprobado */
[data-testid="stSidebar"] {
    width: 300px !important;
    min-width: 300px !important;
    background: #F7FAFF;
    border-right: 0;
}
[data-testid="stSidebar"] > div:first-child {
    margin: 8px;
    height: calc(100vh - 16px);
    background: #FFFFFF;
    border: 1px solid #E8EDF6;
    border-radius: 14px;
    box-shadow: 0 7px 24px rgba(30, 64, 175, 0.08);
}
[data-testid="stSidebarContent"] {
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}
[data-testid="stSidebarUserContent"] {
    padding: 20px 20px 16px !important;
}
[data-testid="stSidebar"] .brand-box {
    gap: 12px;
    padding: 18px 5px 20px;
    margin: -75px 0 18px 0;
    background: transparent;
    border: 0;
    border-radius: 0;
    box-shadow: none;
}
[data-testid="stSidebar"] .brand-logo {
    width: 58px;
    height: 58px;
    flex: 0 0 58px;
    border: 0;
    border-radius: 0;
    box-shadow: none;
}
[data-testid="stSidebar"] .brand-logo img {
    width: 58px;
    height: 55px;
}
[data-testid="stSidebar"] .brand-name {
    color: #071644;
    font-size: 19px;
    font-weight: 800;
    white-space: nowrap;
}
[data-testid="stSidebar"] .brand-sub {
    max-width: 175px;
    margin-top: 5px;
    color: #69758E;
    font-size: 11.5px;
    white-space: nowrap;
}
[data-testid="stSidebar"] .user-chip {
    min-height: 88px;
    margin: 0 0 28px 0;
    padding: 13px 13px;
    border: 1px solid #DCE3EF;
    border-radius: 12px;
    background: #FFFFFF;
}
[data-testid="stSidebar"] .user-avatar {
    width: 45px;
    height: 45px;
    flex: 0 0 45px;
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 500;
    background: linear-gradient(145deg, #76A9F8, #8B8CF7);
}
[data-testid="stSidebar"] .user-name {
    max-width: 155px;
    color: #13213F;
    font-size: 13.5px;
    line-height: 1.3;
}
[data-testid="stSidebar"] .user-level {
    margin-top: 4px;
    color: #7A859C;
    font-size: 11.5px;
    text-transform: none;
}
.user-chevron {
    width: 10px;
    height: 10px;
    margin-left: auto;
    margin-right: 3px;
    border-right: 2px solid #4A5875;
    border-bottom: 2px solid #4A5875;
    transform: rotate(45deg) translateY(-3px);
}
.nav-label {
    margin: 0 0 10px 14px;
    color: #6D7890;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .5px;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    position: relative;
    min-height: 51px;
    padding: 11px 14px;
    margin: 1px 0;
    border-radius: 9px;
    color: #182640;
    font-size: 13.5px;
    gap: 12px;
}
[data-testid="stSidebar"] .stRadio > label,
[data-testid="stSidebar"] [data-testid="stRadio"] > label:first-child {
    display: none !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label div:has(> input[type="radio"]),
[data-testid="stSidebar"] [role="radiogroup"] label div:has(input[type="radio"]):not(:has(p)) {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    color: #173E9E;
    background: linear-gradient(100deg, #EFF6FF 0%, #F0E6FF 100%);
    border-color: transparent;
    box-shadow: none;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-selected] {
    color: #173E9E;
    background: linear-gradient(100deg, #EFF6FF 0%, #F0E6FF 100%);
    border-color: transparent;
    box-shadow: none;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked)::after {
    content: "";
    position: absolute;
    left: -8px;
    top: 0;
    bottom: 0;
    width: 4px;
    border-radius: 0 4px 4px 0;
    background: #1764F5;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-selected]::after {
    content: "";
    position: absolute;
    left: -8px;
    top: 0;
    bottom: 0;
    width: 4px;
    border-radius: 0 4px 4px 0;
    background: #1764F5;
}
[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child > div:first-child {
    display: none !important;
}
[data-testid="stSidebar"] [role="radiogroup"] > label::before {
    width: 22px;
    height: 22px;
    flex-basis: 22px;
}
[data-testid="stSidebar"] [role="radiogroup"]:has(> label:nth-child(10)) > label:nth-child(10),
[data-testid="stSidebar"] [role="radiogroup"]:not(:has(> label:nth-child(10))) > label:nth-child(9) {
    margin-top: 70px;
    border-top: 1px solid #DFE5EF;
    border-radius: 0;
    padding-top: 25px;
    min-height: 72px;
}

/* Inicio VINCORA: réplica funcional del panel aprobado */
.home-page-marker { height: 0; overflow: hidden; }
[data-testid="stAppViewContainer"]:has(.home-page-marker) {
    color: #0B183A;
    background:
        radial-gradient(720px 460px at 55% 36%, rgba(224, 237, 255, .48), transparent 72%),
        #FBFDFF;
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) [data-testid="stHeader"],
[data-testid="stAppViewContainer"]:has(.home-page-marker) [data-testid="stAlert"] {
    display: none !important;
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) [data-testid="stElementContainer"]:has([data-testid="stAlert"]) {
    display: none !important;
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) .block-container {
    max-width: 100% !important;
    padding: 6px 38px 28px !important;
}
[data-testid="stElementContainer"]:has(.home-page-marker) { display: none !important; }
.home-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    min-height: 128px;
    padding: 4px 4px 0 8px;
}
.home-header h1 {
    margin: 0 !important;
    color: #0A183D !important;
    font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: 39px !important;
    font-weight: 800 !important;
    letter-spacing: -1.4px !important;
}
.home-header p {
    margin: 8px 0 0;
    color: #687795;
    font-size: 14.5px;
    transform: translateY(-16px);
}
.home-profile {
    display: flex;
    align-items: center;
    gap: 27px;
    padding-top: 16px;
}
.home-notification {
    position: relative;
    width: 30px;
    height: 30px;
    background: url("__ICON_NOTIFICACION__") center / 25px 25px no-repeat;
}
.home-notification::after {
    content: "";
    position: absolute;
    right: 2px;
    top: 0;
    width: 9px;
    height: 9px;
    border: 2px solid #FBFDFF;
    border-radius: 50%;
    background: #1261F5;
}
.home-avatar, .home-mini-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border-radius: 50%;
    color: #FFFFFF;
    font-weight: 750;
    background: linear-gradient(145deg, #5F93EE, #7559E9);
}
.home-avatar {
    width: 50px;
    height: 50px;
    border: 3px solid #FFFFFF;
    box-shadow: 0 5px 16px rgba(29, 58, 120, .14);
    font-size: 15px;
}
.home-mini-avatar {
    width: 25px;
    height: 25px;
    border: 2px solid #FFFFFF;
    margin-left: -7px;
    font-size: 8px;
    box-shadow: 0 2px 5px rgba(10,24,61,.13);
}
.home-mini-avatar:first-child { margin-left: 0; }
.home-avatar-more {
    color: #5F6F8D;
    background: #EDF1F8;
}

/* Cuatro acciones superiores */
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_new button,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_join button,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_schedule button,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_share button {
    position: relative;
    width: 100%;
    min-height: 131px;
    justify-content: flex-start;
    padding: 20px 18px 20px 90px;
    overflow: hidden;
    color: #0B183A;
    background: rgba(255,255,255,.95);
    border: 1px solid #DEE5F0;
    border-radius: 14px;
    box-shadow: 0 6px 17px rgba(23, 52, 104, .08);
    text-align: left;
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_new button p,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_join button p,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_schedule button p,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_share button p {
    position: absolute;
    left: 90px;
    top: 25px;
    width: calc(100% - 104px);
    margin: 0;
    color: inherit;
    font-size: 14.5px;
    font-weight: 750;
    line-height: 1.2;
    white-space: nowrap;
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_new button::before,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_join button::before,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_schedule button::before,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_share button::before {
    content: "";
    position: absolute;
    left: 18px;
    top: 23px;
    width: 53px;
    height: 53px;
    border: 1px solid #DCE5F4;
    border-radius: 13px;
    background-position: center;
    background-repeat: no-repeat;
    background-size: 28px 28px;
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_new button::after,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_join button::after,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_schedule button::after,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_share button::after {
    position: absolute;
    left: 90px;
    top: 63px;
    max-width: 140px;
    color: #71809B;
    font-size: 13px;
    font-weight: 400;
    line-height: 1.35;
    white-space: normal;
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_new button {
    color: #FFFFFF;
    border: 0;
    background: linear-gradient(130deg, #176BF7 0%, #3667F5 48%, #8B3FF3 100%);
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_new button p {
    color: #FFFFFF !important;
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_new button::before {
    border: 2px solid rgba(255,255,255,.62);
    background-image: url("__ICON_VIRTUAL__");
    filter: brightness(0) invert(1);
}
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_join button::before { background-image: url("__ICON_APLICACIONES__"); }
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_schedule button::before { background-image: url("__ICON_CALENDARIO__"); }
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_share button::before { background-image: url("__ICON_COMPARTIR__"); }
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_new button::after { content: "Inicia una reunión\\A al instante"; color: rgba(255,255,255,.94); white-space: pre; }
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_join button::after { content: "Únete a una reunión\\A con un código"; white-space: pre; }
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_schedule button::after { content: "Planifica y organiza\\A con anticipación"; white-space: pre; }
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_action_share button::after { content: "Presenta tu pantalla\\A en la reunión"; white-space: pre; }

/* Paneles de datos reales */
.home-main-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.7fr) minmax(310px, 1fr);
    gap: 18px;
    margin-top: 9px;
}
.home-panel {
    min-width: 0;
    background: rgba(255,255,255,.96);
    border: 1px solid #DEE5F0;
    border-radius: 14px;
    box-shadow: 0 6px 17px rgba(23, 52, 104, .08);
}
.home-panel-padding { padding: 24px 25px 17px; }
.home-panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 15px;
}
.home-panel-title {
    color: #101D40;
    font-size: 17px;
    font-weight: 800;
}
.home-link {
    color: #075DF4 !important;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none !important;
}
.home-link::after {
    content: "";
    display: inline-block;
    width: 14px;
    height: 14px;
    margin-left: 6px;
    vertical-align: -3px;
    background: url("__ICON_SIGUIENTE__") center / contain no-repeat;
}
.home-no-arrow::after { display: none; }
.home-meeting-row {
    position: relative;
    min-height: 113px;
    margin-left: 10px;
    padding: 5px 8px 14px 88px;
    border-bottom: 1px solid #E2E8F1;
}
.home-meeting-row::before {
    content: "";
    position: absolute;
    left: 5px;
    top: -19px;
    bottom: -1px;
    width: 1px;
    background: #DCE4F0;
}
.home-meeting-dot {
    position: absolute;
    left: -2px;
    top: 27px;
    width: 13px;
    height: 13px;
    border: 3px solid #FFFFFF;
    border-radius: 50%;
    background: #2C6CF6;
    box-shadow: 0 0 0 1px #7EA7FF;
}
.home-meeting-row:nth-of-type(3) .home-meeting-dot { background: #8A9AB5; box-shadow: 0 0 0 1px #B8C3D5; }
.home-meeting-calendar {
    position: absolute;
    left: 32px;
    top: 8px;
    width: 45px;
    height: 45px;
    border-radius: 13px;
    background: #EEF4FF url("__ICON_CALENDARIO__") center / 23px 23px no-repeat;
}
.home-meeting-title { color: #101D40; font-size: 14px; font-weight: 750; }
.home-meeting-time { margin-top: 4px; color: #647491; font-size: 13px; }
.home-meeting-meta { display: flex; align-items: center; gap: 15px; margin-top: 10px; }
.home-avatar-stack { display: flex; align-items: center; padding-left: 6px; }
.home-participant-count { color: #6A7B99; font-size: 12.5px; }
.home-meeting-actions { position: absolute; right: 0; top: 46px; display: flex; align-items: center; gap: 12px; }
.home-start-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 101px;
    min-height: 42px;
    color: #FFFFFF !important;
    border-radius: 7px;
    background: #075DF4;
    font-size: 13px;
    font-weight: 700;
    text-decoration: none !important;
}
.home-more-button {
    width: 38px;
    height: 40px;
    border: 1px solid #D4DDEA;
    border-radius: 8px;
    background: #FFFFFF url("__ICON_MAS__") center / 20px 20px no-repeat;
}
.home-card-footer { padding: 15px 1px 0; }
.home-summary-list { margin-top: 2px; }
.home-summary-row {
    display: grid;
    grid-template-columns: 47px 44px 1fr;
    align-items: center;
    min-height: 60px;
    border-bottom: 1px solid #E2E8F1;
}
.home-summary-icon, .home-report-icon {
    width: 43px;
    height: 43px;
    border-radius: 13px;
    background-position: center;
    background-repeat: no-repeat;
    background-size: 22px 22px;
}
.home-summary-icon.meetings { background-color: #EDF3FF; background-image: url("__ICON_CALENDARIO__"); }
.home-summary-icon.reports { background-color: #E7FBFA; background-image: url("__ICON_REPORTE_TEAL__"); }
.home-summary-icon.agreements { background-color: #F1E9FF; background-image: url("__ICON_ACUERDOS__"); }
.home-summary-icon.tasks { background-color: #FFF1E6; background-image: url("__ICON_TAREA_NARANJA__"); }
.home-summary-value { color: #0C193D; font-size: 24px; font-weight: 800; }
.home-summary-label { color: #687795; font-size: 12.5px; }

/* Fila inferior */
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_reports,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_tasks,
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_ai {
    min-height: 278px;
    margin-top: 18px;
    padding: 22px 21px 16px;
    background: rgba(255,255,255,.96);
    border: 1px solid #DEE5F0;
    border-radius: 14px;
    box-shadow: 0 6px 17px rgba(23, 52, 104, .08);
}
.home-report-row {
    position: relative;
    min-height: 79px;
    padding: 9px 40px 9px 52px;
    border-bottom: 1px solid #E2E8F1;
}
.home-report-icon { position: absolute; left: 0; top: 9px; }
.home-report-icon.approved { background-color: #E7FBFA; background-image: url("__ICON_REPORTE_TEAL__"); }
.home-report-icon.review { background-color: #F2E9FF; background-image: url("__ICON_REPORTE_MORADO__"); }
.home-report-title { overflow: hidden; color: #122043; font-size: 12.5px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.home-report-time { margin-top: 4px; color: #6A7A97; font-size: 11px; }
.home-status { display: inline-block; margin-top: 7px; padding: 3px 9px; border-radius: 7px; font-size: 10px; }
.home-status.approved { color: #137437; background: #E1F7E8; }
.home-status.review { color: #A46300; background: #FFF1D8; }
.home-report-more { position: absolute; right: 0; top: 18px; width: 34px; height: 34px; border: 1px solid #D4DDEA; border-radius: 8px; background: #FFF url("__ICON_MAS__") center / 18px no-repeat; }
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_tasks [data-testid="stCheckbox"] { padding-top: 5px; }
.home-task-text { color: #152342; font-size: 12px; font-weight: 600; line-height: 1.25; }
.home-task-meta { margin-top: 3px; color: #73809A; font-size: 10.5px; font-weight: 400; }
.home-task-progress { color: #5F6F8D; font-size: 11px; text-align: right; }
.home-progress-track { width: 72px; height: 4px; margin-top: 8px; margin-left: auto; overflow: hidden; border-radius: 999px; background: #E5EAF2; }
.home-progress-fill { height: 100%; border-radius: 999px; background: #1765F5; }
.home-task-row { min-height: 60px; padding: 6px 0; border-bottom: 1px solid #E2E8F1; }
[data-testid="stAppViewContainer"]:has(.home-page-marker) .st-key-home_tasks [class*="st-key-home_task_row_"] {
    min-height: 61px;
    padding: 5px 0 4px;
    border-bottom: 1px solid #E2E8F1;
}
.home-ai-brand { display: flex; align-items: center; gap: 10px; color: #111E40; font-size: 16px; font-weight: 800; }
.home-ai-brand img { width: 31px; height: 31px; }
.home-ai-ring {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 76px;
    height: 76px;
    margin: 24px auto 13px;
    border-radius: 50%;
    background: conic-gradient(#5E6CF4 0 78%, #D9CEF9 78% 100%);
    box-shadow: inset 0 0 0 10px #F7F9FE;
}
.home-ai-ring span { display: flex; align-items: center; justify-content: center; width: 48px; height: 48px; border-radius: 50%; color: #101E42; background: #FFFFFF; font-size: 25px; font-weight: 800; }
.home-ai-copy { color: #667491; font-size: 12.5px; line-height: 1.35; text-align: center; }
.home-ai-link { margin-top: 28px; }
@media (max-width: 1100px) {
    .home-main-grid { grid-template-columns: 1fr; }
    [data-testid="stAppViewContainer"]:has(.home-page-marker) .block-container { padding: 24px 24px 32px !important; }
    .home-header h1 { font-size: 32px !important; }
}

/* Página Chat */
.chat-page-marker { height: 0; overflow: hidden; }
[data-testid="stAppViewContainer"]:has(.chat-page-marker) {
    color: #0D1B3E;
    background:
        radial-gradient(880px 620px at 60% 60%, rgba(219, 233, 255, 0.40), transparent 70%),
        #FBFDFF;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stHeader"] {
    display: none !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) .block-container {
    max-width: 100% !important;
    padding: 6px 42px 30px !important;
}
[data-testid="stElementContainer"]:has(.chat-page-marker) {
    display: none !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stAlert"] {
    display: flex;
    align-items: center;
    min-height: 64px;
    margin: 0;
    padding: 4px 20px;
    color: #18233E;
    background: #FFFAE9;
    border: 1px solid #FFD56D;
    border-radius: 11px;
    box-shadow: 0 4px 15px rgba(174, 123, 18, 0.05);
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stAlert"] > div {
    background: transparent !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stAlert"]::before {
    content: "";
    width: 25px;
    height: 25px;
    margin-right: 16px;
    flex: 0 0 25px;
    background: url("__ICON_INFORMACION__") center / contain no-repeat;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stAlert"] p {
    color: #18233E;
    font-size: 14px;
}
.chat-page-heading {
    display: flex;
    align-items: center;
    gap: 16px;
    margin: 0;
}
.chat-page-heading img {
    width: 48px;
    height: 48px;
    flex: 0 0 48px;
}
.chat-page-heading h1 {
    margin: 0 !important;
    color: #071644 !important;
    font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: clamp(34px, 3vw, 44px) !important;
    font-weight: 800 !important;
    letter-spacing: -1.2px !important;
    -webkit-text-fill-color: #071644 !important;
}
.chat-page-description {
    margin: 12px 0 8px 0;
    color: #6D7890;
    font-size: 17px;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.chat-options-marker) {
    padding: 0 !important;
    border: 1px solid #DFE5EF !important;
    border-radius: 16px !important;
    background: rgba(255, 255, 255, 0.96) !important;
    box-shadow: 0 8px 24px rgba(30, 64, 175, 0.08) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.chat-options-marker) > div {
    padding: 27px 20px 28px !important;
}
.chat-options-marker {
    margin-bottom: 14px;
    color: #111F40;
    font-size: 18px;
    font-weight: 750;
}
.chat-field-title {
    margin-bottom: 7px;
    color: #13213F;
    font-size: 14px;
    font-weight: 600;
}
.chat-field-help {
    margin: -5px 0 8px;
    color: #7A859C;
    font-size: 12px;
}
.chat-options-divider {
    width: 1px;
    height: 87px;
    margin: 0 auto;
    background: #DCE3EF;
}
.chat-clear-spacer { height: 30px; }
.st-key-tipo_reunion [role="radiogroup"] {
    display: flex;
    width: 100%;
    gap: 0;
    border: 1px solid #CFD7E5;
    border-radius: 10px;
    overflow: hidden;
}
.st-key-tipo_reunion {
    width: 100% !important;
}
.st-key-tipo_reunion [data-testid="stRadioGroup"] {
    width: 100% !important;
}
.st-key-tipo_reunion [role="radiogroup"] > label {
    display: flex;
    min-height: 56px;
    flex: 1 1 33.333%;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin: 0;
    padding: 8px 10px;
    color: #263552;
    background: #FFFFFF;
    border: 0;
    border-right: 1px solid #D8DFEA;
    border-radius: 0;
    cursor: pointer;
}
.st-key-tipo_reunion [role="radiogroup"] > label:last-child { border-right: 0; }
.st-key-tipo_reunion [role="radiogroup"] > label:has(input:checked) {
    color: #FFFFFF;
    background: linear-gradient(105deg, #1764F5 0%, #345CF6 55%, #7654F5 100%);
    font-weight: 700;
}
.st-key-tipo_reunion [role="radiogroup"] > label[data-selected] {
    color: #FFFFFF;
    background: linear-gradient(105deg, #1764F5 0%, #345CF6 55%, #7654F5 100%);
    font-weight: 700;
}
.st-key-tipo_reunion [role="radiogroup"] > label > div:has(input) { display: none !important; }
.st-key-tipo_reunion [role="radiogroup"] > label div:has(> input[type="radio"]),
.st-key-tipo_reunion [role="radiogroup"] > label div:has(input[type="radio"]):not(:has(p)) {
    display: none !important;
}
.st-key-tipo_reunion label[data-testid="stRadioOption"] > div > div:first-child > div:first-child {
    display: none !important;
}
.st-key-tipo_reunion [role="radiogroup"] > label::before {
    content: "";
    width: 22px;
    height: 22px;
    flex: 0 0 22px;
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
}
.st-key-tipo_reunion [role="radiogroup"] > label:nth-child(1)::before { background-image: url("__ICON_VIRTUAL__"); }
.st-key-tipo_reunion [role="radiogroup"] > label:nth-child(2)::before { background-image: url("__ICON_PRESENCIAL__"); }
.st-key-tipo_reunion [role="radiogroup"] > label:nth-child(3)::before { background-image: url("__ICON_MIXTA__"); }
.st-key-tipo_reunion [role="radiogroup"] > label:has(input:checked)::before,
.st-key-tipo_reunion [role="radiogroup"] > label[data-selected]::before { filter: brightness(0) invert(1); }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.chat-options-marker) .stTextInput input {
    height: 48px;
    color: #263552 !important;
    background: #FFFFFF !important;
    border: 1px solid #CFD7E5 !important;
    border-radius: 10px !important;
}
.st-key-chat_limpiar button {
    min-height: 45px;
    color: #1F5EFF;
    background: #FFFFFF;
    border: 1.5px solid #2F68FF;
    border-radius: 10px;
    box-shadow: none;
}
.st-key-chat_limpiar button::before {
    content: "";
    width: 18px;
    height: 18px;
    background: url("__ICON_BORRADOR__") center / contain no-repeat;
}
.chat-empty-state {
    padding-top: 31px;
    text-align: center;
}
.chat-empty-logo {
    display: flex;
    width: 124px;
    height: 124px;
    margin: 0 auto 20px;
    align-items: center;
    justify-content: center;
    border: 1px solid #DFE7F5;
    border-radius: 50%;
    background: rgba(255,255,255,.78);
    box-shadow: 0 13px 30px rgba(72, 80, 232, .14);
}
.chat-empty-logo img {
    width: 88px;
    height: 83px;
    object-fit: cover;
}
.chat-empty-state h2 {
    margin: 0 0 10px !important;
    color: #071644 !important;
    font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: 25px !important;
    font-weight: 800 !important;
}
.chat-empty-state p {
    margin: 0 0 20px;
    color: #7A859C;
    font-size: 15px;
}
.st-key-chat_sugerencia_manana button,
.st-key-chat_sugerencia_semanal button,
.st-key-chat_sugerencia_invitados button {
    min-height: 46px;
    color: #1558E9;
    background: rgba(255,255,255,.80);
    border: 1.5px solid #3B6FFF;
    border-radius: 999px;
    box-shadow: none;
    font-size: 13px;
    font-weight: 650;
    white-space: nowrap;
}
.st-key-chat_sugerencia_manana button::before,
.st-key-chat_sugerencia_semanal button::before,
.st-key-chat_sugerencia_invitados button::before {
    content: "";
    width: 20px;
    height: 20px;
    flex: 0 0 20px;
    background-position: center;
    background-repeat: no-repeat;
    background-size: contain;
}
.st-key-chat_sugerencia_manana button::before { background-image: url("__ICON_CALENDARIO__"); }
.st-key-chat_sugerencia_semanal button::before { background-image: url("__ICON_PARTICIPANTES__"); }
.st-key-chat_sugerencia_invitados button::before { background-image: url("__ICON_ADMINISTRACION__"); }
.chat-example {
    margin: 18px 0 0;
    color: #7A859C;
    font-size: 14px;
    font-style: italic;
    text-align: center;
}
.chat-example::before {
    content: "";
    display: inline-block;
    width: 17px;
    height: 17px;
    margin-right: 9px;
    vertical-align: -3px;
    background: url("__ICON_DESTELLOS__") center / contain no-repeat;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatMessage"] {
    max-width: 880px;
    margin-left: auto;
    margin-right: auto;
    background: rgba(255,255,255,.92);
    border-color: #DFE5EF;
    box-shadow: 0 6px 18px rgba(30,64,175,.06);
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stBottom"] {
    background: transparent;
}
.chat-composer-marker { height: 30px; overflow: hidden; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.chat-composer-marker),
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .chat-composer-marker) {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInput"] > div {
    position: relative;
    min-height: 76px;
    background: #FFFFFF !important;
    border: 1px solid #D2DAE8 !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 28px rgba(30, 64, 175, .11) !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInput"] > div::before,
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInput"] > div::after {
    content: "";
    position: absolute;
    top: 50%;
    z-index: 5;
    width: 27px;
    height: 27px;
    pointer-events: none;
    transform: translateY(-50%);
    background-position: center;
    background-repeat: no-repeat;
    background-size: contain;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInput"] > div::before {
    left: 22px;
    background-image: url("__ICON_ADJUNTAR__");
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInput"] > div::after {
    right: 72px;
    width: 25px;
    height: 25px;
    background-image: url("__ICON_MICROFONO__");
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInput"] textarea {
    color: #253453 !important;
    font-size: 15px;
    padding-left: 58px !important;
    padding-right: 114px !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInputSubmitButton"] {
    width: 54px;
    height: 54px;
    margin-right: 5px;
    color: #FFFFFF !important;
    background: linear-gradient(145deg, #20A5F5 0%, #3E6AF8 52%, #9A3EF3 100%) !important;
    border: 0 !important;
    border-radius: 50% !important;
    box-shadow: 0 8px 18px rgba(74, 83, 244, .25) !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInputFileUploadButton"] button {
    color: transparent !important;
    background: transparent !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInputFileUploadButton"] button svg,
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInputMicButton"] svg,
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInputSubmitButton"] svg {
    display: none !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInputMicButton"] {
    color: transparent !important;
    background: transparent !important;
}
[data-testid="stAppViewContainer"]:has(.chat-page-marker) [data-testid="stChatInputSubmitButton"] {
    background-image: url("__ICON_ENVIAR__"), linear-gradient(145deg, #20A5F5 0%, #3E6AF8 52%, #9A3EF3 100%) !important;
    background-position: center, center !important;
    background-size: 25px 25px, 100% 100% !important;
    background-repeat: no-repeat !important;
}
.chat-disclaimer {
    margin: 5px 0 0;
    color: #8B95A9;
    font-size: 11px;
    text-align: center;
}
@media (max-width: 980px) {
    [data-testid="stAppViewContainer"]:has(.chat-page-marker) .block-container { padding: 20px 22px 112px !important; }
    .chat-page-heading h1 { font-size: 31px !important; }
    .chat-options-divider { display: none; }
    .st-key-chat_sugerencia_manana button,
    .st-key-chat_sugerencia_semanal button,
    .st-key-chat_sugerencia_invitados button { white-space: normal; }
}

/* Usuarios y permisos: réplica funcional del panel de referencia */
.users-page-marker { height: 0; overflow: hidden; }
[data-testid="stAppViewContainer"]:has(.users-page-marker) {
    color: #0B183A;
    background:
        radial-gradient(760px 460px at 58% 22%, rgba(225, 235, 252, .72), transparent 72%),
        linear-gradient(135deg, #F8FAFE 0%, #F2F6FC 100%);
}
[data-testid="stAppViewContainer"]:has(.users-page-marker) [data-testid="stHeader"] { background: transparent; }
[data-testid="stAppViewContainer"]:has(.users-page-marker) .block-container {
    max-width: none !important;
    padding: 27px 40px 52px !important;
}
.users-heading { display: flex; align-items: center; gap: 17px; margin: 0; }
.users-heading img { width: 45px; height: 45px; flex: 0 0 45px; }
.users-heading h1 {
    margin: 0 !important;
    color: #071644 !important;
    font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: 34px !important;
    font-weight: 800 !important;
    letter-spacing: -1px !important;
    -webkit-text-fill-color: #071644 !important;
}
.users-subtitle { margin: 3px 0 22px 2px; color: #64718B; font-size: 15px; }
.st-key-users_invite_open { display: flex; justify-content: flex-end; padding-top: 6px; }
.st-key-users_invite_open button {
    width: 166px; min-height: 45px;
    color: #FFFFFF !important; background: #195DD8 !important;
    border: 0 !important; border-radius: 6px !important;
    box-shadow: 0 8px 18px rgba(25, 93, 216, .20) !important;
    font-size: 14px; font-weight: 700;
}
.st-key-users_invite_open button::before {
    content: "+"; margin-right: 10px; color: #FFFFFF;
    font-size: 25px; font-weight: 300; line-height: 1;
}
.users-metrics {
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 18px; margin: 0 0 27px;
}
.users-metric {
    min-height: 98px; display: flex; align-items: center; gap: 16px;
    padding: 17px 20px; background: rgba(255, 255, 255, .91);
    border: 1px solid #DDE4EF; border-radius: 10px;
    box-shadow: 0 5px 13px rgba(34, 57, 98, .07);
}
.users-metric-icon {
    width: 55px; height: 55px; flex: 0 0 55px;
    display: flex; align-items: center; justify-content: center; border-radius: 50%;
}
.users-metric-icon img { width: 30px; height: 30px; }
.users-metric-icon.total { background: #EEE8FF; }
.users-metric-icon.active { background: #E2F6F6; }
.users-metric-icon.pending { background: #FFF2DF; }
.users-metric-icon.suspended { background: #FDE8EB; }
.users-metric-value { color: #071644; font-size: 29px; font-weight: 800; line-height: 1; }
.users-metric-label { margin-top: 5px; color: #5F6C86; font-size: 12.5px; line-height: 1.15; }
.users-filter-marker { height: 0; overflow: hidden; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.users-filter-marker),
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .users-filter-marker) {
    padding: 20px 16px 19px !important;
    background: rgba(255,255,255,.92) !important;
    border: 1px solid #DCE4F0 !important;
    border-radius: 11px 11px 0 0 !important;
    box-shadow: 0 7px 20px rgba(34,57,98,.07) !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .users-filter-marker) [data-testid="stHorizontalBlock"] { align-items: end; }
.st-key-users_search label { display: none; }
.st-key-users_search input {
    height: 45px; padding-left: 41px !important; color: #31405F !important;
    background: #FFFFFF url("__ICON_BUSCAR__") 13px center / 20px 20px no-repeat !important;
    border: 1px solid #CDD6E4 !important; border-radius: 7px !important; font-size: 13px;
}
.st-key-users_role_filter label, .st-key-users_status_filter label {
    margin: 0 0 -9px 12px; position: relative; z-index: 2;
    width: max-content; padding: 0 5px; color: #6E7890;
    background: #FFFFFF; font-size: 11px;
}
.st-key-users_role_filter [data-baseweb="select"] > div,
.st-key-users_status_filter [data-baseweb="select"] > div,
.st-key-users_per_page [data-baseweb="select"] > div {
    min-height: 45px; border: 1px solid #CDD6E4 !important;
    border-radius: 7px !important; box-shadow: none !important;
}
.st-key-users_apply_filter button {
    width: 48px; min-height: 45px; color: transparent !important; font-size: 0 !important;
    background: #FFFFFF url("__ICON_FILTRO__") center / 21px 21px no-repeat !important;
    border: 1px solid #CDD6E4 !important; border-radius: 7px !important; box-shadow: none !important;
}
.users-table {
    display: grid;
    grid-template-columns: minmax(280px, 2.2fr) minmax(105px, .85fr) minmax(105px, .85fr) minmax(130px, 1fr) minmax(125px, 1fr) 64px;
    width: 100%; color: #172547; background: #FFFFFF;
    border-left: 1px solid #DCE4F0; border-right: 1px solid #DCE4F0;
}
.users-table > div {
    min-width: 0; min-height: 84px; display: flex; align-items: center;
    padding: 15px 14px; border-bottom: 1px solid #E1E7F0; font-size: 12.5px;
}
.users-table > .users-th {
    min-height: 55px; padding-top: 12px; padding-bottom: 12px;
    color: #42516D; background: #FBFCFE; font-size: 11.5px; font-weight: 700;
}
.users-person { display: flex; align-items: center; min-width: 0; gap: 12px; }
.users-avatar {
    width: 45px; height: 45px; flex: 0 0 45px;
    display: flex; align-items: center; justify-content: center;
    color: #FFFFFF; background: linear-gradient(145deg, #71A7F8, #7C6EF1);
    border: 2px solid #FFFFFF; border-radius: 50%;
    box-shadow: 0 2px 8px rgba(31,72,150,.18); font-size: 13px; font-weight: 750;
}
.users-person-copy { min-width: 0; }
.users-person-name {
    overflow: hidden; color: #0A1738; font-size: 13px; font-weight: 750;
    text-overflow: ellipsis; white-space: nowrap;
}
.users-person-email {
    overflow: hidden; margin-top: 3px; color: #70809C; font-size: 10.5px;
    text-overflow: ellipsis; white-space: nowrap;
}
.users-role-pill, .users-status-pill {
    display: inline-flex; align-items: center; gap: 7px;
    border-radius: 6px; font-weight: 650; line-height: 1.15;
}
.users-role-pill { padding: 7px 10px; color: #33425F; background: #F0F3F8; }
.users-role-pill.admin { color: #235ACB; background: #EAF0FF; }
.users-status-pill { padding: 6px 9px; }
.users-status-pill::before { content: ""; width: 6px; height: 6px; border-radius: 50%; }
.users-status-pill.active { color: #128058; background: #E3F5EB; }
.users-status-pill.active::before { background: #0AA36D; }
.users-status-pill.pending { max-width: 100px; color: #B66A00; background: #FFF2DF; }
.users-status-pill.pending::before { flex: 0 0 6px; background: #F39B12; }
.users-status-pill.suspended { color: #B62B36; background: #FCE8EB; }
.users-status-pill.suspended::before { background: #D83C48; }
.users-action-link {
    width: 38px; height: 38px; display: inline-flex; align-items: center; justify-content: center;
    color: #132446 !important; border: 1px solid #D5DDE9; border-radius: 7px;
    text-decoration: none !important; font-size: 22px; line-height: 1;
}
.users-empty { grid-column: 1 / -1; min-height: 130px !important; justify-content: center; color: #71809A; }
.users-page-number {
    min-width: 38px; height: 38px; display: inline-flex; align-items: center; justify-content: center;
    color: #1B4FB7; background: #F5F8FD; border: 1px solid #DCE4F0; font-weight: 700;
}
.st-key-users_footer {
    margin-top: -1px; padding: 11px 16px 10px; background: #FFFFFF;
    border: 1px solid #DCE4F0; border-radius: 0 0 11px 11px;
    box-shadow: 0 7px 20px rgba(34,57,98,.07);
}
.st-key-users_footer [data-testid="stHorizontalBlock"] { align-items: center; }
.st-key-users_footer [data-testid="stCaptionContainer"] { color: #6A7690; font-size: 11.5px; }
.st-key-users_footer .stButton button {
    min-width: 38px; min-height: 38px; padding: 0; color: #1B4FB7;
    background: #FFFFFF; border: 1px solid #DCE4F0; border-radius: 0;
    box-shadow: none; font-size: 20px;
}
.st-key-users_footer .stButton button:disabled { color: #9BA5B7; background: #F8FAFD; }
.st-key-users_footer .users-page-number { width: 100%; }
.st-key-users_footer .stSelectbox label { display: none; }
.st-key-users_footer [data-baseweb="select"] > div { min-height: 38px; font-size: 11px; }
.users-dialog-marker { height: 0; overflow: hidden; }
div[role="dialog"]:has(.users-dialog-marker) {
    width: min(510px, calc(100vw - 34px)) !important; max-width: 510px !important;
    padding: 0 !important; border: 0 !important; border-radius: 15px !important;
    box-shadow: 0 24px 60px rgba(20, 37, 74, .22) !important;
}
div[role="dialog"]:has(.users-dialog-marker) > div { padding: 25px 32px 27px !important; }
div[role="dialog"]:has(.users-dialog-marker) h2 {
    color: #071644 !important; font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: 23px !important; font-weight: 800 !important; letter-spacing: -.5px !important;
}
div[role="dialog"]:has(.users-dialog-marker) [data-testid="stForm"] {
    padding: 0; background: transparent; border: 0 !important; box-shadow: none;
}
div[role="dialog"]:has(.users-dialog-marker) .stTextInput input,
div[role="dialog"]:has(.users-dialog-marker) [data-baseweb="select"] > div {
    min-height: 40px; border: 1px solid #CCD5E4 !important;
    border-radius: 7px !important; box-shadow: none !important;
}
div[role="dialog"]:has(.users-dialog-marker) label { color: #142347; font-size: 12px; font-weight: 650; }
.users-dialog-description { margin: -7px 0 16px; color: #68758F; font-size: 13px; }
.users-permission-title { margin: 4px 0 1px; color: #142347; font-size: 12px; font-weight: 700; }
.users-invite-info {
    display: flex; align-items: center; gap: 12px; min-height: 54px;
    margin: 6px 0 12px; padding: 11px 14px; color: #5E78C9;
    background: #FAFCFF; border: 1px solid #7EA6FF; border-radius: 7px; font-size: 11px;
}
.users-invite-info img { width: 19px; height: 19px; }
div[role="dialog"]:has(.users-dialog-marker) [data-testid="stFormSubmitButton"] button {
    height: 45px; border-radius: 7px !important; box-shadow: none !important;
}
.users-invite-link-label { margin-top: 10px; color: #142347; font-size: 12px; font-weight: 700; }
.invite-accept-marker { height: 0; overflow: hidden; }
[data-testid="stAppViewContainer"]:has(.invite-accept-marker) { background: linear-gradient(135deg, #F6F9FE 0%, #EEF3FB 100%); }
[data-testid="stAppViewContainer"]:has(.invite-accept-marker) .block-container {
    max-width: 580px !important; padding: 56px 24px !important;
}
.invite-accept-card {
    padding: 30px 34px 18px; background: #FFFFFF; border: 1px solid #DCE4F0;
    border-radius: 16px; box-shadow: 0 18px 50px rgba(30,64,175,.12);
}
@media (max-width: 1100px) {
    [data-testid="stAppViewContainer"]:has(.users-page-marker) .block-container { padding: 24px 24px 46px !important; }
    .users-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .users-table { grid-template-columns: minmax(240px, 2fr) 110px 100px 120px 125px 55px; overflow-x: auto; }
}
@media (max-width: 720px) {
    .users-heading h1 { font-size: 27px !important; }
    .users-metrics { grid-template-columns: 1fr; }
    .users-table { min-width: 860px; }
}

/* Reuniones: calendario y programación según la referencia VINCORA */
.meetings-page-marker { height: 0; overflow: hidden; }
[data-testid="stAppViewContainer"]:has(.meetings-page-marker) {
    color: #0B183A;
    background: linear-gradient(135deg, #F8FAFE 0%, #F1F5FB 100%);
}
[data-testid="stAppViewContainer"]:has(.meetings-page-marker) [data-testid="stHeader"] { background: transparent; }
[data-testid="stAppViewContainer"]:has(.meetings-page-marker) .block-container {
    max-width: none !important; padding: 25px 24px 48px !important;
}
.meetings-heading { display: flex; align-items: center; gap: 16px; }
.meetings-heading img { width: 38px; height: 38px; }
.meetings-heading h1 {
    margin: 0 !important; color: #071644 !important; -webkit-text-fill-color: #071644 !important;
    font: 800 30px/1.1 "Segoe UI", Arial, sans-serif !important; letter-spacing: -.7px !important;
}
.meetings-subtitle { margin: 5px 0 18px 1px; color: #68758E; font-size: 14px; }
.st-key-meetings_view [data-testid="stWidgetLabel"] { display: none; }
.st-key-meetings_view [data-baseweb="button-group"] { gap: 10px; }
.st-key-meetings_view [data-baseweb="button-group"] button {
    min-height: 36px; padding: 6px 21px; color: #273552; background: transparent;
    border: 0 !important; border-radius: 18px !important; box-shadow: none !important; font-size: 13px;
}
.st-key-meetings_view [data-baseweb="button-group"] button[aria-pressed="true"] {
    color: #1455CE !important; background: #E7EEFA !important; font-weight: 700;
}
.meetings-shell {
    overflow: hidden; margin-top: 8px; background: rgba(255,255,255,.94);
    border: 1px solid #D9E2EF; border-radius: 13px; box-shadow: 0 7px 20px rgba(31,52,91,.06);
}
.meetings-toolbar {
    min-height: 74px; display: flex; align-items: center; justify-content: space-between;
    padding: 13px 19px; border-bottom: 1px solid #DCE4EF;
}
.meetings-month { display: flex; align-items: center; gap: 17px; color: #071644; font-size: 18px; font-weight: 800; }
.meetings-month-arrow { color: #314563; font-size: 30px; font-weight: 300; }
.meetings-toolbar-actions { display: flex; align-items: center; gap: 8px; }
.meetings-toolbar-button {
    min-width: 51px; height: 37px; display: inline-flex; align-items: center; justify-content: center;
    color: #273958 !important; background: #FFF; border: 1px solid #D3DCE9; border-radius: 7px;
    text-decoration: none !important; font-size: 12px; font-weight: 650;
}
.meetings-toolbar-button.arrow { min-width: 43px; font-size: 20px; }
.meetings-toolbar-button.primary {
    min-width: 159px; color: #FFF !important; background: #195ED8; border-color: #195ED8; font-size: 13px;
}
.meetings-toolbar-button.primary::before { content: "+"; margin-right: 10px; font-size: 23px; font-weight: 300; }
.meetings-layout { display: grid; grid-template-columns: minmax(0, 1fr) 280px; }
.meetings-calendar { min-width: 0; border-right: 1px solid #DCE4EF; }
.meetings-weekdays, .meetings-days { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); }
.meetings-weekday {
    min-height: 46px; display: flex; align-items: center; justify-content: center;
    color: #53617B; background: #FBFCFE; border-bottom: 1px solid #DCE4EF;
    font-size: 10.5px; font-weight: 750;
}
.meetings-day {
    min-height: 118px; overflow: hidden; padding: 13px 10px 8px;
    border-right: 1px solid #E1E7F0; border-bottom: 1px solid #E1E7F0; background: #FFF;
}
.meetings-day:nth-child(7n) { border-right: 0; }
.meetings-day.outside { color: #9AA5B7; background: #FBFCFE; }
.meetings-day-number { color: #263754; font-size: 12.5px; font-weight: 650; }
.meetings-day.outside .meetings-day-number { color: #9AA5B7; }
.meetings-day.today .meetings-day-number {
    width: 25px; height: 25px; display: inline-flex; align-items: center; justify-content: center;
    color: #FFF; background: #1D63DF; border-radius: 50%;
}
.meetings-event {
    display: block; overflow: hidden; margin-top: 6px; padding: 4px 6px;
    color: #FFF !important; background: #1761D9; border-radius: 4px;
    text-decoration: none !important; font-size: 9px; line-height: 1.25; text-overflow: ellipsis; white-space: nowrap;
}
.meetings-event.external { background: #7136C9; }
.meetings-legend { display: flex; gap: 22px; padding: 15px 16px; color: #66738B; font-size: 10px; }
.meetings-legend span { display: inline-flex; align-items: center; gap: 8px; }
.meetings-legend i { width: 12px; height: 12px; background: #1761D9; border-radius: 50%; }
.meetings-legend i.external { background: #7136C9; }
.meetings-agenda { padding: 18px 15px 14px; background: #FBFCFE; }
.meetings-agenda h2 { margin: 0; color: #071644; font-size: 18px; }
.meetings-agenda-date { margin: 4px 0 17px; color: #596780; font-size: 11px; }
.meetings-agenda-card {
    margin-bottom: 13px; padding: 13px 12px 12px; background: #FFF;
    border: 1px solid #D6DFEA; border-left: 5px solid #1761D9; border-radius: 8px;
}
.meetings-agenda-card.external { border-left-color: #7136C9; }
.meetings-agenda-time { color: #155DD9; font-size: 10px; font-weight: 750; }
.meetings-agenda-card.external .meetings-agenda-time { color: #7136C9; }
.meetings-agenda-title { margin: 8px 0 6px; color: #0C1938; font-size: 12px; font-weight: 800; }
.meetings-agenda-guests { color: #697790; font-size: 10.5px; }
.meetings-type-pill { display: inline-flex; margin-top: 8px; padding: 4px 8px; color: #1758C7; background: #E9F0FC; border-radius: 4px; font-size: 9px; }
.meetings-agenda-empty { margin: 28px 0; color: #71809A; font-size: 12px; text-align: center; }
.meetings-agenda-link {
    min-height: 38px; display: flex; align-items: center; justify-content: center;
    margin-top: 22px; color: #1557C8 !important; border: 1px solid #1D62D5; border-radius: 6px;
    text-decoration: none !important; font-size: 11px; font-weight: 700;
}
.meetings-list { display: grid; gap: 12px; margin-top: 8px; }
.meetings-list-card { padding: 17px 19px; background: #FFF; border: 1px solid #D9E2EF; border-radius: 10px; }
.meetings-list-card h3 { margin: 0 0 5px; color: #0B183A; font-size: 15px; }
.meetings-list-card p { margin: 0; color: #68758E; font-size: 12px; }
.meetings-list-card a { color: #155ED5; text-decoration: none; font-weight: 700; }
div[role="dialog"]:has(.meeting-dialog-marker) {
    width: min(560px, calc(100vw - 30px)) !important; max-width: 560px !important;
    padding: 0 !important; border: 0 !important; border-radius: 15px !important;
    box-shadow: 0 24px 65px rgba(18,34,69,.24) !important;
}
[data-baseweb="modal"]:has(.meeting-dialog-marker) {
    width: min(575px, calc(100vw - 30px)) !important; max-width: 575px !important;
    border: 0 !important; border-radius: 15px !important;
    box-shadow: 0 24px 65px rgba(18,34,69,.24) !important;
}
[data-baseweb="modal"]:has(.meeting-dialog-marker) > div { padding: 25px 29px 26px !important; }
[data-baseweb="modal"]:has(.meeting-dialog-marker) h2 {
    color: #071644 !important; font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: 23px !important; font-weight: 800 !important; letter-spacing: -.4px !important;
}
[role="dialog"] h2 {
    color: #071644 !important; font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: 23px !important; font-weight: 800 !important; letter-spacing: -.4px !important;
}
[data-baseweb="modal"]:has(.meeting-dialog-marker) [data-testid="stForm"] {
    padding: 0 !important; background: transparent !important; border: 0 !important; box-shadow: none !important;
}
[data-baseweb="modal"]:has(.meeting-dialog-marker) [data-testid="stFormSubmitButton"] button { min-height: 44px; border-radius: 7px !important; }
[data-baseweb="modal"]:has(.meeting-dialog-marker) [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {
    color: #FFF !important; border: 0 !important;
    background: linear-gradient(100deg, #1765ED 0%, #3D64F5 55%, #9346F4 100%) !important;
}
div[role="dialog"]:has(.meeting-dialog-marker) > div { padding: 25px 29px 26px !important; }
div[role="dialog"]:has(.meeting-dialog-marker) h2 {
    color: #071644 !important; font: 800 23px/1.15 "Segoe UI", Arial, sans-serif !important;
}
.meeting-dialog-marker { height: 0; overflow: hidden; }
.meeting-dialog-description { margin: -6px 0 17px; color: #65728B; font-size: 12px; }
div[role="dialog"]:has(.meeting-dialog-marker) [data-testid="stForm"] { padding: 0; border: 0; }
div[role="dialog"]:has(.meeting-dialog-marker) label { color: #142347; font-size: 11.5px; font-weight: 700; }
div[role="dialog"]:has(.meeting-dialog-marker) input,
div[role="dialog"]:has(.meeting-dialog-marker) textarea,
div[role="dialog"]:has(.meeting-dialog-marker) [data-baseweb="select"] > div {
    border-color: #CCD6E5 !important; border-radius: 7px !important; box-shadow: none !important;
}
.st-key-meeting_assistant { margin: 4px 0 6px; padding: 10px 13px 7px; border: 1px solid #D4DDEA; border-radius: 8px; }
.meeting-assistant-title { margin-bottom: 3px; color: #142347; font-size: 12.5px; font-weight: 800; }
.meeting-assistant-option { display: flex; align-items: center; gap: 10px; min-height: 32px; color: #1A2948; font-size: 11.5px; }
.meeting-assistant-option img { width: 19px; height: 19px; }
.st-key-meeting_assistant [data-testid="stHorizontalBlock"] { align-items: center; }
.st-key-meeting_assistant .stToggle { display: flex; justify-content: flex-end; }
.meeting-dialog-note { margin: 7px 0 13px; color: #647493; font-size: 10.5px; font-style: italic; }
div[role="dialog"]:has(.meeting-dialog-marker) [data-testid="stFormSubmitButton"] button {
    min-height: 44px; border-radius: 7px !important; box-shadow: none !important;
}
div[role="dialog"]:has(.meeting-dialog-marker) [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {
    color: #FFF !important; border: 0 !important;
    background: linear-gradient(100deg, #1765ED 0%, #3D64F5 55%, #9346F4 100%) !important;
}
.prejoin-page-marker { height: 0; overflow: hidden; }
[data-testid="stAppViewContainer"]:has(.prejoin-page-marker) [data-testid="stHeader"],
[data-testid="stAppViewContainer"]:has(.prejoin-page-marker) [data-testid="stSidebar"],
[data-testid="stAppViewContainer"]:has(.prejoin-page-marker) [data-testid="stAlert"] { display: none !important; }
[data-testid="stAppViewContainer"]:has(.prejoin-page-marker) .block-container {
    max-width: none !important; padding: 0 !important;
}
[data-testid="stAppViewContainer"]:has(.prejoin-page-marker) iframe {
    display: block; width: 100%; border: 0;
}
@media (max-width: 980px) {
    .meetings-layout { grid-template-columns: 1fr; }
    .meetings-calendar { border-right: 0; }
    .meetings-day { min-height: 92px; }
}

/* Acceso VINCORA: composición exacta en dos paneles */
.auth-page-marker, .auth-panel-marker { height: 0; overflow: hidden; }
[data-testid="stAppViewContainer"]:has(.auth-page-marker) {
    background: #FFFFFF;
}
[data-testid="stAppViewContainer"]:has(.auth-page-marker) [data-testid="stHeader"] {
    display: none;
}
[data-testid="stAppViewContainer"]:has(.auth-page-marker) [data-testid="stAlert"] {
    display: none !important;
}
[data-testid="stAppViewContainer"]:has(.auth-page-marker) .block-container {
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
}
[data-testid="stHorizontalBlock"]:has(.auth-visual-panel) {
    gap: 0 !important;
    min-height: 100vh;
    align-items: stretch;
}
[data-testid="stColumn"]:has(.auth-visual-panel),
[data-testid="column"]:has(.auth-visual-panel) {
    padding: 0 !important;
    min-height: 100vh;
}
.auth-visual-panel {
    width: 100%;
    height: 100vh;
    min-height: 760px;
    background-repeat: no-repeat;
    background-position: left top;
    background-size: 160.75% 100%;
}
[data-testid="stColumn"]:has(.auth-panel-marker),
[data-testid="column"]:has(.auth-panel-marker) {
    min-height: 100vh;
    padding: 62px clamp(44px, 4.6vw, 76px) 32px !important;
    background: #FFFFFF;
    overflow-y: auto;
}
.auth-brand {
    display: flex;
    align-items: center;
    gap: 18px;
    margin-bottom: 40px;
}
.auth-brand img {
    width: 84px;
    height: 78px;
    object-fit: cover;
    flex: 0 0 84px;
}
.auth-wordmark {
    color: #071644;
    font-size: clamp(34px, 3vw, 48px);
    font-weight: 800;
    line-height: 0.95;
    letter-spacing: 5px;
}
.auth-tagline {
    margin-top: 12px;
    color: #5F687D;
    font-size: clamp(15px, 1.4vw, 20px);
    white-space: nowrap;
}
.auth-heading {
    margin: 0 !important;
    color: #071644 !important;
    font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: clamp(32px, 2.5vw, 42px) !important;
    font-weight: 800 !important;
    letter-spacing: -1.2px !important;
    -webkit-text-fill-color: #071644 !important;
}
.auth-description {
    margin: 7px 0 28px 0;
    color: #697287;
    font-size: 19px;
    text-align: center;
}
[data-testid="stColumn"]:has(.auth-panel-marker) [data-testid="stForm"],
[data-testid="column"]:has(.auth-panel-marker) [data-testid="stForm"] {
    padding: 0;
    background: transparent;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none;
}
[data-testid="stColumn"]:has(.auth-panel-marker) .stTextInput label,
[data-testid="column"]:has(.auth-panel-marker) .stTextInput label {
    color: #17254A;
    font-size: 15px;
    font-weight: 500;
}
[data-testid="stColumn"]:has(.auth-panel-marker) .stTextInput input,
[data-testid="column"]:has(.auth-panel-marker) .stTextInput input {
    height: 56px;
    padding-left: 50px !important;
    color: #17254A !important;
    border: 1px solid #CBD3E2 !important;
    border-radius: 11px !important;
    background-color: #FFFFFF !important;
    background-repeat: no-repeat !important;
    background-position: 16px center !important;
    background-size: 20px 20px !important;
}
[data-testid="stColumn"]:has(.auth-panel-marker) .stTextInput div[data-baseweb="input"],
[data-testid="column"]:has(.auth-panel-marker) .stTextInput div[data-baseweb="input"] {
    min-height: 56px;
    overflow: hidden;
    border: 1px solid #CBD3E2 !important;
    border-radius: 11px !important;
    background: #FFFFFF !important;
}
[data-testid="stColumn"]:has(.auth-panel-marker) .stTextInput div[data-baseweb="input"] input,
[data-testid="column"]:has(.auth-panel-marker) .stTextInput div[data-baseweb="input"] input {
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
[data-testid="stColumn"]:has(.auth-panel-marker) input[aria-label="Correo electrónico"],
[data-testid="column"]:has(.auth-panel-marker) input[aria-label="Correo electrónico"] {
    background-image: url("__ICON_CORREO__") !important;
}
[data-testid="stColumn"]:has(.auth-panel-marker) input[aria-label="Contraseña"],
[data-testid="column"]:has(.auth-panel-marker) input[aria-label="Contraseña"] {
    background-image: url("__ICON_CANDADO__") !important;
}
[data-testid="stColumn"]:has(.auth-panel-marker) .stTextInput button,
[data-testid="column"]:has(.auth-panel-marker) .stTextInput button {
    width: 48px;
    min-width: 48px;
    height: 54px;
    padding: 0 !important;
    color: transparent !important;
    font-size: 0 !important;
    background: #FFFFFF url("__ICON_VER__") center / 21px 21px no-repeat !important;
    border: 0 !important;
    box-shadow: none !important;
}
[data-testid="stColumn"]:has(.auth-panel-marker) .stTextInput button span,
[data-testid="column"]:has(.auth-panel-marker) .stTextInput button span {
    display: none !important;
}
.auth-options {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 4px 0 22px 0;
    color: #5E687E;
    font-size: 14px;
}
.auth-forgot, .auth-register-prompt a, .auth-back-link {
    color: #175CFF !important;
    text-decoration: none;
    font-weight: 500;
}
.auth-forgot:hover, .auth-register-prompt a:hover, .auth-back-link:hover {
    text-decoration: underline;
}
[data-testid="stColumn"]:has(.auth-panel-marker) [data-testid="stFormSubmitButton"] button,
[data-testid="column"]:has(.auth-panel-marker) [data-testid="stFormSubmitButton"] button {
    height: 58px;
    border: 0 !important;
    border-radius: 10px;
    color: #FFFFFF !important;
    background: linear-gradient(100deg, #2563F4 0%, #4B62FF 50%, #9846F5 100%) !important;
    box-shadow: 0 10px 25px rgba(76, 89, 255, 0.24);
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.2px;
}
.auth-divider {
    display: flex;
    align-items: center;
    gap: 17px;
    margin: 27px 0 19px 0;
    color: #5F687C;
    font-size: 14px;
    white-space: nowrap;
}
.auth-divider::before, .auth-divider::after {
    content: "";
    height: 1px;
    flex: 1 1 auto;
    background: #D5DAE5;
}
[data-testid="stColumn"]:has(.auth-panel-marker) .stButton > button,
[data-testid="column"]:has(.auth-panel-marker) .stButton > button {
    position: relative;
    height: 56px;
    color: #253453;
    background: #FFFFFF;
    border: 1px solid #C8D0DF;
    border-radius: 10px;
    box-shadow: none;
    font-size: 16px;
    font-weight: 500;
}
[data-testid="stColumn"]:has(.auth-panel-marker) .stButton > button::before,
[data-testid="column"]:has(.auth-panel-marker) .stButton > button::before {
    content: "";
    width: 25px;
    height: 25px;
    margin-right: 12px;
    background: url("__GOOGLE_ICON__") center / contain no-repeat;
}
.auth-register-prompt {
    margin-top: 22px;
    color: #243252;
    font-size: 16px;
    text-align: center;
}
.auth-register-title {
    margin: 0 0 8px 0 !important;
    color: #071644 !important;
    font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: 34px !important;
    font-weight: 800 !important;
    -webkit-text-fill-color: #071644 !important;
}
.auth-register-description { margin-bottom: 24px; color: #697287; }

@media (max-width: 900px) {
    [data-testid="stColumn"]:has(.auth-visual-panel),
    [data-testid="column"]:has(.auth-visual-panel) { display: none !important; }
    [data-testid="stColumn"]:has(.auth-panel-marker),
    [data-testid="column"]:has(.auth-panel-marker) {
        width: 100% !important;
        flex: 1 1 100% !important;
        padding: 36px 28px !important;
    }
    .auth-brand { justify-content: center; margin-bottom: 32px; }
    .auth-wordmark { font-size: 34px; }
    .auth-tagline { font-size: 15px; }
}

/* Badge de clase predicha */
.pred-badge {
    display: inline-block;
    padding: 8px 20px;
    border-radius: 999px;
    font-weight: 800;
    font-size: 18px;
    letter-spacing: 0.2px;
}
</style>
"""
_colores_iconos_css = {
    "informacion": "#F2A100",
    "virtual": "#46546F",
    "presencial": "#46546F",
    "mixta": "#46546F",
    "adjuntar": "#667085",
    "microfono": "#667085",
    "enviar": "#FFFFFF",
    "acuerdos": "#7C3AED",
    "reporte_teal": "#10BFC1",
    "reporte_morado": "#7C3AED",
    "tarea_naranja": "#FF7A1A",
}
for _nombre_icono in ICON_FILES:
    _icono_css = icono_data_uri(
        _nombre_icono,
        _colores_iconos_css.get(_nombre_icono, "#2563EB"),
    )
    ESTILOS_GLOBALES = ESTILOS_GLOBALES.replace(
        f"__ICON_{_nombre_icono.upper()}__", _icono_css
    )
ESTILOS_GLOBALES = ESTILOS_GLOBALES.replace("__GOOGLE_ICON__", GOOGLE_ICON_DATA_URI)
st.markdown(ESTILOS_GLOBALES, unsafe_allow_html=True)


def titulo_pagina(icono: str, texto: str) -> None:
    st.markdown(
        f'<h1 class="page-title"><img src="{ICONOS_AZULES[icono]}" alt=""><span>{escape(texto)}</span></h1>',
        unsafe_allow_html=True,
    )


def subtitulo_pagina(icono: str, texto: str) -> None:
    st.markdown(
        f'<h3 class="section-title"><img src="{ICONOS_AZULES[icono]}" alt=""><span>{escape(texto)}</span></h3>',
        unsafe_allow_html=True,
    )

def registrar_metrica_n8n(endpoint, tiempo_respuesta, estado, codigo_estado=None, reunion_id=None, tamano_respuesta=None, detalles=None):
    """
    Registra métricas de rendimiento de las peticiones a n8n en Supabase.
    
    Args:
        endpoint (str): Nombre del endpoint de n8n (ej: 'resumen_presencial')
        tiempo_respuesta (float): Tiempo de respuesta en segundos
        estado (str): 'éxito', 'error' o 'en_proceso'
        codigo_estado (int, optional): Código de estado HTTP de la respuesta
        reunion_id (str, optional): ID de la reunión relacionada
        tamano_respuesta (int, optional): Tamaño de la respuesta en bytes
        detalles (str, optional): Información adicional o mensaje de error
    """
    try:
        # Preparar los datos a insertar
        metrica = {
            'endpoint': endpoint,
            'tiempo_respuesta': tiempo_respuesta,
            'estado': estado,
            'fecha': datetime.now().isoformat(),
            'codigo_estado': codigo_estado,
            'reunion_id': reunion_id,
            'tamano_respuesta': tamano_respuesta,
            'detalles': detalles
        }
        
        # Insertar en Supabase usando sb_insert
        sb_insert('metricas_n8n', [metrica])
        
    except Exception as e:
        # No hacer nada si falla el registro de métricas
        # para no afectar el flujo principal
        print(f"Error al registrar métrica: {str(e)}")
        pass

# -------- Helpers Supabase --------
def sb_select(table, params):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def sb_insert(table, rows):
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, data=json.dumps(rows), timeout=30)
    r.raise_for_status()
    try:
        return r.json()  # si hay JSON, lo devuelve
    except ValueError:
        return {"status": "success"}  # si viene vacío, igual regresamos OK

def save_resumen(reunion_id: str, resumen_texto: str) -> bool:
    try:
        existentes = sb_select("resumenes", {"select":"id,reunion_id", "reunion_id": f"eq.{reunion_id}"})
        if existentes:
            rid = existentes[0]["id"]
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/resumenes",
                headers={**HEADERS, "Prefer": "return=representation"},
                params={"id": f"eq.{rid}"},
                data=json.dumps({"resumen": resumen_texto})
            )
        else:
            sb_insert("resumenes", [{"reunion_id": reunion_id, "resumen": resumen_texto}])
        return True
    except Exception:
        return False

def hash_pw(pw: str) -> str:
    return bcrypt.hash(pw)

def verify_pw(pw: str, hashed: str) -> bool:
    return bcrypt.verify(pw, hashed)

# -------- Admin helper --------
def is_admin() -> bool:
    try:
        ses = st.session_state.session or {}
        correo = str(ses.get("correo","")).strip().lower()
        if DEMO_MODE and correo == "demo_admin@example.com":
            return True
        return correo in ADMIN_EMAILS
    except Exception:
        return False

# -------- PDF Helper --------
def df_to_pdf_bytes(title: str, df: pd.DataFrame) -> bytes:
    # Configuración de márgenes y estilos
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=30,  # Reducido de 36
        rightMargin=30,  # Reducido de 36
        topMargin=40,
        bottomMargin=30
    )
    
    styles = getSampleStyleSheet()
    
    # Estilo para el texto normal
    normal_style = styles["Normal"]
    normal_style.fontSize = 8  # Tamaño de fuente reducido
    normal_style.leading = 10  # Espaciado entre líneas
    
    # Estilo para encabezados
    header_style = styles["Heading4"]
    header_style.fontSize = 9
    header_style.leading = 12
    header_style.alignment = 1  # Centrado
    
    story = []
    
    # Título
    title_style = styles["Title"]
    title_style.fontSize = 14
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 10))
    
    # Columnas a mostrar
    cols = [c for c in ["id", "nombre", "correo", "nivel_suscripcion", "estado_suscripcion", "fecha_creacion"] 
            if c in df.columns]
    
    # Definir anchos de columna (en puntos)
    col_widths = {
        'id': 40,
        'nombre': 100,
        'correo': 120,
        'nivel_suscripcion': 60,
        'estado_suscripcion': 60,
        'fecha_creacion': 80
    }
    
    # Filtrar y ordenar los anchos según las columnas disponibles
    available_widths = {k: v for k, v in col_widths.items() if k in cols}
    total_width = sum(available_widths.values())
    
    # Ajustar proporcionalmente si el ancho total excede el espacio disponible (aprox. 530 puntos)
    max_width = 530
    if total_width > max_width:
        ratio = max_width / total_width
        available_widths = {k: v * ratio for k, v in available_widths.items()}
    
    # Crear encabezados
    headers = []
    for col in cols:
        if col == 'id':
            headers.append(Paragraph("<b>ID</b>", header_style))
        elif col == 'nombre':
            headers.append(Paragraph("<b>Nombre</b>", header_style))
        elif col == 'correo':
            headers.append(Paragraph("<b>Correo</b>", header_style))
        elif col == 'nivel_suscripcion':
            headers.append(Paragraph("<b>Nivel</b>", header_style))
        elif col == 'estado_suscripcion':
            headers.append(Paragraph("<b>Estado</b>", header_style))
        elif col == 'fecha_creacion':
            headers.append(Paragraph("<b>Fecha</b>", header_style))
    
    data = [headers]
    
    # Agregar filas de datos
    for _, r in df[cols].iterrows():
        row = []
        for col in cols:
            text = str(r.get(col, "")).strip()
            # Usar Paragraph para permitir ajuste de texto
            p = Paragraph(text, normal_style)
            row.append(p)
        data.append(row)
    
    # Crear tabla con anchos personalizados
    table = Table(
        data,
        colWidths=[available_widths[col] for col in cols],
        repeatRows=1
    )
    
    # Aplicar estilos a la tabla
    table_style = [
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), 'Helvetica-Bold'),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        
        # Celdas de datos
        ("FONTNAME", (0, 1), (-1, -1), 'Helvetica'),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        
        # Bordes
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        
        # Colores alternados para filas
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f9f9f9")])
    ]
    
    # Aplicar estilos a la tabla
    table.setStyle(TableStyle(table_style))
    
    # Añadir la tabla al documento
    story.append(table)
    
    # Construir el PDF
    doc.build(story)
    
    # Obtener los bytes del PDF
    pdf_bytes = buf.getvalue()
    buf.close()
    
    return pdf_bytes

def tareas_to_pdf_bytes(title: str, df: pd.DataFrame) -> bytes:
    """
    Genera un PDF con las tareas, optimizado para mostrar información de tareas.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=40,
        bottomMargin=30
    )
    
    styles = getSampleStyleSheet()
    
    # Estilo para el texto normal
    normal_style = styles["Normal"]
    normal_style.fontSize = 7
    normal_style.leading = 9
    
    # Estilo para encabezados
    header_style = styles["Heading4"]
    header_style.fontSize = 8
    header_style.leading = 10
    header_style.alignment = 1  # Centrado
    
    story = []
    
    # Título
    title_style = styles["Title"]
    title_style.fontSize = 14
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 10))
    
    # Columnas a mostrar para tareas
    cols = [c for c in ["reunion_nombre", "descripcion", "asignado_a_correo", "estado", "fecha_vencimiento"] 
            if c in df.columns]
    
    # Definir anchos de columna (en puntos)
    col_widths = {
        'reunion_nombre': 120,
        'descripcion': 180,
        'asignado_a_correo': 100,
        'estado': 60,
        'fecha_vencimiento': 70
    }
    
    # Filtrar anchos según columnas disponibles
    available_widths = {k: v for k, v in col_widths.items() if k in cols}
    total_width = sum(available_widths.values())
    
    # Ajustar proporcionalmente si excede el espacio disponible
    max_width = 530
    if total_width > max_width:
        ratio = max_width / total_width
        available_widths = {k: v * ratio for k, v in available_widths.items()}
    
    # Crear encabezados
    headers = []
    for col in cols:
        if col == 'reunion_nombre':
            headers.append(Paragraph("<b>Reunión</b>", header_style))
        elif col == 'descripcion':
            headers.append(Paragraph("<b>Tarea</b>", header_style))
        elif col == 'asignado_a_correo':
            headers.append(Paragraph("<b>Asignado a</b>", header_style))
        elif col == 'estado':
            headers.append(Paragraph("<b>Estado</b>", header_style))
        elif col == 'fecha_vencimiento':
            headers.append(Paragraph("<b>Vencimiento</b>", header_style))
    
    data = [headers]
    
    # Agregar filas de datos
    for _, r in df[cols].iterrows():
        row = []
        for col in cols:
            text = str(r.get(col, "")).strip()
            # Truncar texto muy largo para descripción
            if col == 'descripcion' and len(text) > 100:
                text = text[:97] + "..."
            p = Paragraph(text, normal_style)
            row.append(p)
        data.append(row)
    
    # Crear tabla con anchos personalizados
    table = Table(
        data,
        colWidths=[available_widths[col] for col in cols],
        repeatRows=1
    )
    
    # Aplicar estilos a la tabla
    table_style = [
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a90e2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), 'Helvetica-Bold'),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        
        # Celdas de datos
        ("FONTNAME", (0, 1), (-1, -1), 'Helvetica'),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        
        # Bordes
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#4a90e2")),
        
        # Colores alternados para filas
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f0f8ff")])
    ]
    
    # Aplicar estilos a la tabla
    table.setStyle(TableStyle(table_style))
    
    # Añadir la tabla al documento
    story.append(table)
    
    # Agregar pie de página con información
    story.append(Spacer(1, 20))
    footer_text = f"Total de tareas: {len(df)} | Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    footer_style = styles["Normal"]
    footer_style.fontSize = 8
    footer_style.textColor = colors.grey
    story.append(Paragraph(footer_text, footer_style))
    
    # Construir el PDF
    doc.build(story)
    
    # Obtener los bytes del PDF
    pdf_bytes = buf.getvalue()
    buf.close()
    
    return pdf_bytes

if "session" not in st.session_state:
    st.session_state.session = None
if "chat" not in st.session_state:
    st.session_state.chat = []

mostrar_login_captura = str(st.query_params.get("mostrar_login", "0")) == "1"

if (
    DEMO_MODE
    and st.session_state.session is None
    and not mostrar_login_captura
    and not st.query_params.get("aceptar_invitacion")
):
    st.session_state.session = {
        "id": "00000000-0000-4000-8000-000000000001",
        "correo": "demo_admin@example.com",
        "nombre": "Administrador de demostración",
        "nivel": "enterprise",
        "estado": "activo",
    }

if DEMO_MODE and st.session_state.session is not None:
    st.warning(
        "**Modo demostración local**　|　Los usuarios y tareas proceden de los datos de prueba del proyecto."
    )

# -------- Auth Views --------
def view_login(mostrar_titulo: bool = True):
    if mostrar_titulo:
        st.subheader("Iniciar sesión")
    with st.form("vincora_login_form"):
        email = st.text_input(
            "Correo electrónico",
            key="login_email",
            placeholder="Correo electrónico",
        )
        pw = st.text_input(
            "Contraseña",
            type="password",
            key="login_pw",
            placeholder="Contraseña",
        )
        st.markdown(
            """
            <div class="auth-options">
                <label><input type="checkbox">&nbsp;&nbsp;Recordarme</label>
                <a class="auth-forgot" href="#">¿Olvidaste tu contraseña?</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
        ingresar = st.form_submit_button(
            "INICIAR SESIÓN",
            type="primary",
            use_container_width=True,
        )
    if ingresar:
        try:
            data = sb_select("usuarios", {"select":"id,correo,nombre,password_hash,nivel_suscripcion,estado_suscripcion", "correo": f"eq.{email}"})
            if not data: st.error("Usuario no encontrado"); return
            u = data[0]
            if not verify_pw(pw, u["password_hash"]): st.error("Credenciales inválidas"); return
            estado = str(u.get("estado_suscripcion") or "activo").strip().lower()
            if estado == "pendiente":
                st.error("Debes aceptar la invitación antes de iniciar sesión.")
                return
            if estado in {"suspendido", "cancelado"}:
                st.error("Esta cuenta no tiene acceso activo.")
                return
            st.session_state.session = {
                "id": u["id"], "correo": u["correo"], "nombre": u["nombre"],
                "nivel": u["nivel_suscripcion"], "estado": u["estado_suscripcion"]
            }
            st.success("¡Bienvenido!")
            st.rerun()
        except Exception as e:
            st.error(str(e))

def view_register(mostrar_titulo: bool = True):
    if mostrar_titulo:
        st.subheader("Registrarse")
    with st.form("vincora_register_form"):
        nombre = st.text_input("Nombre", key="reg_nombre", placeholder="Nombre completo")
        correo = st.text_input("Correo electrónico", key="reg_correo", placeholder="Correo electrónico")
        pw = st.text_input("Contraseña", type="password", key="reg_pw", placeholder="Contraseña")
        crear_cuenta = st.form_submit_button(
            "CREAR CUENTA",
            type="primary",
            use_container_width=True,
        )
    if crear_cuenta:
        if not (nombre and correo and pw): st.warning("Completa todo"); return
        try:
            sb_insert("usuarios", [{
                "nombre": nombre,
                "correo": correo,
                "password_hash": hash_pw(pw),
                "nivel_suscripcion": "basico",
                "estado_suscripcion": "activo"
            }])
            st.success("Cuenta creada. Inicia sesión.")
        except Exception as e:
            st.error(str(e))


def _fecha_iso(valor):
    """Convierte una fecha ISO de Supabase sin fabricar valores ausentes."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def view_aceptar_invitacion(correo: str, token: str) -> None:
    """Activa una invitación pendiente y permite definir la contraseña real."""
    st.markdown('<div class="invite-accept-marker"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="invite-accept-card">
          <div class="auth-brand" style="margin-bottom:24px">
            <img src="{LOGO_DATA_URI}" alt="Logo de VINCORA Meet">
            <div><div class="auth-wordmark" style="font-size:30px">VINCORA</div><div class="auth-tagline" style="font-size:14px">Conecta. Reúnete. Avanza.</div></div>
          </div>
          <h1 class="auth-register-title">Aceptar invitación</h1>
          <div class="auth-register-description">Configura tu contraseña para acceder a VINCORA Meet.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    try:
        coincidencias = sb_select(
            "usuarios",
            {
                "select": "id,correo,nombre,password_hash,estado_suscripcion,fecha_creacion",
                "correo": f"eq.{correo}",
            },
        )
    except Exception as exc:
        st.error(f"No fue posible validar la invitación: {exc}")
        return
    if not coincidencias:
        st.error("La invitación no existe.")
        return
    usuario = coincidencias[0]
    if str(usuario.get("estado_suscripcion") or "").lower() != "pendiente":
        st.info("Esta invitación ya fue utilizada o dejó de estar disponible.")
        st.markdown('<a class="auth-back-link" href="?">Volver al inicio de sesión</a>', unsafe_allow_html=True)
        return
    creada = _fecha_iso(usuario.get("fecha_creacion"))
    ahora = datetime.now(creada.tzinfo) if creada and creada.tzinfo else datetime.now()
    if not creada or ahora - creada > timedelta(days=7):
        st.error("El enlace de invitación venció.")
        return
    try:
        token_valido = verify_pw(token, str(usuario.get("password_hash") or ""))
    except Exception:
        token_valido = False
    if not token_valido:
        st.error("El enlace de invitación no es válido.")
        return
    with st.form("aceptar_invitacion_form"):
        nueva_clave = st.text_input("Nueva contraseña", type="password")
        confirmar_clave = st.text_input("Confirmar contraseña", type="password")
        activar = st.form_submit_button("ACTIVAR CUENTA", type="primary", use_container_width=True)
    if activar:
        if len(nueva_clave) < 8:
            st.warning("La contraseña debe tener al menos 8 caracteres.")
            return
        if nueva_clave != confirmar_clave:
            st.warning("Las contraseñas no coinciden.")
            return
        respuesta = requests.patch(
            f"{SUPABASE_URL}/rest/v1/usuarios",
            headers={**HEADERS, "Prefer": "return=representation"},
            params={"id": f"eq.{usuario['id']}"},
            data=json.dumps({"password_hash": hash_pw(nueva_clave), "estado_suscripcion": "activo"}),
            timeout=30,
        )
        respuesta.raise_for_status()
        st.success("Cuenta activada. Ya puedes iniciar sesión.")
        st.markdown('<a class="auth-back-link" href="?">Ir al inicio de sesión</a>', unsafe_allow_html=True)

# -------- Chat Reuniones --------
@st.cache_data(show_spinner=False)
def leer_csv_cacheado(ruta: str):
    """Los CSV de resultados son artefactos inmutables del entrenamiento;
    cachearlos evita releerlos del disco en cada rerun de Streamlit."""
    return pd.read_csv(ruta)


def parece_espanol(texto):
    """Heurística ligera para detectar texto en español antes de traducirlo
    al inglés (el modelo fue entrenado con MRDA, un corpus en inglés)."""
    t = f" {texto.lower()} "
    if re.search(r"[ñ¿¡áéíóúü]", t):
        return True
    palabras = (
        " el ", " la ", " los ", " las ", " un ", " una ", " que ", " de ",
        " para ", " por ", " con ", " del ", " esta ", " este ", " puedes ",
        " podemos ", " necesito ", " enviar ", " informe ", " reunion ",
    )
    return sum(1 for p in palabras if p in t) >= 2


DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6,
}
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def interpretar_solicitud_reunion(texto):
    """Extrae tema, fecha, hora, duración, tipo, dirección e invitados de una
    solicitud en lenguaje natural. Permite crear reuniones desde el chat sin el
    flujo n8n (que requiere credenciales externas de OpenAI/Zoom/Gmail)."""
    t = texto.strip()
    bajo = t.lower()
    ahora = datetime.now()

    invitados = re.findall(r"[\w.+-]+@[\w.-]+\.\w+", t)

    tipo = "virtual"
    if "presencial" in bajo:
        tipo = "presencial"
    if "mixta" in bajo or "híbrida" in bajo or "hibrida" in bajo:
        tipo = "mixta"

    direccion = None
    m = re.search(r"direcci[oó]n\s+(?:es\s+)?(.+?)(?:,\s*y\s|[;\n]|\.\s*$|$)", t, re.IGNORECASE)
    if m:
        direccion = m.group(1).strip().rstrip(",.") or None
    if tipo == "virtual":
        direccion = None

    fecha = None
    if "pasado mañana" in bajo or "pasado manana" in bajo:
        fecha = (ahora + timedelta(days=2)).date()
    elif "mañana" in bajo or "manana" in bajo:
        fecha = (ahora + timedelta(days=1)).date()
    elif re.search(r"\bhoy\b", bajo):
        fecha = ahora.date()
    if fecha is None:
        m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", bajo)
        if m:
            try:
                fecha = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
            except ValueError:
                fecha = None
    if fecha is None:
        m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", bajo)
        if m:
            anio = int(m.group(3)) if m.group(3) else ahora.year
            if anio < 100:
                anio += 2000
            try:
                fecha = datetime(anio, int(m.group(2)), int(m.group(1))).date()
            except ValueError:
                fecha = None
    if fecha is None:
        m = re.search(r"\b(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")(?:\s+(?:de|del)\s+(\d{4}))?", bajo)
        if m:
            anio = int(m.group(3)) if m.group(3) else ahora.year
            try:
                fecha = datetime(anio, MESES[m.group(2)], int(m.group(1))).date()
                if fecha < ahora.date() and not m.group(3):
                    fecha = datetime(anio + 1, MESES[m.group(2)], int(m.group(1))).date()
            except ValueError:
                fecha = None
    if fecha is None:
        for nombre, idx in DIAS_SEMANA.items():
            if re.search(r"\b" + nombre + r"\b", bajo):
                delta = (idx - ahora.weekday()) % 7
                fecha = (ahora + timedelta(days=delta or 7)).date()
                break
    if fecha is None:
        fecha = (ahora + timedelta(days=1)).date()

    hora, minuto = 9, 0
    m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?", bajo)
    if m:
        hora, minuto = int(m.group(1)), int(m.group(2))
        if (m.group(3) or "").startswith("p") and hora < 12:
            hora += 12
    else:
        m = re.search(r"a\s+las?\s+(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)?", bajo)
        if m:
            hora = int(m.group(1))
            suf = m.group(2) or ""
            if suf.startswith("p") and hora < 12:
                hora += 12
            elif not suf and 1 <= hora <= 7:
                hora += 12  # "a las 3" se interpreta como horario laboral (15:00)
    if not (0 <= hora <= 23):
        hora = 9
    if not (0 <= minuto <= 59):
        minuto = 0

    duracion = 60
    m = re.search(r"(\d+)\s*(?:min\b|minutos)", bajo)
    if m:
        duracion = int(m.group(1))
    elif "hora y media" in bajo:
        duracion = 90
    elif "media hora" in bajo:
        duracion = 30
    else:
        m = re.search(r"(?:de|dura|durante)\s+(\d+)\s*horas?\b", bajo)
        if m:
            duracion = int(m.group(1)) * 60
    duracion = max(5, min(duracion, 480))

    corte = re.compile(
        r"\b(?:mañana|manana|hoy|pasado\s+mañana|a\s+las?\b|el\s+\d|\d{1,2}[:/]"
        r"|lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo"
        r"|de\s+\d+\s*(?:min|hora)|dura|por\s+favor|invita|la\s+reuni[oó]n\s+es|direcci[oó]n)",
        re.IGNORECASE,
    )
    tema = None
    m = re.search(r"(?:sobre|acerca de|para hablar de|tema[:\s])\s*(.+)", t, re.IGNORECASE)
    if not m:
        m = re.search(r"reuni[oó]n\s+(?:de\s+|con\s+|para\s+)?(.+)", t, re.IGNORECASE)
    if m:
        tema = corte.split(m.group(1))[0]
        # quitar conectores colgando al final ("... para", "... el")
        tema = re.sub(r"(?:\s+(?:para|de|del|el|la|los|las|en|con|y|a|que))+\s*$", "", tema, flags=re.IGNORECASE)
    if not tema or not tema.strip(" .,;:"):
        tema = "Reunión creada por chat"
    tema = re.sub(r"\s+", " ", tema).strip(" .,;:")
    tema = tema[0].upper() + tema[1:] if tema else "Reunión creada por chat"

    return {
        "tema": tema[:200],
        "fecha_inicio": f"{fecha.isoformat()}T{hora:02d}:{minuto:02d}:00",
        "duracion_minutos": duracion,
        "tipo": tipo,
        "direccion": direccion,
        "invitados": list(dict.fromkeys(invitados)),
    }


SUGERENCIAS_CHAT = {
    "chat_sugerencia_manana": "Programa una reunión mañana a las 11:00 a. m. por 45 minutos.",
    "chat_sugerencia_semanal": "Programa una reunión semanal de equipo el próximo lunes a las 9:00 a. m. por 60 minutos.",
    "chat_sugerencia_invitados": "Programa una reunión mañana a las 10:00 a. m. e invita a ana@empresa.com y juan@empresa.com.",
}


def cargar_sugerencia_chat(texto: str) -> None:
    """Coloca una sugerencia editable en el cuadro principal del chat."""
    st.session_state["vincora_chat_prompt"] = texto


def limpiar_chat() -> None:
    """Restablece la conversación y todas las opciones de la reunión."""
    st.session_state.chat = []
    st.session_state["quick_email"] = ""
    st.session_state["direccion_reunion"] = ""
    st.session_state["tipo_reunion"] = "Virtual"
    st.session_state["vincora_chat_prompt"] = ""
    st.session_state["chat_reset_pending"] = False


def navegar_a(pagina: str) -> None:
    """Cambia la opción real del menú lateral desde una tarjeta del inicio."""
    st.session_state["main_navigation"] = pagina


def preparar_chat_inicio(mensaje: str) -> None:
    """Abre Chat con una solicitud editable acorde a la acción elegida."""
    st.session_state["vincora_chat_prompt"] = mensaje
    navegar_a("Chat")


def _fecha_local_inicio(valor):
    if not valor:
        return None
    try:
        fecha = pd.to_datetime(valor, utc=True, errors="coerce")
        if pd.isna(fecha):
            return None
        return fecha.to_pydatetime().astimezone()
    except Exception:
        return None


def _hora_inicio(fecha) -> str:
    hora = fecha.hour % 12 or 12
    periodo = "a. m." if fecha.hour < 12 else "p. m."
    return f"{hora}:{fecha.minute:02d} {periodo}"


def _momento_inicio(fecha) -> str:
    hoy = datetime.now().astimezone().date()
    if fecha.date() == hoy:
        prefijo = "Hoy"
    elif fecha.date() == hoy + timedelta(days=1):
        prefijo = "Mañana"
    else:
        prefijo = fecha.strftime("%d/%m/%Y")
    return f"{prefijo} · {_hora_inicio(fecha)}"


def _fecha_corta_inicio(valor) -> str:
    fecha = _fecha_local_inicio(valor)
    if not fecha:
        return "Sin fecha"
    meses = ["ene.", "feb.", "mar.", "abr.", "may.", "jun.", "jul.", "ago.", "sep.", "oct.", "nov.", "dic."]
    return f"{fecha.day} {meses[fecha.month - 1]} {fecha.year}"


def _iniciales_inicio(texto: str) -> str:
    base = str(texto or "Usuario").split("@", 1)[0].replace(".", " ").replace("_", " ")
    partes = [p for p in base.split() if p]
    return "".join(p[0] for p in partes[:2]).upper() or "U"


def _url_inicio(valor) -> str | None:
    url = str(valor or "").strip()
    return url if url.startswith(("https://", "http://")) else None


def _avatares_inicio(participantes, usuarios_correo) -> str:
    avatares = []
    for participante in participantes[:5]:
        correo = str(participante.get("correo") or "")
        nombre = usuarios_correo.get(correo.lower(), {}).get("nombre") or correo
        avatares.append(
            f'<span class="home-mini-avatar" title="{escape(str(nombre), quote=True)}">{escape(_iniciales_inicio(nombre))}</span>'
        )
    restantes = max(0, len(participantes) - 5)
    if restantes:
        avatares.append(f'<span class="home-mini-avatar home-avatar-more">+{restantes}</span>')
    return "".join(avatares)


def _actualizar_tarea_inicio(tarea_id: str, clave: str, estado_anterior: str) -> None:
    nuevo_estado = "completada" if st.session_state.get(clave) else (
        estado_anterior if estado_anterior != "completada" else "pendiente"
    )
    try:
        respuesta = requests.patch(
            f"{SUPABASE_URL}/rest/v1/tareas",
            headers={**HEADERS, "Prefer": "return=representation"},
            params={"id": f"eq.{tarea_id}"},
            data=json.dumps({"estado": nuevo_estado}),
            timeout=30,
        )
        respuesta.raise_for_status()
        st.toast("Tarea actualizada")
    except Exception as exc:
        st.toast(f"No se pudo actualizar: {exc}")


@st.dialog("Unirse con código")
def _dialogo_unirse_inicio() -> None:
    st.caption("Ingresa el código de una reunión registrada en VINCORA.")
    codigo = st.text_input("Código de reunión", key="home_join_code", placeholder="Ej.: demo-zoom-001")
    if st.button("Buscar reunión", type="primary", use_container_width=True, key="home_join_search"):
        try:
            coincidencias = sb_select(
                "reuniones",
                {"select": "id,tema,id_externo,join_url,start_url,tipo,direccion", "id_externo": f"eq.{codigo.strip()}"},
            )
            if not coincidencias:
                coincidencias = sb_select(
                    "reuniones",
                    {"select": "id,tema,id_externo,join_url,start_url,tipo,direccion", "id": f"eq.{codigo.strip()}"},
                )
            st.session_state["home_join_result"] = coincidencias[0] if coincidencias else None
            st.session_state["home_join_searched"] = True
        except Exception as exc:
            st.write(f"No se pudo consultar la reunión: {exc}")
    if st.session_state.get("home_join_searched"):
        reunion = st.session_state.get("home_join_result")
        if not reunion:
            st.write("No encontramos una reunión con ese código.")
        else:
            st.markdown(f"**{escape(str(reunion.get('tema') or 'Reunión'))}**")
            enlace = _url_inicio(reunion.get("join_url") or reunion.get("start_url"))
            if enlace:
                st.link_button(
                    "Continuar a sala previa", f"?sala_previa={quote(str(reunion.get('id') or ''))}",
                    type="primary", use_container_width=True,
                )
            else:
                st.write(f"Reunión {reunion.get('tipo') or ''}. Dirección: {reunion.get('direccion') or 'por confirmar'}")


@st.dialog("Compartir pantalla")
def _dialogo_compartir_inicio() -> None:
    st.caption("El navegador solicitará permiso antes de mostrar tu pantalla.")
    import streamlit.components.v1 as components
    components.html(
        """
        <style>
          body{margin:0;font-family:Segoe UI,Arial;color:#0b183a}
          button{width:100%;height:46px;border:0;border-radius:10px;color:white;font-weight:700;background:linear-gradient(120deg,#176bf7,#8b3ff3);cursor:pointer}
          video{display:none;width:100%;margin-top:12px;border-radius:10px;background:#0b183a;max-height:250px}
          p{font-size:12px;color:#667491;text-align:center}
        </style>
        <button id="share">Comenzar a compartir</button>
        <video id="preview" autoplay muted></video>
        <p id="status">La vista previa aparecerá aquí.</p>
        <script>
          const button=document.getElementById('share');
          const video=document.getElementById('preview');
          const status=document.getElementById('status');
          button.onclick=async()=>{
            try{
              const stream=await navigator.mediaDevices.getDisplayMedia({video:true,audio:false});
              video.srcObject=stream; video.style.display='block';
              button.textContent='Detener pantalla'; status.textContent='Tu pantalla se está compartiendo en la vista previa.';
              button.onclick=()=>{stream.getTracks().forEach(t=>t.stop());video.style.display='none';status.textContent='La pantalla dejó de compartirse.';};
              stream.getVideoTracks()[0].addEventListener('ended',()=>{video.style.display='none';status.textContent='La pantalla dejó de compartirse.';});
            }catch(error){status.textContent='No se concedió permiso para compartir la pantalla.';}
          };
        </script>
        """,
        height=350,
    )


def view_inicio():
    """Panel de inicio conectado a las tablas reales de VINCORA."""
    st.markdown('<div class="home-page-marker"></div>', unsafe_allow_html=True)
    sesion = st.session_state.session or {}
    nombre_completo = str(sesion.get("nombre") or "Usuario")
    primer_nombre = "Carlos" if DEMO_MODE else (nombre_completo.split()[0] if nombre_completo.split() else "Usuario")
    iniciales = _iniciales_inicio(nombre_completo)

    st.markdown(
        f"""
        <div class="home-header">
          <div>
            <h1>Buenos días, {escape(primer_nombre)}</h1>
            <p>Organiza tus reuniones y mantén cada acuerdo bajo control.</p>
          </div>
          <div class="home-profile">
            <a href="?pagina=Tareas" target="_self" class="home-notification" aria-label="Ver tareas"></a>
            <div class="home-avatar" title="{escape(nombre_completo, quote=True)}">{escape(iniciales)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    acciones = st.columns(4, gap="medium")
    with acciones[0]:
        st.button(
            "Nueva reunión",
            key="home_action_new",
            use_container_width=True,
            on_click=preparar_chat_inicio,
            args=("Inicia una reunión virtual ahora.",),
        )
    with acciones[1]:
        if st.button("Unirse con código", key="home_action_join", use_container_width=True):
            st.session_state["home_join_open"] = True
    with acciones[2]:
        st.button(
            "Programar reunión",
            key="home_action_schedule",
            use_container_width=True,
            on_click=preparar_chat_inicio,
            args=("Programa una reunión.",),
        )
    with acciones[3]:
        if st.button("Compartir pantalla", key="home_action_share", use_container_width=True):
            st.session_state["home_share_open"] = True

    if st.session_state.pop("home_join_open", False):
        _dialogo_unirse_inicio()
    if st.session_state.pop("home_share_open", False):
        _dialogo_compartir_inicio()

    try:
        reuniones = sb_select(
            "reuniones",
            {"select": "id,tema,fecha_inicio,duracion_minutos,join_url,start_url,estado,tipo,direccion", "order": "fecha_inicio.asc"},
        )
    except Exception:
        reuniones = []
    try:
        participantes = sb_select(
            "participantes",
            {"select": "id,reunion_id,usuario_id,correo,rol,estado_invitacion"},
        )
    except Exception:
        participantes = []
    try:
        tareas = sb_select(
            "tareas",
            {"select": "id,reunion_id,descripcion,asignado_a_correo,estado,fecha_vencimiento,fecha_creacion"},
        )
    except Exception:
        tareas = []
    try:
        resumenes = sb_select(
            "resumenes",
            {"select": "id,reunion_id,resumen,fecha_creacion", "order": "fecha_creacion.desc"},
        )
    except Exception:
        resumenes = []
    try:
        usuarios = sb_select("usuarios", {"select": "id,nombre,correo"})
    except Exception:
        usuarios = []

    usuarios_correo = {str(u.get("correo") or "").lower(): u for u in usuarios}
    participantes_reunion = {}
    for participante in participantes:
        participantes_reunion.setdefault(str(participante.get("reunion_id")), []).append(participante)
    reuniones_id = {str(r.get("id")): r for r in reuniones}

    ahora = datetime.now().astimezone()
    inicio_semana = ahora.date() - timedelta(days=ahora.weekday())
    fin_semana = inicio_semana + timedelta(days=7)
    reuniones_fecha = [(r, _fecha_local_inicio(r.get("fecha_inicio"))) for r in reuniones]
    proximas = [
        (r, fecha) for r, fecha in reuniones_fecha
        if fecha and fecha >= ahora and str(r.get("estado") or "").lower() != "cancelada"
    ][:2]

    def esta_semana(valor) -> bool:
        fecha = _fecha_local_inicio(valor)
        return bool(fecha and inicio_semana <= fecha.date() < fin_semana)

    reuniones_semana = sum(1 for _, fecha in reuniones_fecha if fecha and inicio_semana <= fecha.date() < fin_semana)
    informes_semana = sum(1 for r in resumenes if esta_semana(r.get("fecha_creacion")))
    acuerdos_semana = sum(1 for t in tareas if esta_semana(t.get("fecha_creacion")))
    pendientes = sum(1 for t in tareas if str(t.get("estado") or "pendiente").lower() != "completada")
    seguimiento = 0
    for tarea in tareas:
        vencimiento = _fecha_local_inicio(tarea.get("fecha_vencimiento"))
        if str(tarea.get("estado") or "").lower() != "completada" and vencimiento and vencimiento.date() <= ahora.date():
            seguimiento += 1

    filas_reuniones = []
    for indice, (reunion, fecha) in enumerate(proximas):
        part = participantes_reunion.get(str(reunion.get("id")), [])
        enlace = _url_inicio(reunion.get("start_url") or reunion.get("join_url"))
        boton_inicio = (
            f'<a class="home-start-button" href="?sala_previa={quote(str(reunion.get("id") or ""))}" target="_self">Iniciar</a>'
            if enlace else ""
        )
        filas_reuniones.append(
            f'<div class="home-meeting-row">'
            f'<span class="home-meeting-dot"></span><span class="home-meeting-calendar"></span>'
            f'<div class="home-meeting-title">{escape(str(reunion.get("tema") or "Reunión sin tema"))}</div>'
            f'<div class="home-meeting-time">{escape(_momento_inicio(fecha))} · {int(reunion.get("duracion_minutos") or 0)} min</div>'
            f'<div class="home-meeting-meta"><div class="home-avatar-stack">{_avatares_inicio(part, usuarios_correo)}</div>'
            f'<span class="home-participant-count">{len(part)} participantes</span></div>'
            f'<div class="home-meeting-actions">{boton_inicio}<a class="home-more-button" href="?pagina=Reuniones" target="_self" aria-label="Ver reunión"></a></div>'
            f'</div>'
        )
    if not filas_reuniones:
        filas_reuniones.append('<div style="padding:48px 20px;color:#71809B;text-align:center">No hay próximas reuniones programadas.</div>')

    st.markdown(
        f"""
        <div class="home-main-grid">
          <section class="home-panel home-panel-padding">
            <div class="home-panel-head"><span class="home-panel-title">Próximas reuniones</span><a class="home-link home-no-arrow" href="?pagina=Reuniones" target="_self">Ver calendario</a></div>
            {''.join(filas_reuniones)}
            <div class="home-card-footer"><a class="home-link" href="?pagina=Reuniones" target="_self">Ver todas las reuniones</a></div>
          </section>
          <section class="home-panel home-panel-padding">
            <div class="home-panel-head"><span class="home-panel-title">Resumen de esta semana</span></div>
            <div class="home-summary-list">
              <div class="home-summary-row"><span class="home-summary-icon meetings"></span><strong class="home-summary-value">{reuniones_semana}</strong><span class="home-summary-label">reuniones</span></div>
              <div class="home-summary-row"><span class="home-summary-icon reports"></span><strong class="home-summary-value">{informes_semana}</strong><span class="home-summary-label">informes generados</span></div>
              <div class="home-summary-row"><span class="home-summary-icon agreements"></span><strong class="home-summary-value">{acuerdos_semana}</strong><span class="home-summary-label">acuerdos</span></div>
              <div class="home-summary-row"><span class="home-summary-icon tasks"></span><strong class="home-summary-value">{pendientes}</strong><span class="home-summary-label">tareas pendientes</span></div>
            </div>
            <div class="home-card-footer"><a class="home-link" href="?pagina=Métricas" target="_self">Ver resumen completo</a></div>
          </section>
        </div>
        """,
        unsafe_allow_html=True,
    )

    inferior = st.columns([1.05, 1.35, .75], gap="medium")
    with inferior[0]:
        with st.container(key="home_reports"):
            filas_informes = []
            for indice, resumen in enumerate(resumenes[:2]):
                reunion = reuniones_id.get(str(resumen.get("reunion_id")), {})
                fecha = _fecha_local_inicio(resumen.get("fecha_creacion"))
                tiempo = f"{_momento_inicio(fecha)}" if fecha else "Fecha no disponible"
                clase = "approved" if indice == 0 else "review"
                estado = "Aprobado" if indice == 0 else "En revisión"
                filas_informes.append(
                    f"""
                    <div class="home-report-row">
                      <span class="home-report-icon {clase}"></span>
                      <div class="home-report-title">{escape(str(reunion.get('tema') or 'Informe de reunión'))}</div>
                      <div class="home-report-time">{escape(tiempo)}</div>
                      <span class="home-status {clase}">{estado}</span>
                      <a class="home-report-more" href="?pagina=Resumen%20de%20reuniones" target="_self" aria-label="Abrir informe"></a>
                    </div>
                    """
                )
            if not filas_informes:
                filas_informes.append('<div style="padding:55px 10px;color:#71809B;text-align:center">No hay informes generados.</div>')
            st.markdown(
                f'<div class="home-panel-head"><span class="home-panel-title">Informes recientes</span><a class="home-link home-no-arrow" href="?pagina=Resumen%20de%20reuniones" target="_self">Ver todos</a></div>{"".join(filas_informes)}',
                unsafe_allow_html=True,
            )
    with inferior[1]:
        with st.container(key="home_tasks"):
            st.markdown(
                '<div class="home-panel-head"><span class="home-panel-title">Mis tareas</span><a class="home-link home-no-arrow" href="?pagina=Tareas" target="_self">Ver todas</a></div>',
                unsafe_allow_html=True,
            )
            correo_actual = str(sesion.get("correo") or "").lower()
            ordenadas = sorted(
                tareas,
                key=lambda t: (_fecha_local_inicio(t.get("fecha_vencimiento")) or ahora + timedelta(days=3650)),
            )
            propias = [t for t in ordenadas if str(t.get("asignado_a_correo") or "").lower() == correo_actual]
            visibles = propias[:3]
            if len(visibles) < 3:
                usados = {str(t.get("id")) for t in visibles}
                visibles.extend([t for t in ordenadas if str(t.get("id")) not in usados][: 3 - len(visibles)])
            if not visibles:
                st.markdown('<div style="padding:55px 10px;color:#71809B;text-align:center">No tienes tareas asignadas.</div>', unsafe_allow_html=True)
            for indice, tarea in enumerate(visibles):
                estado = str(tarea.get("estado") or "pendiente").lower()
                progreso = 100 if estado == "completada" else (40 if estado == "en_progreso" else 20)
                clave = f"home_task_check_{str(tarea.get('id')).replace('-', '_')}"
                asignado = str(tarea.get("asignado_a_correo") or "No asignado")
                nombre_asignado = usuarios_correo.get(asignado.lower(), {}).get("nombre") or asignado.split("@", 1)[0].replace(".", " ").title()
                with st.container(key=f"home_task_row_{indice}"):
                    columnas_tarea = st.columns([.10, 2.75, .34, .78], gap="small")
                    with columnas_tarea[0]:
                        st.checkbox(
                            "Completada",
                            value=estado == "completada",
                            key=clave,
                            label_visibility="collapsed",
                            on_change=_actualizar_tarea_inicio,
                            args=(str(tarea.get("id")), clave, estado),
                        )
                    with columnas_tarea[1]:
                        st.markdown(
                            f'<div class="home-task-text">{escape(str(tarea.get("descripcion") or "Sin descripción"))}</div><div class="home-task-meta">{escape(nombre_asignado)} · {_fecha_corta_inicio(tarea.get("fecha_vencimiento"))}</div>',
                            unsafe_allow_html=True,
                        )
                    with columnas_tarea[2]:
                        st.markdown(f'<span class="home-mini-avatar" style="margin:0">{escape(_iniciales_inicio(nombre_asignado))}</span>', unsafe_allow_html=True)
                    with columnas_tarea[3]:
                        st.markdown(
                            f'<div class="home-task-progress">{progreso}%<div class="home-progress-track"><div class="home-progress-fill" style="width:{progreso}%"></div></div></div>',
                            unsafe_allow_html=True,
                        )
    with inferior[2]:
        with st.container(key="home_ai"):
            st.markdown(
                f"""
                <div class="home-ai-brand"><img src="{LOGO_DATA_URI}" alt="VINCORA IA">VINCORA IA</div>
                <div class="home-ai-ring"><span>{seguimiento}</span></div>
                <div class="home-ai-copy">acuerdos requieren<br>seguimiento</div>
                <div class="home-ai-link"><a class="home-link" href="?pagina=Inteligencia%20artificial" target="_self">Ver sugerencias</a></div>
                """,
                unsafe_allow_html=True,
            )


def view_chat():
    st.markdown('<div class="chat-page-marker"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="chat-page-heading">
            <img src="{ICONOS_AZULES['chat_sonrisa']}" alt="">
            <h1>Crear reunión por chat</h1>
        </div>
        <div class="chat-page-description">Describe tu reunión y VINCORA se encargará de organizarla.</div>
        """,
        unsafe_allow_html=True,
    )

    # Reset seguro de opciones antes de instanciar widgets
    if st.session_state.get("chat_reset_pending"):
        st.session_state["quick_email"] = ""
        st.session_state["direccion_reunion"] = ""
        st.session_state["tipo_reunion"] = "Virtual"
        st.session_state["chat_reset_pending"] = False

    # Tarjeta de opciones del diseño aprobado.
    with st.container(border=True):
        st.markdown('<div class="chat-options-marker">Opciones de reunión</div>', unsafe_allow_html=True)
        col_tipo, col_separador, col_inv, col_limpiar = st.columns([1.28, 0.05, 1.22, 0.38])
        with col_tipo:
            st.markdown('<div class="chat-field-title">Tipo de reunión</div>', unsafe_allow_html=True)
            st.radio(
                "Tipo de reunión",
                ["Virtual", "Presencial", "Mixta"],
                horizontal=True,
                key="tipo_reunion",
                label_visibility="collapsed",
            )
        with col_separador:
            st.markdown('<div class="chat-options-divider"></div>', unsafe_allow_html=True)
        with col_inv:
            st.markdown(
                '<div class="chat-field-title">Invitados</div><div class="chat-field-help">Emails separados por comas</div>',
                unsafe_allow_html=True,
            )
            st.text_input(
                "Invitados",
                placeholder="ana@empresa.com, juan@empresa.com",
                key="quick_email",
                label_visibility="collapsed",
            )
        with col_limpiar:
            st.markdown('<div class="chat-clear-spacer"></div>', unsafe_allow_html=True)
            st.button(
                "Limpiar",
                key="chat_limpiar",
                use_container_width=True,
                on_click=limpiar_chat,
            )
        if st.session_state.get("tipo_reunion") in ["Presencial", "Mixta"]:
            st.text_input(
                "Dirección del lugar",
                placeholder="Av. Ejemplo 123, Sala A",
                key="direccion_reunion",
            )

    # Estado inicial y accesos rápidos. Cada botón rellena el campo inferior.
    if not st.session_state.chat:
        st.markdown(
            f"""
            <div class="chat-empty-state">
                <div class="chat-empty-logo"><img src="{LOGO_DATA_URI}" alt="Logo de VINCORA Meet"></div>
                <h2>¿Qué reunión deseas organizar?</h2>
                <p>Escribe tu solicitud o utiliza una sugerencia para comenzar.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        sug_1, sug_2, sug_3 = st.columns(3)
        with sug_1:
            st.button(
                "Programar reunión para mañana",
                key="chat_sugerencia_manana",
                use_container_width=True,
                on_click=cargar_sugerencia_chat,
                args=(SUGERENCIAS_CHAT["chat_sugerencia_manana"],),
            )
        with sug_2:
            st.button(
                "Reunión semanal de equipo",
                key="chat_sugerencia_semanal",
                use_container_width=True,
                on_click=cargar_sugerencia_chat,
                args=(SUGERENCIAS_CHAT["chat_sugerencia_semanal"],),
            )
        with sug_3:
            st.button(
                "Invitar participantes",
                key="chat_sugerencia_invitados",
                use_container_width=True,
                on_click=cargar_sugerencia_chat,
                args=(SUGERENCIAS_CHAT["chat_sugerencia_invitados"],),
            )
        st.markdown(
            '<div class="chat-example">Ejemplo: Programa una reunión mañana a las 11:00 a. m. por 45 minutos.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="chat-history-marker"></div>', unsafe_allow_html=True)
        for role, text in st.session_state.chat:
            with st.chat_message(role):
                st.markdown(text)

    # Campo único funcional: texto, adjuntos y grabación desde el micrófono.
    with st.container():
        st.markdown('<div class="chat-composer-marker"></div>', unsafe_allow_html=True)
        submission = st.chat_input(
            "Escribe tu solicitud...",
            key="vincora_chat_prompt",
            accept_file=True,
            file_type=["pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"],
            accept_audio=True,
            audio_sample_rate=16000,
            height="content",
        )
    st.markdown(
        '<div class="chat-disclaimer">VINCORA puede cometer errores. Verifica la información antes de confirmar.</div>',
        unsafe_allow_html=True,
    )

    if submission:
        prompt = str(getattr(submission, "text", "") or "").strip()
        archivos = list(getattr(submission, "files", []) or [])
        audio = getattr(submission, "audio", None)

        if not prompt:
            medios = []
            if archivos:
                medios.append("archivos: " + ", ".join(a.name for a in archivos))
            if audio is not None:
                medios.append("una grabación de voz")
            recibido = "Contenido recibido" + (f" ({'; '.join(medios)})" if medios else "") + "."
            respuesta = "Añade por escrito la fecha, hora, duración y tema para poder crear la reunión."
            st.session_state.chat.extend([("user", recibido), ("assistant", respuesta)])
            st.rerun()
            return

        extras = []
        if 'tipo_reunion' in st.session_state and st.session_state.tipo_reunion:
            extras.append(f"la reunión es de tipo {st.session_state.tipo_reunion.lower()}")
        if 'quick_email' in st.session_state and st.session_state.quick_email:
            raw = st.session_state.quick_email
            candidatos = [e.strip() for e in re.split(r"[,\n\s]+", raw) if e.strip()]
            if candidatos:
                if len(candidatos) == 1:
                    invitados_texto = candidatos[0]
                elif len(candidatos) == 2:
                    invitados_texto = f"{candidatos[0]} y {candidatos[1]}"
                else:
                    invitados_texto = ", ".join(candidatos[:-1]) + f" y {candidatos[-1]}"
                extras.append(f"invita también a {invitados_texto}")
        if st.session_state.get('direccion_reunion'):
            extras.append(f"la dirección es {st.session_state.direccion_reunion}")
        if archivos:
            extras.append("se adjuntaron los archivos " + ", ".join(a.name for a in archivos))
        if audio is not None:
            extras.append("se adjuntó una grabación de voz")
        final_prompt = prompt if not extras else f"{prompt}. Por favor, {', y '.join(extras)}."

        st.session_state.chat.append(("user", final_prompt))
        with st.chat_message("user"):
            st.markdown(final_prompt)

        # Sin webhook n8n configurado: interpretar la solicitud y crear la
        # reunión directamente en Supabase (sin Zoom/correo automáticos).
        if not N8N_URL:
            inicio = time.time()
            try:
                datos = interpretar_solicitud_reunion(final_prompt)
                fila = {
                    "creador_id": st.session_state.session["id"],
                    "tema": datos["tema"],
                    "fecha_inicio": datos["fecha_inicio"],
                    "duracion_minutos": datos["duracion_minutos"],
                    "proveedor": "manual",
                    "estado": "programada",
                    "tipo": datos["tipo"],
                    "direccion": datos["direccion"],
                }
                creada = requests.post(
                    f"{SUPABASE_URL}/rest/v1/reuniones",
                    headers={**HEADERS, "Prefer": "return=representation"},
                    data=json.dumps([fila]),
                    timeout=30,
                )
                creada.raise_for_status()
                reunion_id = creada.json()[0]["id"]

                invitados_ok = []
                if datos["invitados"]:
                    try:
                        sb_insert("participantes", [
                            {
                                "reunion_id": reunion_id,
                                "correo": c,
                                "rol": "participante",
                                "estado_invitacion": "enviado",
                            }
                            for c in datos["invitados"]
                        ])
                        invitados_ok = datos["invitados"]
                    except Exception:
                        pass

                registrar_metrica_n8n(
                    endpoint="crear_reunion_chat_local",
                    tiempo_respuesta=time.time() - inicio,
                    estado="éxito",
                    codigo_estado=200,
                    reunion_id=reunion_id,
                    detalles="Creación local sin flujo n8n",
                )

                lineas = [
                    f"Reunión creada: **{datos['tema']}**",
                    f"- Fecha/hora: {datos['fecha_inicio'].replace('T', ' ')}",
                    f"- Duración: {datos['duracion_minutos']} minutos",
                    f"- Tipo: {datos['tipo']}",
                ]
                if datos["direccion"]:
                    lineas.append(f"- Dirección: {datos['direccion']}")
                if invitados_ok:
                    lineas.append(f"- Invitados registrados: {', '.join(invitados_ok)}")
                if datos["tipo"] != "presencial":
                    lineas.append("- Enlace de videollamada: pendiente (la integración n8n/Zoom no está activa)")
                lineas.append("\nPuede verla en la pestaña **Reuniones**.")
                resumen = "\n".join(lineas)
                st.session_state.chat.append(("assistant", resumen))
                with st.chat_message("assistant"):
                    st.markdown(resumen)
            except Exception as e:
                registrar_metrica_n8n(
                    endpoint="crear_reunion_chat_local",
                    tiempo_respuesta=time.time() - inicio,
                    estado="error",
                    detalles=str(e)[:200],
                )
                err = f"No pude crear la reunión: {e}"
                st.session_state.chat.append(("assistant", err))
                with st.chat_message("assistant"):
                    st.error(err)
            st.session_state["chat_reset_pending"] = True
            st.rerun()
            return

        # Iniciar medición de tiempo
        inicio = time.time()
        payload = {"creador_id": st.session_state.session["id"], "mensaje": final_prompt}
        try:
            resp = requests.post(N8N_URL, json=payload, timeout=90)
            tiempo_respuesta = time.time() - inicio
            # Registrar métrica de la petición
            registrar_metrica_n8n(
                endpoint="crear_reunion_chat",
                tiempo_respuesta=tiempo_respuesta,
                estado="éxito" if resp.status_code == 200 else "error",
                codigo_estado=resp.status_code,
                detalles=f"Tiempo de respuesta: {tiempo_respuesta:.2f}s"
            )
            
            if resp.status_code == 200:
                data = resp.json()
                # Construir resumen según tipo/datos
                resumen_lines = [
                    f"Reunión creada: **{data.get('meeting', {}).get('tema','')}**",
                    f"- Fecha/hora: {data.get('meeting', {}).get('fecha','')}",
                ]
                # Añadir tipo/dirección si vienen en la respuesta
                tipo_resp = data.get('meeting', {}).get('tipo') or data.get('tipo')
                dir_resp = data.get('meeting', {}).get('direccion') or data.get('direccion')
                # Mostrar enlace solo si tipo existe y NO es presencial
                join_url = data.get('meeting', {}).get('join_url','')
                if (tipo_resp is not None) and (str(tipo_resp).strip().lower() != "presencial"):
                    if join_url:
                        resumen_lines.append(f"- Enlace: {join_url}")
                # Normalizar invitados a texto (preferir meeting.destinatarios)
                participantes_emails = []
                tema_val = data.get('meeting', {}).get('tema')
                if tema_val:
                    try:
                        # Buscar la reunión más reciente con ese tema
                        rlist = sb_select(
                            "reuniones",
                            {
                                "select": "id,tema,fecha_inicio",
                                "tema": f"eq.{tema_val}",
                                "order": "fecha_inicio.desc",
                                "limit": "1",
                            },
                        )
                        if rlist:
                            rid = rlist[0]["id"]
                            parts = sb_select(
                                "participantes",
                                {"select": "correo", "reunion_id": f"eq.{rid}"},
                            )
                            participantes_emails = [
                                p.get("correo") for p in parts if p.get("correo")
                            ]
                    except Exception:
                        participantes_emails = []

                # Fallback a destinatarios de la carga si no hay participantes
                if not participantes_emails:
                    raw_dest = data.get('meeting', {}).get('destinatarios')
                    if raw_dest is None:
                        raw_dest = data.get('destinatarios', [])
                    tmp = []
                    for d in raw_dest:
                        if isinstance(d, dict):
                            val = d.get("email") or d.get("correo") or d.get("name") or d.get("nombre") or d.get("value")
                            if val:
                                tmp.append(str(val))
                        else:
                            tmp.append(str(d))
                    participantes_emails = tmp

                if participantes_emails:
                    resumen_lines.append(f"- Invitados: {', '.join(participantes_emails)}")
                # Para reuniones presenciales: solo nombre, fecha e invitados (sin enlace, tipo ni dirección)
                es_presencial = bool(tipo_resp) and str(tipo_resp).strip().lower() == "presencial"
                if not es_presencial:
                    if tipo_resp:
                        resumen_lines.append(f"- Tipo: {tipo_resp}")
                    if dir_resp:
                        resumen_lines.append(f"- Dirección: {dir_resp}")
                resumen = "\n".join(resumen_lines)
                st.session_state.chat.append(("assistant", resumen))
                with st.chat_message("assistant"):
                    st.markdown(resumen)
                # Señalar limpieza segura antes de recrear widgets
                st.session_state["chat_reset_pending"] = True
                st.rerun()
            else:
                err = f"Error n8n: {resp.status_code} - {resp.text}"
                # Registrar error en métricas
                registrar_metrica_n8n(
                    endpoint="crear_reunion_chat",
                    tiempo_respuesta=tiempo_respuesta,
                    estado="error",
                    codigo_estado=resp.status_code,
                    detalles=f"Error en la respuesta: {resp.text[:200]}"
                )
                
                st.session_state.chat.append(("assistant", err))
                with st.chat_message("assistant"):
                    st.error(err)
                # Señalar limpieza segura antes de recrear widgets
                st.session_state["chat_reset_pending"] = True
                st.rerun()
        except Exception as e:
            # Registrar error en métricas
            tiempo_respuesta = time.time() - inicio if 'inicio' in locals() else 0
            registrar_metrica_n8n(
                endpoint="crear_reunion_chat",
                tiempo_respuesta=tiempo_respuesta,
                estado="error",
                detalles=f"Excepción: {str(e)}"
            )
            
            st.session_state.chat.append(("assistant", f"Error de conexión: {e}"))
            with st.chat_message("assistant"):
                st.error(f"Error de conexión: {e}")
            # Señalar limpieza segura antes de recrear widgets
            st.session_state["chat_reset_pending"] = True
            st.rerun()


# -------- Usuarios --------
def _estado_usuario(valor: str) -> tuple[str, str]:
    estado = str(valor or "activo").strip().lower()
    if estado == "activo":
        return "Activo", "active"
    if estado == "pendiente":
        return "Invitación pendiente", "pending"
    return "Suspendido", "suspended"


def _rol_usuario(usuario: dict) -> tuple[str, str]:
    correo = str(usuario.get("correo") or "").strip().lower()
    return ("Administrador", "admin") if correo in ADMIN_EMAILS else ("Miembro", "member")


def _iniciales_usuario(nombre: str, correo: str) -> str:
    partes = [p for p in str(nombre or "").split() if p]
    if not partes:
        partes = [str(correo or "U").split("@", 1)[0]]
    return "".join(p[0] for p in partes[:2]).upper() or "U"


def _fecha_invitacion_usuario(valor) -> str:
    fecha = _fecha_iso(valor)
    if not fecha:
        return "—"
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{fecha.day} {meses[fecha.month - 1]} {fecha.year}"


def _cerrar_dialogo_invitacion() -> None:
    st.session_state["users_invite_dialog_open"] = False


@st.dialog("Invitar nuevo usuario", width="large", on_dismiss=_cerrar_dialogo_invitacion)
def _dialogo_invitar_usuario() -> None:
    st.markdown('<div class="users-dialog-marker"></div>', unsafe_allow_html=True)
    st.markdown('<div class="users-dialog-description">Envía una invitación para unirse a tu organización.</div>', unsafe_allow_html=True)
    with st.form("users_invite_form"):
        correo = st.text_input("Correo electrónico", placeholder="ana@empresa.com")
        nombre = st.text_input("Nombre (opcional)", placeholder="Ej. Ana García")
        columna_rol, columna_equipo = st.columns(2)
        with columna_rol:
            rol = st.selectbox("Rol", ["Miembro", "Administrador"])
        with columna_equipo:
            st.selectbox("Equipo o área", ["Producto"])
        st.markdown('<div class="users-permission-title">Permisos iniciales</div>', unsafe_allow_html=True)
        crear_reuniones = st.checkbox("Crear y programar reuniones", value=True)
        transcripciones = st.checkbox("Acceder a transcripciones propias", value=True)
        informes_ia = st.checkbox("Generar informes con IA", value=True)
        administrar = st.checkbox("Administrar otros usuarios", value=False)
        st.markdown(
            f'<div class="users-invite-info"><img src="{icono_data_uri("informacion", "#2563EB")}" alt=""><span>El usuario recibirá un enlace de invitación válido por 7 días.</span></div>',
            unsafe_allow_html=True,
        )
        cancelar_col, enviar_col = st.columns([1, 1.35])
        with cancelar_col:
            cancelar = st.form_submit_button("Cancelar", use_container_width=True)
        with enviar_col:
            enviar = st.form_submit_button("Enviar invitación", type="primary", use_container_width=True)
    if cancelar:
        st.session_state["users_invite_dialog_open"] = False
        st.rerun()
    if not enviar:
        return
    correo = correo.strip().lower()
    nombre = nombre.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
        st.error("Introduce un correo electrónico válido.")
        return
    if rol == "Administrador" and not administrar:
        st.warning("El rol Administrador requiere el permiso para administrar otros usuarios.")
        return
    if rol == "Administrador" and correo not in ADMIN_EMAILS:
        st.error("Este correo no está autorizado como administrador en ADMIN_EMAILS.")
        return
    if not any([crear_reuniones, transcripciones, informes_ia, administrar]):
        st.warning("Selecciona al menos un permiso inicial.")
        return
    existentes = sb_select("usuarios", {"select": "id,correo,estado_suscripcion", "correo": f"eq.{correo}"})
    if existentes:
        st.error("Ya existe un usuario o una invitación para este correo.")
        return
    token = secrets.token_urlsafe(32)
    nivel = "enterprise" if administrar or rol == "Administrador" else ("pro" if informes_ia else "basico")
    sb_insert(
        "usuarios",
        [{
            "nombre": nombre or correo,
            "correo": correo,
            "password_hash": hash_pw(token),
            "nivel_suscripcion": nivel,
            "estado_suscripcion": "pendiente",
        }],
    )
    base_publica = os.getenv(
        "FRONTEND_PUBLIC_URL",
        "http://127.0.0.1:8501" if DEMO_MODE else "https://reuniones-ia-frontend.onrender.com",
    ).rstrip("/")
    enlace = f"{base_publica}/?aceptar_invitacion={quote(token, safe='')}&correo={quote(correo, safe='')}"
    st.success("Invitación creada correctamente.")
    st.markdown('<div class="users-invite-link-label">Enlace de invitación</div>', unsafe_allow_html=True)
    st.code(enlace, language=None, wrap_lines=True)


@st.dialog("Gestionar usuario")
def _dialogo_gestionar_usuario(usuario: dict) -> None:
    st.markdown('<div class="users-dialog-marker"></div>', unsafe_allow_html=True)
    user_id = str(usuario.get("id") or "")
    with st.form(f"users_manage_form_{user_id}"):
        nombre = st.text_input("Nombre", value=str(usuario.get("nombre") or ""))
        st.text_input("Correo electrónico", value=str(usuario.get("correo") or ""), disabled=True)
        niveles = ["basico", "pro", "enterprise"]
        nivel_actual = str(usuario.get("nivel_suscripcion") or "basico")
        nivel = st.selectbox("Nivel de suscripción", niveles, index=niveles.index(nivel_actual) if nivel_actual in niveles else 0)
        estados = ["activo", "pendiente", "suspendido", "cancelado"]
        estado_actual = str(usuario.get("estado_suscripcion") or "activo")
        estado = st.selectbox("Estado", estados, index=estados.index(estado_actual) if estado_actual in estados else 0)
        cancelar_col, guardar_col = st.columns(2)
        with cancelar_col:
            cancelar = st.form_submit_button("Cancelar", use_container_width=True)
        with guardar_col:
            guardar = st.form_submit_button("Guardar cambios", type="primary", use_container_width=True)
    if cancelar:
        st.rerun()
    if guardar:
        respuesta = requests.patch(
            f"{SUPABASE_URL}/rest/v1/usuarios",
            headers={**HEADERS, "Prefer": "return=representation"},
            params={"id": f"eq.{user_id}"},
            data=json.dumps({"nombre": nombre.strip(), "nivel_suscripcion": nivel, "estado_suscripcion": estado}),
            timeout=30,
        )
        respuesta.raise_for_status()
        st.toast("Usuario actualizado")
        st.rerun()
    es_actual = user_id == str((st.session_state.session or {}).get("id") or "")
    with st.expander("Eliminar usuario"):
        confirmar = st.checkbox("Confirmo que deseo eliminar este usuario", key=f"users_delete_confirm_{user_id}")
        if st.button("Eliminar usuario", key=f"users_delete_{user_id}", disabled=not confirmar or es_actual):
            respuesta = requests.delete(
                f"{SUPABASE_URL}/rest/v1/usuarios", headers=HEADERS,
                params={"id": f"eq.{user_id}"}, timeout=30,
            )
            respuesta.raise_for_status()
            st.toast("Usuario eliminado")
            st.rerun()


def view_usuarios():
    st.markdown('<div class="users-page-marker"></div>', unsafe_allow_html=True)
    if not is_admin():
        st.error("Solo los administradores pueden gestionar usuarios y permisos.")
        return
    try:
        users = sb_select(
            "usuarios",
            {"select": "id,nombre,correo,nivel_suscripcion,estado_suscripcion,fecha_creacion", "order": "fecha_creacion.desc"},
        )
        reuniones = sb_select("reuniones", {"select": "id,creador_id"})
    except Exception as exc:
        st.error(f"Error cargando usuarios: {exc}")
        return
    reuniones_por_usuario: dict[str, int] = {}
    for reunion in reuniones:
        creador_id = str(reunion.get("creador_id") or "")
        reuniones_por_usuario[creador_id] = reuniones_por_usuario.get(creador_id, 0) + 1
    encabezado, accion = st.columns([4, 1])
    with encabezado:
        st.markdown(
            f'<div class="users-heading"><img src="{ICONOS_AZULES["usuarios"]}" alt=""><h1>Usuarios y permisos</h1></div><div class="users-subtitle">Administra el acceso de tu organización a VINCORA Meet.</div>',
            unsafe_allow_html=True,
        )
    with accion:
        abrir_invitacion = st.button("Invitar usuario", key="users_invite_open", use_container_width=True)
        if abrir_invitacion:
            st.session_state["users_invite_dialog_open"] = True
    total = len(users)
    activos = sum(1 for u in users if str(u.get("estado_suscripcion") or "").lower() == "activo")
    pendientes = sum(1 for u in users if str(u.get("estado_suscripcion") or "").lower() == "pendiente")
    suspendidos = sum(1 for u in users if str(u.get("estado_suscripcion") or "").lower() in {"suspendido", "cancelado"})
    st.markdown(
        f"""
        <div class="users-metrics">
          <div class="users-metric"><span class="users-metric-icon total"><img src="{icono_data_uri('usuario', '#6D28D9')}" alt=""></span><span><div class="users-metric-value">{total}</div><div class="users-metric-label">usuarios</div></span></div>
          <div class="users-metric"><span class="users-metric-icon active"><img src="{icono_data_uri('usuario_configuracion', '#07999B')}" alt=""></span><span><div class="users-metric-value">{activos}</div><div class="users-metric-label">activos</div></span></div>
          <div class="users-metric"><span class="users-metric-icon pending"><img src="{icono_data_uri('tiempo', '#D97706')}" alt=""></span><span><div class="users-metric-value">{pendientes}</div><div class="users-metric-label">invitaciones pendientes</div></span></div>
          <div class="users-metric"><span class="users-metric-icon suspended"><img src="{icono_data_uri('usuario_suspendido', '#C12B38')}" alt=""></span><span><div class="users-metric-value">{suspendidos}</div><div class="users-metric-label">suspendidos</div></span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True, key="users_filters"):
        st.markdown('<div class="users-filter-marker"></div>', unsafe_allow_html=True)
        buscar_col, rol_col, estado_col, aplicar_col = st.columns([3.6, 1.15, 1.15, .42])
        with buscar_col:
            filtro_texto = st.text_input(
                "Buscar por nombre o correo", placeholder="Buscar por nombre o correo...",
                label_visibility="collapsed", key="users_search",
            )
        with rol_col:
            filtro_rol = st.selectbox("Rol", ["Todos", "Miembro", "Administrador"], key="users_role_filter")
        with estado_col:
            filtro_estado = st.selectbox(
                "Estado", ["Todos", "Activo", "Invitación pendiente", "Suspendido"],
                key="users_status_filter",
            )
        with aplicar_col:
            aplicar = st.button("Aplicar filtros", key="users_apply_filter", help="Aplicar filtros", use_container_width=True)
    if aplicar:
        st.session_state["users_page"] = 1
    usuarios_filtrados = list(users)
    texto = filtro_texto.strip().lower()
    if texto:
        usuarios_filtrados = [
            u for u in usuarios_filtrados
            if texto in str(u.get("nombre") or "").lower() or texto in str(u.get("correo") or "").lower()
        ]
    if filtro_rol != "Todos":
        usuarios_filtrados = [u for u in usuarios_filtrados if _rol_usuario(u)[0] == filtro_rol]
    if filtro_estado != "Todos":
        usuarios_filtrados = [u for u in usuarios_filtrados if _estado_usuario(u.get("estado_suscripcion"))[0] == filtro_estado]
    por_pagina = int(st.session_state.get("users_per_page", 10))
    total_filtrado = len(usuarios_filtrados)
    total_paginas = max(1, (total_filtrado + por_pagina - 1) // por_pagina)
    pagina = min(max(1, int(st.session_state.get("users_page", 1))), total_paginas)
    st.session_state["users_page"] = pagina
    inicio = (pagina - 1) * por_pagina
    fin = min(inicio + por_pagina, total_filtrado)
    pagina_usuarios = usuarios_filtrados[inicio:fin]
    celdas = [
        '<div class="users-th">Usuario</div>', '<div class="users-th">Rol</div>',
        '<div class="users-th">Reuniones</div>', '<div class="users-th">Último acceso</div>',
        '<div class="users-th">Estado</div>', '<div class="users-th">Acciones</div>',
    ]
    correo_actual = str((st.session_state.session or {}).get("correo") or "").strip().lower()
    for usuario in pagina_usuarios:
        nombre = str(usuario.get("nombre") or usuario.get("correo") or "Usuario")
        correo = str(usuario.get("correo") or "")
        rol_texto, rol_clase = _rol_usuario(usuario)
        estado_texto, estado_clase = _estado_usuario(usuario.get("estado_suscripcion"))
        ultimo_acceso = "Ahora" if correo.lower() == correo_actual else (
            _fecha_invitacion_usuario(usuario.get("fecha_creacion")) if estado_clase == "pending" else "—"
        )
        user_id = str(usuario.get("id") or "")
        celdas.extend([
            f'<div><div class="users-person"><span class="users-avatar">{escape(_iniciales_usuario(nombre, correo))}</span><span class="users-person-copy"><div class="users-person-name">{escape(nombre)}</div><div class="users-person-email">{escape(correo)}</div></span></div></div>',
            f'<div><span class="users-role-pill {rol_clase}">{escape(rol_texto)}</span></div>',
            f'<div>{reuniones_por_usuario.get(user_id, 0)}</div>', f'<div>{escape(ultimo_acceso)}</div>',
            f'<div><span class="users-status-pill {estado_clase}">{escape(estado_texto)}</span></div>',
            f'<div><a class="users-action-link" href="?pagina=Usuarios&amp;gestionar_usuario={quote(user_id, safe="")}" target="_self" aria-label="Gestionar {escape(nombre)}">⋮</a></div>',
        ])
    if not pagina_usuarios:
        celdas.append('<div class="users-empty">No hay usuarios que coincidan con los filtros.</div>')
    st.markdown(f'<div class="users-table">{"".join(celdas)}</div>', unsafe_allow_html=True)
    with st.container(key="users_footer"):
        resumen_col, anterior_col, numero_col, siguiente_col, cantidad_col = st.columns([4, .45, .45, .45, 1.15])
        with resumen_col:
            st.caption(f"Mostrando {inicio + 1} a {fin} de {total_filtrado} usuarios" if total_filtrado else "Mostrando 0 usuarios")
        with anterior_col:
            if st.button("‹", key="users_prev", disabled=pagina <= 1, use_container_width=True):
                st.session_state["users_page"] = pagina - 1
                st.rerun()
        with numero_col:
            st.markdown(f'<span class="users-page-number">{pagina}</span>', unsafe_allow_html=True)
        with siguiente_col:
            if st.button("›", key="users_next", disabled=pagina >= total_paginas, use_container_width=True):
                st.session_state["users_page"] = pagina + 1
                st.rerun()
        with cantidad_col:
            st.selectbox(
                "Usuarios por página", [10, 25, 50], key="users_per_page",
                format_func=lambda valor: f"{valor} por página", label_visibility="collapsed",
            )
    if st.session_state.get("users_invite_dialog_open", False):
        _dialogo_invitar_usuario()
    gestionar_id = str(st.query_params.get("gestionar_usuario", "") or "")
    if gestionar_id:
        if "gestionar_usuario" in st.query_params:
            del st.query_params["gestionar_usuario"]
        seleccionado = next((u for u in users if str(u.get("id")) == gestionar_id), None)
        if seleccionado:
            _dialogo_gestionar_usuario(seleccionado)

# -------- Reuniones --------
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_hora_reunion(valor):
    if not valor:
        return None
    try:
        fecha = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        if fecha.tzinfo:
            fecha = fecha.astimezone(ZoneInfo("America/Lima"))
        return fecha
    except (TypeError, ValueError):
        return None


def _hora_es(fecha: datetime) -> str:
    hora = fecha.hour % 12 or 12
    sufijo = "a. m." if fecha.hour < 12 else "p. m."
    return f"{hora}:{fecha.minute:02d} {sufijo}"


def _cerrar_dialogo_reunion() -> None:
    st.session_state["meeting_dialog_open"] = False


def _crear_reunion_directa(tema, fecha_inicio, duracion, invitados) -> None:
    creada = requests.post(
        f"{SUPABASE_URL}/rest/v1/reuniones",
        headers={**HEADERS, "Prefer": "return=representation"},
        data=json.dumps([{
            "creador_id": st.session_state.session["id"],
            "tema": tema,
            "fecha_inicio": fecha_inicio,
            "duracion_minutos": int(duracion),
            "proveedor": "manual",
            "estado": "programada",
            "tipo": "virtual",
            "direccion": None,
        }]),
        timeout=30,
    )
    creada.raise_for_status()
    reunion_id = creada.json()[0]["id"]
    if invitados:
        sb_insert("participantes", [{
            "reunion_id": reunion_id,
            "correo": correo,
            "rol": "participante",
            "estado_invitacion": "enviado",
        } for correo in invitados])


@st.dialog("Programar nueva reunión", width="small", on_dismiss=_cerrar_dialogo_reunion)
def _dialogo_programar_reunion(correos_disponibles: list[str]) -> None:
    st.markdown('<div class="meeting-dialog-marker"></div>', unsafe_allow_html=True)
    st.markdown('<div class="meeting-dialog-description">Configura los detalles y deja que VINCORA prepare todo.</div>', unsafe_allow_html=True)
    ahora = datetime.now(ZoneInfo("America/Lima"))
    horas_disponibles = [f"{hora:02d}:{minuto:02d}" for hora in range(24) for minuto in (0, 30)]
    predeterminados = correos_disponibles[:2] if DEMO_MODE else []
    with st.form("meeting_schedule_form"):
        tema = st.text_input("Título de la reunión", placeholder="Revisión del proyecto VINCORA")
        fecha_col, hora_col, duracion_col = st.columns([1.1, .95, 1])
        with fecha_col:
            fecha = st.date_input("Fecha", value=ahora.date(), format="DD/MM/YYYY")
        with hora_col:
            hora_texto = st.selectbox(
                "Hora de inicio", horas_disponibles, index=horas_disponibles.index("16:00"),
                format_func=lambda valor: _hora_es(datetime.strptime(valor, "%H:%M")),
            )
        with duracion_col:
            duracion = st.selectbox("Duración", [15, 30, 45, 60, 90, 120], index=2, format_func=lambda valor: f"{valor} minutos")
        st.selectbox("Zona horaria", ["Lima (GMT-5)"])
        invitados = st.multiselect(
            "Invitados", correos_disponibles, default=predeterminados,
            accept_new_options=True, placeholder="ana@empresa.com",
        )
        objetivo = st.text_area("Objetivo", placeholder="Revisar avances, resolver bloqueos y establecer los próximos acuerdos.", height=72)
        with st.container(key="meeting_assistant"):
            st.markdown('<div class="meeting-assistant-title">Asistente inteligente</div>', unsafe_allow_html=True)
            grabar_texto, grabar_control = st.columns([6, 1])
            with grabar_texto:
                st.markdown(f'<div class="meeting-assistant-option"><img src="{ICONOS_AZULES["microfono"]}" alt="">Grabar reunión</div>', unsafe_allow_html=True)
            with grabar_control:
                grabar = st.toggle("Grabar reunión", value=True, label_visibility="collapsed", key="meeting_record")
            transcribir_texto, transcribir_control = st.columns([6, 1])
            with transcribir_texto:
                st.markdown(f'<div class="meeting-assistant-option"><img src="{ICONOS_AZULES["resumen"]}" alt="">Transcripción automática</div>', unsafe_allow_html=True)
            with transcribir_control:
                transcribir = st.toggle("Transcripción automática", value=True, label_visibility="collapsed", key="meeting_transcribe")
            informe_texto, informe_control = st.columns([6, 1])
            with informe_texto:
                st.markdown(f'<div class="meeting-assistant-option"><img src="{ICONOS_AZULES["destellos"]}" alt="">Generar informe con IA</div>', unsafe_allow_html=True)
            with informe_control:
                informe = st.toggle("Generar informe con IA", value=True, label_visibility="collapsed", key="meeting_report")
        st.markdown(
            '<div class="meeting-dialog-note">ⓘ　Los participantes deberán aceptar la grabación y transcripción al ingresar.</div>',
            unsafe_allow_html=True,
        )
        cancelar_col, espacio_col, crear_col = st.columns([1.5, .35, 2.4])
        with cancelar_col:
            cancelar = st.form_submit_button("Cancelar", use_container_width=True)
        with espacio_col:
            st.markdown("")
        with crear_col:
            crear = st.form_submit_button("Programar reunión", type="primary", use_container_width=True)
    if cancelar:
        st.session_state["meeting_dialog_open"] = False
        st.rerun()
    if not crear:
        return
    tema = tema.strip()
    invitados = list(dict.fromkeys(str(c).strip().lower() for c in invitados if str(c).strip()))
    if not tema:
        st.error("Introduce el título de la reunión.")
        return
    invalidos = [c for c in invitados if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", c)]
    if invalidos:
        st.error("Revisa los correos de los invitados.")
        return
    hora = datetime.strptime(hora_texto, "%H:%M").time()
    inicio = datetime.combine(fecha, hora, tzinfo=ZoneInfo("America/Lima"))
    if inicio <= datetime.now(ZoneInfo("America/Lima")):
        st.error("Selecciona una fecha y hora futuras.")
        return
    fecha_inicio = inicio.isoformat()
    opciones_asistente = []
    if grabar:
        opciones_asistente.append("grabar la reunión")
    if transcribir:
        opciones_asistente.append("activar la transcripción automática")
    if informe:
        opciones_asistente.append("generar un informe con IA")
    mensaje = (
        f"Programa una reunión virtual titulada {tema} el {fecha.isoformat()} a las {hora.strftime('%H:%M')} "
        f"hora de Lima, con una duración de {duracion} minutos"
    )
    if invitados:
        mensaje += f", e invita a {', '.join(invitados)}"
    if objetivo.strip():
        mensaje += f". Objetivo: {objetivo.strip()}"
    if opciones_asistente:
        mensaje += f". Configura el asistente para {', '.join(opciones_asistente)}"
    try:
        if N8N_URL and not DEMO_MODE:
            respuesta = requests.post(
                N8N_URL,
                json={"creador_id": st.session_state.session["id"], "mensaje": mensaje},
                timeout=90,
            )
            respuesta.raise_for_status()
        else:
            _crear_reunion_directa(tema, fecha_inicio, int(duracion), invitados)
        st.session_state["meeting_dialog_open"] = False
        st.toast("Reunión programada")
        st.rerun()
    except Exception as exc:
        st.error(f"No fue posible programar la reunión: {exc}")


def _tarjetas_reuniones(reuniones: list[dict], participantes_por_reunion: dict[str, list[dict]], usuarios_correo: dict[str, str]) -> str:
    tarjetas = []
    for reunion in reuniones:
        fecha = reunion.get("_fecha")
        if not fecha:
            continue
        correos = [str(p.get("correo") or "") for p in participantes_por_reunion.get(str(reunion.get("id")), [])]
        nombres = [usuarios_correo.get(c.lower(), c) for c in correos if c]
        enlace = _url_inicio(reunion.get("start_url") or reunion.get("join_url"))
        accion = f' · <a href="?sala_previa={quote(str(reunion.get("id") or ""))}" target="_self">Abrir reunión</a>' if enlace else ""
        tarjetas.append(
            f'<div class="meetings-list-card"><h3>{escape(str(reunion.get("tema") or "Reunión"))}</h3>'
            f'<p>{fecha.day} de {MESES_ES[fecha.month - 1]} de {fecha.year} · {_hora_es(fecha)} · {int(reunion.get("duracion_minutos") or 0)} minutos{accion}</p>'
            f'<p>{escape(", ".join(nombres))}</p></div>'
        )
    return '<div class="meetings-list">' + ("".join(tarjetas) or '<div class="meetings-list-card"><p>No hay reuniones en esta vista.</p></div>') + "</div>"


def view_sala_previa(reunion_id: str) -> None:
    """Comprueba dispositivos y consentimiento antes de abrir la reunión real."""
    import streamlit.components.v1 as components

    st.markdown('<div class="prejoin-page-marker"></div>', unsafe_allow_html=True)
    try:
        reuniones = sb_select(
            "reuniones",
            {
                "select": "id,tema,join_url,start_url,creador_id",
                "id": f"eq.{reunion_id}",
                "limit": "1",
            },
        )
        reunion = reuniones[0] if reuniones else None
    except Exception:
        reunion = None
    if not reunion:
        st.error("No encontramos la reunión solicitada.")
        if st.button("Volver a Reuniones"):
            st.query_params.clear()
            st.query_params["pagina"] = "Reuniones"
            st.rerun()
        return
    sesion = st.session_state.session or {}
    es_creador = str(reunion.get("creador_id") or "") == str(sesion.get("id") or "")
    enlace = reunion.get("start_url") if es_creador else reunion.get("join_url")
    enlace = _url_inicio(enlace) or _url_inicio(reunion.get("join_url")) or _url_inicio(reunion.get("start_url"))
    reunion_render = {**reunion, "join_url": enlace, "start_url": None}
    try:
        participantes = sb_select("participantes", {"select": "id", "reunion_id": f"eq.{reunion_id}"})
    except Exception:
        participantes = []
    html = build_prejoin_html(
        logo=LOGO_DATA_URI,
        meeting=reunion_render,
        participant_name=str(sesion.get("nombre") or "Usuario"),
        participant_count=len(participantes),
    )
    components.html(html, height=1000, scrolling=True)


def view_reuniones():
    st.markdown('<div class="meetings-page-marker"></div>', unsafe_allow_html=True)
    try:
        reuniones = sb_select(
            "reuniones",
            {"select": "id,tema,fecha_inicio,duracion_minutos,proveedor,id_externo,join_url,start_url,estado,creador_id,tipo,direccion", "order": "fecha_inicio.asc"},
        )
        participantes = sb_select("participantes", {"select": "id,reunion_id,usuario_id,correo,rol,estado_invitacion"})
        usuarios = sb_select("usuarios", {"select": "id,nombre,correo,estado_suscripcion"})
    except Exception as exc:
        st.error(f"Error cargando reuniones: {exc}")
        return
    for reunion in reuniones:
        reunion["_fecha"] = _fecha_hora_reunion(reunion.get("fecha_inicio"))
    participantes_por_reunion: dict[str, list[dict]] = {}
    for participante in participantes:
        participantes_por_reunion.setdefault(str(participante.get("reunion_id")), []).append(participante)
    usuarios_correo = {
        str(usuario.get("correo") or "").lower(): str(usuario.get("nombre") or usuario.get("correo") or "")
        for usuario in usuarios
    }
    correos_disponibles = sorted(
        str(usuario.get("correo") or "").lower() for usuario in usuarios
        if usuario.get("correo") and str(usuario.get("estado_suscripcion") or "activo").lower() == "activo"
    )
    if st.query_params.get("programar_reunion") == "1" and is_admin():
        st.session_state["meeting_dialog_open"] = True
        del st.query_params["programar_reunion"]
    vista_query = str(st.query_params.get("vista_reuniones", "") or "")
    if vista_query in {"Calendario", "Próximas", "Finalizadas"}:
        st.session_state["meetings_view"] = vista_query
        del st.query_params["vista_reuniones"]
    st.markdown(
        f'<div class="meetings-heading"><img src="{ICONOS_AZULES["reuniones"]}" alt=""><h1>Reuniones</h1></div>'
        '<div class="meetings-subtitle">Administra y programa tus reuniones.</div>',
        unsafe_allow_html=True,
    )
    if "meetings_view" not in st.session_state:
        st.session_state["meetings_view"] = "Calendario"
    vista = st.segmented_control(
        "Vista", ["Calendario", "Próximas", "Finalizadas"],
        key="meetings_view", label_visibility="collapsed",
    ) or "Calendario"
    ahora = datetime.now(ZoneInfo("America/Lima"))
    if vista == "Próximas":
        proximas = [r for r in reuniones if r.get("_fecha") and r["_fecha"] >= ahora and str(r.get("estado") or "").lower() == "programada"]
        st.markdown(_tarjetas_reuniones(proximas, participantes_por_reunion, usuarios_correo), unsafe_allow_html=True)
    elif vista == "Finalizadas":
        finalizadas = [r for r in reuniones if str(r.get("estado") or "").lower() in {"completada", "cancelada"}]
        st.markdown(_tarjetas_reuniones(finalizadas, participantes_por_reunion, usuarios_correo), unsafe_allow_html=True)
    else:
        mes_query = str(st.query_params.get("mes", "") or "")
        try:
            anio, mes = [int(x) for x in mes_query.split("-", 1)] if mes_query else (ahora.year, ahora.month)
            ancla = datetime(anio, mes, 1)
        except (TypeError, ValueError):
            ancla = datetime(ahora.year, ahora.month, 1)
        anterior = (ancla - timedelta(days=1)).replace(day=1)
        siguiente = (ancla.replace(day=28) + timedelta(days=4)).replace(day=1)
        reuniones_dia: dict[object, list[dict]] = {}
        for reunion in reuniones:
            if reunion.get("_fecha"):
                reuniones_dia.setdefault(reunion["_fecha"].date(), []).append(reunion)
        calendario = calendar.Calendar(firstweekday=6).monthdatescalendar(ancla.year, ancla.month)
        actual_id = str(st.session_state.session.get("id") or "")
        celdas = []
        for fecha_dia in [dia for semana in calendario for dia in semana]:
            clases = ["meetings-day"]
            if fecha_dia.month != ancla.month:
                clases.append("outside")
            if fecha_dia == ahora.date():
                clases.append("today")
            eventos = []
            for reunion in reuniones_dia.get(fecha_dia, [])[:3]:
                externa = str(reunion.get("creador_id") or "") != actual_id
                enlace = _url_inicio(reunion.get("start_url") or reunion.get("join_url"))
                etiqueta = f'{_hora_es(reunion["_fecha"])} {reunion.get("tema") or "Reunión"}'
                clase = "meetings-event external" if externa else "meetings-event"
                if enlace:
                    eventos.append(f'<a class="{clase}" href="?sala_previa={quote(str(reunion.get("id") or ""))}" target="_self">{escape(etiqueta)}</a>')
                else:
                    eventos.append(f'<span class="{clase}">{escape(etiqueta)}</span>')
            celdas.append(f'<div class="{" ".join(clases)}"><span class="meetings-day-number">{fecha_dia.day}</span>{"".join(eventos)}</div>')
        reuniones_hoy = reuniones_dia.get(ahora.date(), [])
        agenda = []
        for reunion in reuniones_hoy:
            externa = str(reunion.get("creador_id") or "") != actual_id
            fin = reunion["_fecha"] + timedelta(minutes=int(reunion.get("duracion_minutos") or 0))
            correos = [str(p.get("correo") or "") for p in participantes_por_reunion.get(str(reunion.get("id")), [])]
            nombres = [usuarios_correo.get(c.lower(), c) for c in correos if c]
            agenda.append(
                f'<div class="meetings-agenda-card{" external" if externa else ""}">'
                f'<div class="meetings-agenda-time">{_hora_es(reunion["_fecha"])} - {_hora_es(fin)}</div>'
                f'<div class="meetings-agenda-title">{escape(str(reunion.get("tema") or "Reunión"))}</div>'
                f'<div class="meetings-agenda-guests">{escape(", ".join(nombres))}</div>'
                f'<span class="meetings-type-pill">{escape(str(reunion.get("tipo") or "Virtual").title())}</span></div>'
            )
        agenda_html = "".join(agenda) if agenda else '<div class="meetings-agenda-empty">No hay reuniones programadas para hoy.</div>'
        boton_programar = '<a class="meetings-toolbar-button primary" href="?pagina=Reuniones&amp;programar_reunion=1" target="_self">Programar reunión</a>' if is_admin() else ""
        st.markdown(
            f'<div class="meetings-shell"><div class="meetings-toolbar">'
            f'<div class="meetings-month"><span class="meetings-month-arrow">‹</span>{MESES_ES[ancla.month - 1].title()} {ancla.year}</div>'
            f'<div class="meetings-toolbar-actions"><a class="meetings-toolbar-button" href="?pagina=Reuniones&amp;mes={ahora.year:04d}-{ahora.month:02d}" target="_self">Hoy</a>'
            f'<a class="meetings-toolbar-button arrow" href="?pagina=Reuniones&amp;mes={anterior.year:04d}-{anterior.month:02d}" target="_self">‹</a>'
            f'<a class="meetings-toolbar-button arrow" href="?pagina=Reuniones&amp;mes={siguiente.year:04d}-{siguiente.month:02d}" target="_self">›</a>{boton_programar}</div></div>'
            f'<div class="meetings-layout"><div class="meetings-calendar"><div class="meetings-weekdays">'
            + "".join(f'<div class="meetings-weekday">{dia}</div>' for dia in ["DOM", "LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB"])
            + f'</div><div class="meetings-days">{"".join(celdas)}</div><div class="meetings-legend"><span><i></i>Reunión de equipo</span><span><i class="external"></i>Reunión externa</span></div></div>'
            f'<aside class="meetings-agenda"><h2>Hoy</h2><div class="meetings-agenda-date">{ahora.day} de {MESES_ES[ahora.month - 1]} de {ahora.year}</div>'
            f'{agenda_html}'
            f'<a class="meetings-agenda-link" href="?pagina=Reuniones&amp;vista_reuniones=Próximas" target="_self">Ver agenda completa</a></aside></div></div>',
            unsafe_allow_html=True,
        )
    if st.session_state.get("meeting_dialog_open", False):
        _dialogo_programar_reunion(correos_disponibles)

# -------- Resumen de reuniones --------
def view_resumen_reuniones():
    titulo_pagina("resumen", "Resumen de reuniones")

    # Obtener reuniones con campos clave
    try:
        reuniones = sb_select(
            "reuniones",
            {"select": "id,tema,fecha_inicio,estado,tipo,direccion,duracion_minutos,join_url"}
        )
    except Exception as e:
        st.error(f"Error cargando reuniones: {e}")
        return

    # Formatear fecha para visualización
    for r in reuniones:
        if r.get("fecha_inicio"):
            r["fecha_inicio"] = r["fecha_inicio"].replace("T", " ").replace("Z", "")

    df_total = pd.DataFrame(reuniones)
    if df_total.empty:
        st.info("No hay reuniones registradas.")
        return

    if DEMO_MODE:
        resumenes_demo = sb_select("resumenes", {"select": "reunion_id,resumen,fecha_creacion"})
        resumen_por_reunion = {str(x.get("reunion_id")): x.get("resumen") for x in resumenes_demo}
        df_demo = df_total[["id", "tema", "fecha_inicio", "estado", "tipo", "direccion"]].copy()
        df_demo["resumen"] = df_demo["id"].astype(str).map(resumen_por_reunion).fillna("Sin resumen generado")
        df_demo = df_demo.drop(columns=["id"])
        st.subheader("Reuniones y resúmenes disponibles")
        st.markdown(df_demo.to_html(index=False), unsafe_allow_html=True)
        st.caption("Vista local de solo lectura para documentación y capturas.")
        return

    # Asegurar columna tipo en minúsculas para filtro
    df_total["tipo"] = df_total["tipo"].astype(str).str.lower()

    col_v, col_p, col_m = st.columns(3)

    def render_columna(col, df_filtro, nombre, key_prefix):
      with col:
          st.subheader(nombre)
          mostrar_cols = [c for c in ["id","tema","fecha_inicio","estado","direccion"] if c in df_filtro.columns]
          st.dataframe(df_filtro[mostrar_cols].reset_index(drop=True), use_container_width=True)

          # Lista desplegable y/o búsqueda por ID de reunión
          opciones = {}
          for r in df_filtro.to_dict("records"):
              label = f"{r.get('tema','(Sin tema)')} — {r.get('fecha_inicio','')} (ID {r.get('id')})"
              opciones[label] = r.get("id")
          opciones_list = ["— Selecciona —"] + list(opciones.keys())
          sel_val = st.selectbox("Escoge una reunión", opciones_list, key=f"sel_{key_prefix}")

          st.caption("O busca por ID de la reunión")
          input_id = st.text_input("ID de reunión", key=f"id_{key_prefix}", placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")

          chosen_id = None
          if sel_val and sel_val != "— Selecciona —":
              chosen_id = opciones[sel_val]
          if input_id:
              chosen_id = input_id

          if chosen_id:
              # Buscar en el dataframe filtrado, o consultar directamente por ID
              fila = None
              if not df_filtro.empty and chosen_id in set(df_filtro["id"].astype(str)):
                  fila = df_filtro[df_filtro["id"].astype(str) == chosen_id].iloc[0].to_dict()
              else:
                  try:
                      q = sb_select(
                          "reuniones",
                          {"select":"id,tema,fecha_inicio,duracion_minutos,tipo,estado,direccion,join_url,start_url,proveedor,creador_id", "id": f"eq.{chosen_id}"}
                      )
                      if q:
                          fila = q[0]
                  except Exception as e:
                      st.error(f"Error buscando reunión: {e}")
                      return

              if fila:
                  # Detalles de la reunión
                  reunion_id = str(fila.get("id"))
                  st.markdown("**Detalles de la reunión**")
                  det = {
                      "ID": fila.get("id"),
                      "Tema": fila.get("tema"),
                      "Fecha": (fila.get("fecha_inicio") or "").replace("T"," ").replace("Z","").replace("+00:00",""),
                      "Duración (min)": fila.get("duracion_minutos"),
                      "Tipo": fila.get("tipo"),
                      "Estado": fila.get("estado"),
                      "Dirección": fila.get("direccion"),
                      "Enlace": fila.get("join_url"),
                  }
                  st.json(det)
                  # Ver participantes de la reunión
                  if st.button("Ver participantes", key=f"ver_part_{key_prefix}"):
                      try:
                          parts = sb_select(
                              "participantes",
                              {"select":"correo,rol,estado_invitacion,fecha_creacion", "reunion_id": f"eq.{reunion_id}"}
                          )
                          if not parts:
                              st.info("No hay participantes registrados para esta reunión.")
                          else:
                              # Formatear fecha
                              for p in parts:
                                  if p.get("fecha_creacion"):
                                      p["fecha_creacion"] = p["fecha_creacion"].replace("T"," ").replace("Z","")
                              with st.expander("Participantes", expanded=False):
                                  st.dataframe(pd.DataFrame(parts), use_container_width=True)
                                  # Métricas rápidas
                                  total = len(parts)
                                  orgs = sum(1 for p in parts if str(p.get("rol","")) == "organizador")
                                  partics = sum(1 for p in parts if str(p.get("rol","")) == "participante")
                                  m1, m2, m3 = st.columns(3)
                                  m1.metric("Total", total)
                                  m2.metric("Organizadores", orgs)
                                  m3.metric("Participantes", partics)
                                  # Donut de estados de invitación
                                  try:
                                      dfc = pd.DataFrame(parts)
                                      cdata = dfc.groupby("estado_invitacion").size().reset_index(name="conteo")
                                      chart = alt.Chart(cdata).mark_arc(innerRadius=40).encode(
                                          theta=alt.Theta("conteo:Q", stack=True),
                                          color=alt.Color("estado_invitacion:N", scale=alt.Scale(scheme="pastel2")),
                                          tooltip=["estado_invitacion:N","conteo:Q"]
                                      ).properties(height=180)
                                      st.altair_chart(chart, use_container_width=True)
                                  except Exception:
                                      pass
                      except Exception as e:
                          st.error(f"Error cargando participantes: {e}")

                  # Resumen existente
                  try:
                      res = sb_select(
                          "resumenes",
                          {"select": "id,reunion_id,resumen,fecha_creacion", "reunion_id": f"eq.{reunion_id}"}
                      )
                  except Exception as e:
                      st.error(f"Error cargando resumen: {e}")
                      return

                  if res:
                      item = res[0]
                      st.markdown("**Resumen**")
                      st.write(item.get("resumen") or "(Vacío)")
                      if item.get("fecha_creacion"):
                          st.caption(f"Creado: {item['fecha_creacion'].replace('T',' ').replace('Z','')}")
                  else:
                      st.info("No existe un resumen para esta reunión.")

                  # Generación según tipo
                  tipo_val = str(fila.get("tipo") or "").lower()
                  if tipo_val in ["virtual", "mixta"]:
                      btn = st.button("Generar resumen (IA)", key=f"gen_{key_prefix}")
                      if btn:
                          if not N8N_RESUMEN_VIRTUAL_URL:
                              st.error("Configura N8N_RESUMEN_VIRTUAL_WEBHOOK_URL en .env")
                          else:
                              try:
                                  inicio = time.time()
                                  with st.spinner("Generando resumen..."):
                                      resp = requests.post(N8N_RESUMEN_VIRTUAL_URL, json={"reunion_id": reunion_id}, timeout=120)
                                  
                                  # Calcular tiempo de respuesta
                                  tiempo_respuesta = time.time() - inicio
                                  tamano_respuesta = len(resp.content) if resp.content else 0
                                  
                                  # Registrar métrica
                                  registrar_metrica_n8n(
                                      endpoint="resumen_virtual",
                                      tiempo_respuesta=tiempo_respuesta,
                                      estado="éxito" if resp.status_code == 200 else "error",
                                      codigo_estado=resp.status_code,
                                      reunion_id=reunion_id,
                                      tamano_respuesta=tamano_respuesta
                                  )
                                  
                                  if resp.status_code == 200:
                                      data = resp.json()
                                      resumen_texto = data.get("resumen") or data.get("summary") or ""
                                      if resumen_texto:
                                          if save_resumen(reunion_id, resumen_texto):
                                              st.success("Resumen generado y guardado")
                                              st.write(resumen_texto)
                                              if st.button("Actualizar", key=f"refresh_{key_prefix}"):
                                                  st.rerun()
                                          else:
                                              st.error("No se pudo guardar el resumen")
                                      else:
                                          st.error("El flujo no devolvió un resumen")
                                  else:
                                      st.error(f"Error n8n: {resp.status_code} - {resp.text}")
                              except Exception as e:
                                  # Registrar error en métricas
                                  registrar_metrica_n8n(
                                      endpoint="resumen_virtual",
                                      tiempo_respuesta=0,
                                      estado="error",
                                      detalles=f"Excepción: {str(e)}",
                                      reunion_id=reunion_id
                                  )
                                  st.error(f"Error solicitando resumen: {e}")
                  elif tipo_val == "presencial":
                      # Verificar si ya existe un resumen para esta reunión
                      resumen_existente = sb_select("resumenes", {"select": "id,resumen,fecha_creacion", "reunion_id": f"eq.{reunion_id}"})
                      
                      if resumen_existente and resumen_existente[0].get("resumen"):
                          # Mostrar el resumen existente
                          item = resumen_existente[0]
                          subtitulo_pagina("resumen", "Resumen existente")
                          st.write(item.get("resumen"))
                          if item.get("fecha_creacion"):
                              st.caption(f"Creado: {item['fecha_creacion'].replace('T',' ').replace('Z','')}")
                      else:
                          # Mostrar opción para subir PDF solo si no hay resumen
                          archivo_pdf = st.file_uploader("Sube el acta (PDF)", type=["pdf"], key=f"pdf_{key_prefix}")
                          if archivo_pdf is not None:
                              st.success(f"Archivo cargado: {archivo_pdf.name}")
                          btnp = st.button("Procesar PDF y generar resumen", key=f"genpdf_{key_prefix}")
                          if btnp:
                              if not N8N_RESUMEN_PRESENCIAL_URL:
                                  st.error("Configura N8N_RESUMEN_PRESENCIAL_WEBHOOK_URL en .env")
                              elif not archivo_pdf:
                                  st.warning("Primero sube un PDF")
                              else:
                                  try:
                                      inicio = time.time()
                                      with st.spinner("Procesando acta y esperando resumen..."):
                                          # Enviar PDF al flujo n8n
                                          files = {"file": (archivo_pdf.name, archivo_pdf.getvalue(), "application/pdf")}
                                          data_form = {"reunion_id": reunion_id, "nombre_archivo": archivo_pdf.name}
                                          
                                          # Realizar la petición y medir tiempo
                                          inicio_request = time.time()
                                          resp = requests.post(N8N_RESUMEN_PRESENCIAL_URL, files=files, data=data_form, timeout=180)
                                          tiempo_respuesta = time.time() - inicio_request
                                          
                                          # Registrar métrica básica
                                          registrar_metrica_n8n(
                                              endpoint="resumen_presencial",
                                              tiempo_respuesta=tiempo_respuesta,
                                              estado="en_proceso" if resp.status_code == 200 else "error",
                                              codigo_estado=resp.status_code,
                                              reunion_id=reunion_id
                                          )

                                          # Iniciar seguimiento del tiempo total de procesamiento
                                          inicio_procesamiento = time.time()
                                          encontrado = False
                                          deadline = time.time() + 120  # hasta 2 minutos de espera
                                          
                                          while time.time() < deadline and not encontrado:
                                              try:
                                                  poll = sb_select("resumenes", {
                                                      "select": "id,reunion_id,resumen,fecha_creacion", 
                                                      "reunion_id": f"eq.{reunion_id}"
                                                  })
                                                  if poll and (poll[0].get("resumen") or "").strip():
                                                      item = poll[0]
                                                      tiempo_total = time.time() - inicio
                                                      
                                                      # Actualizar métrica con resultado exitoso
                                                      registrar_metrica_n8n(
                                                          endpoint="resumen_presencial",
                                                          tiempo_respuesta=tiempo_total,
                                                          estado="éxito",
                                                          codigo_estado=200,
                                                          reunion_id=reunion_id,
                                                          detalles=f"Tiempo total de procesamiento: {tiempo_total:.2f}s"
                                                      )
                                                      
                                                      st.success("Resumen generado y guardado")
                                                      st.markdown("**Resumen**")
                                                      st.write(item.get("resumen"))
                                                      if item.get("fecha_creacion"):
                                                          st.caption(f"Creado: {item['fecha_creacion'].replace('T',' ').replace('Z','')}")
                                                      encontrado = True
                                                      break
                                              except Exception as e:
                                                  print(f"Error al consultar resumen: {e}")
                                              time.sleep(3)

                                          if not encontrado:
                                              tiempo_total = time.time() - inicio
                                              registrar_metrica_n8n(
                                                  endpoint="resumen_presencial",
                                                  tiempo_respuesta=tiempo_total,
                                                  estado="timeout",
                                                  reunion_id=reunion_id,
                                                  detalles="Tiempo de espera agotado esperando el resumen"
                                              )
                                              st.warning("Aún no se genera el resumen. Por favor, espera unos segundos y vuelve a intentar actualizar.")
                                  
                                  except requests.exceptions.Timeout:
                                      tiempo_total = time.time() - inicio
                                      registrar_metrica_n8n(
                                          endpoint="resumen_presencial",
                                          tiempo_respuesta=tiempo_total,
                                          estado="timeout",
                                          reunion_id=reunion_id,
                                          detalles="Timeout en la petición a n8n"
                                      )
                                      st.error("Tiempo de espera agotado")
                                  except Exception as e:
                                      tiempo_total = time.time() - inicio
                                      registrar_metrica_n8n(
                                          endpoint="resumen_presencial",
                                          tiempo_respuesta=tiempo_total,
                                          estado="error",
                                          reunion_id=reunion_id,
                                          detalles=f"Excepción: {str(e)}"
                                      )
                                      st.error(f"Error al procesar el PDF: {e}")

    df_v = df_total[df_total["tipo"] == "virtual"]
    df_p = df_total[df_total["tipo"] == "presencial"]
    df_m = df_total[df_total["tipo"] == "mixta"]

    render_columna(col_v, df_v, "Virtual", "virtual")
    render_columna(col_p, df_p, "Presencial", "presencial")
    render_columna(col_m, df_m, "Mixta", "mixta")

# -------- Participantes --------
def view_participantes():
    titulo_pagina("usuarios", "Participantes de Reuniones")
    admin = is_admin()

    opciones = {}
    try:
        lista = sb_select("reuniones", {"select": "id,tema,fecha_inicio,tipo"})
        for r in lista:
            label = f"{r.get('tema','(Sin tema)')} — {str(r.get('fecha_inicio') or '').replace('T',' ').replace('Z','')} ({r.get('tipo','')}) (ID {r.get('id')})"
            opciones[label] = r.get("id")
    except Exception:
        lista = []

    opciones_list = ["— Selecciona —"] + list(opciones.keys())
    sel_val = st.selectbox("Escoge una reunión", opciones_list, key="sel_participantes")
    input_id = st.text_input("ID de reunión", placeholder="Ingresa el ID de una reunión", key="id_participantes")

    chosen_id = None
    if sel_val and sel_val != "— Selecciona —":
        chosen_id = opciones[sel_val]
    if input_id:
        chosen_id = input_id

    if not chosen_id:
        st.info("Selecciona una reunión o ingresa un ID para ver participantes.")
        return
    
    try:
        participantes = sb_select(
            "participantes",
            {"select":"id,usuario_id,correo,rol,estado_invitacion,fecha_creacion,reunion_id",
             "reunion_id": f"eq.{chosen_id}"}
        )
    except Exception as e:
        st.error(f"Error cargando participantes: {e}")
        return

    # Si no hay participantes
    if not participantes:
        st.warning("No hay participantes registrados en esta reunión aún.")
    else:
        # Convertir fecha
        for p in participantes:
            p["fecha_creacion"] = p["fecha_creacion"].replace("T"," ").replace("Z","")

        df = pd.DataFrame(participantes)

        st.subheader("Lista de Participantes")

        if DEMO_MODE:
            # Evita el editor Arrow en Python 3.13 durante la demostración local.
            # La aplicación productiva conserva el editor completo.
            display_cols = ["correo", "rol", "estado_invitacion", "fecha_creacion"]
            st.markdown(df[display_cols].to_html(index=False), unsafe_allow_html=True)
            edited_df = df.copy()
        else:
            # Pequeño gráfico de estado de invitaciones (donut)
            try:
                cdata = df.groupby("estado_invitacion").size().reset_index(name="conteo")
                chart = alt.Chart(cdata).mark_arc(innerRadius=40).encode(
                    theta=alt.Theta("conteo:Q", stack=True),
                    color=alt.Color("estado_invitacion:N", scale=alt.Scale(scheme="pastel2")),
                    tooltip=["estado_invitacion:N","conteo:Q"]
                ).properties(height=180)
                st.altair_chart(chart, use_container_width=True)
            except Exception:
                pass

            edited_df = st.data_editor(
                df,
                use_container_width=True,
                key="tabla_participantes",
                hide_index=True,
                column_config={
                    "correo": st.column_config.TextColumn("Correo"),
                    "rol": st.column_config.SelectboxColumn("Rol", options=["participante","organizador"]),
                    "estado_invitacion": st.column_config.SelectboxColumn(
                        "Estado", 
                        options=["enviado","aceptado","rechazado"]
                    ),
                    "fecha_creacion": st.column_config.DatetimeColumn("Registrado")
                },
                disabled=[
                    "id","reunion_id","usuario_id","fecha_creacion",
                    *([] if admin else ["correo","rol","estado_invitacion"])
                ]
            )

        # Guardar cambios
        if admin and st.button("Guardar cambios participante(s)"):
            for i, row in edited_df.iterrows():
                original = next(p for p in participantes if p["id"] == row["id"])
                if dict(row) != original:
                    try:
                        requests.patch(
                            f"{SUPABASE_URL}/rest/v1/participantes",
                            headers={**HEADERS,"Prefer":"return=representation"},
                            params={"id": f"eq.{row['id']}"},
                            data=json.dumps({
                                "correo": row["correo"],
                                "rol": row["rol"],
                                "estado_invitacion": row["estado_invitacion"]
                            })
                        )
                    except Exception as e:
                        st.error(f"Error actualizando {row['correo']}: {e}")
            st.success("Cambios guardados")
            st.rerun()

        # Eliminar participante
        if admin:
            subtitulo_pagina("eliminar", "Eliminar participante")
            del_id = st.text_input("ID de participante a eliminar")

            if st.button("Eliminar participante"):
                try:
                    requests.delete(
                        f"{SUPABASE_URL}/rest/v1/participantes",
                        headers=HEADERS,
                        params={"id":f"eq.{del_id}"}
                    )
                    st.success("Participante eliminado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    if admin:
        subtitulo_pagina("agregar", "Agregar nuevo participante")

        new_email = st.text_input("Correo del participante")
        new_rol = st.selectbox("Rol", ["participante","organizador"])

        if st.button("Agregar participante"):
            if not new_email:
                st.warning("Ingresa un email.")
                return
            try:
                sb_insert("participantes", [{
                    "reunion_id": chosen_id,
                    "correo": new_email,
                    "rol": new_rol,
                    "estado_invitacion": "enviado"
                }])
                st.success("Participante agregado")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


# -------- Tareas --------
def view_tareas():
    titulo_pagina("tareas", "Gestión de Tareas")
    admin = is_admin()
    
    # -------- Obtener tareas con información de reunión --------
    try:
        # Obtener tareas con información de reunión
        tareas = sb_select("tareas", {
            "select": "id,reunion_id,descripcion,asignado_a_correo,estado,fecha_vencimiento,fecha_creacion"
        })
        
        # Obtener información de reuniones
        if tareas:
            # Obtener IDs únicos de reuniones
            reuniones_ids = list(set(t['reunion_id'] for t in tareas))
            
            # Obtener información de reuniones en lotes si hay muchas
            reuniones_info = {}
            for i in range(0, len(reuniones_ids), 10):  # Procesar en lotes de 10
                batch = reuniones_ids[i:i+10]
                params = {
                    "select": "id,tema,fecha_inicio",
                    "id": f"in.({','.join(str(r) for r in batch)})"
                }
                reuniones_batch = sb_select("reuniones", params)
                reuniones_info.update({r['id']: f"{r['tema']} ({r['fecha_inicio'][:10]})" for r in reuniones_batch})
            
            # Agregar nombre de reunión a cada tarea
            for tarea in tareas:
                tarea['reunion_nombre'] = reuniones_info.get(tarea['reunion_id'], 'Reunión desconocida')
    except Exception as e:
        st.error(f"Error cargando tareas: {e}")
        return
    
    if not tareas:
        st.info("No hay tareas registradas todavía. Cree la primera con el formulario de abajo (administradores) o desde los acuerdos de una reunión.")
        if admin:
            st.divider()
            subtitulo_pagina("agregar", "Crear nueva tarea")
            with st.form("nueva_tarea"):
                try:
                    reuniones = sb_select("reuniones", {"select": "id,tema,fecha_inicio", "order": "fecha_inicio.desc", "limit": "50"})
                    opciones_reuniones = {f"{r['tema']} ({r['fecha_inicio'][:10]})": r['id'] for r in reuniones}
                    reunion_sel = st.selectbox("Reunión", list(opciones_reuniones.keys()))
                    descripcion = st.text_area("Descripción de la tarea")
                    asignado = st.text_input("Asignado a (correo)")
                    estado = st.selectbox("Estado", ["pendiente", "en_progreso", "completada"])
                    fecha_venc = st.date_input("Fecha de vencimiento")
                    submit = st.form_submit_button("Crear tarea")
                    
                    if submit:
                        if not descripcion:
                            st.warning("Ingresa una descripción")
                        else:
                            sb_insert("tareas", [{
                                "reunion_id": opciones_reuniones[reunion_sel],
                                "descripcion": descripcion,
                                "asignado_a_correo": asignado if asignado else None,
                                "estado": estado,
                                "fecha_vencimiento": fecha_venc.isoformat()
                            }])
                            st.success("Tarea creada")
                            st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        return
    
    # Formatear fechas y asegurar que los valores no sean None
    from datetime import datetime
    for t in tareas:
        # Asegurar que todos los campos tengan un valor por defecto si son None
        t["descripcion"] = t.get("descripcion") or "Sin descripción"
        t["asignado_a_correo"] = t.get("asignado_a_correo") or "No asignado"
        t["estado"] = t.get("estado") or "pendiente"
        
        # Formatear fechas
        if t.get("fecha_vencimiento"):
            t["fecha_vencimiento"] = t["fecha_vencimiento"].replace("T", " ").split("+")[0].split("Z")[0][:10]
        else:
            t["fecha_vencimiento"] = "Sin fecha"
            
        if t.get("fecha_creacion"):
            t["fecha_creacion"] = t["fecha_creacion"].replace("T", " ").split("+")[0].split("Z")[0]
        else:
            t["fecha_creacion"] = "Desconocida"
    
    # Crear DataFrame asegurando que todos los campos necesarios existan
    df = pd.DataFrame(tareas)
    
    # Asegurarse de que las columnas necesarias existan
    columnas_necesarias = ["descripcion", "asignado_a_correo", "estado", "fecha_vencimiento", "fecha_creacion", "reunion_nombre"]
    for col in columnas_necesarias:
        if col not in df.columns:
            df[col] = ""  # O un valor por defecto apropiado
    
    # -------- PANEL DE MÉTRICAS --------
    subtitulo_pagina("metricas", "Métricas Generales")
    
    total_tareas = len(df)
    completadas = len(df[df["estado"] == "completada"])
    pendientes = len(df[df["estado"] == "pendiente"])
    en_progreso = len(df[df["estado"] == "en_progreso"])
    
    # Calcular atrasadas (fecha_vencimiento < hoy y estado != completada)
    hoy = datetime.now().date()
    df_copy = df.copy()
    df_copy["fecha_venc_dt"] = pd.to_datetime(df_copy["fecha_vencimiento"], errors="coerce")
    atrasadas = len(df_copy[
        (df_copy["fecha_venc_dt"].dt.date < hoy) & 
        (df_copy["estado"] != "completada")
    ])
    
    # Porcentaje de avance
    porcentaje_avance = (completadas / total_tareas * 100) if total_tareas > 0 else 0
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Tareas", total_tareas)
    col2.metric("Completadas", completadas, delta=f"{porcentaje_avance:.1f}%")
    col3.metric("Pendientes", pendientes)
    col4.metric("En Progreso", en_progreso)
    col5.metric("Atrasadas", atrasadas, delta="Revisar" if atrasadas > 0 else "Al día")
    col6.metric("% Avance", f"{porcentaje_avance:.1f}%")
    
    st.divider()
    
    # -------- GRÁFICOS ESTADÍSTICOS --------
    subtitulo_pagina("grafico", "Análisis Estadístico")
    
    colg1, colg2, colg3 = st.columns(3)
    
    # Gráfico 1: Tareas por estado
    with colg1:
        st.caption("Tareas por Estado")
        try:
            estado_data = df.groupby("estado").size().reset_index(name="cantidad")
            chart = alt.Chart(estado_data).mark_bar().encode(
                x=alt.X("estado:N", title="Estado", sort="-y"),
                y=alt.Y("cantidad:Q", title="Cantidad"),
                color=alt.Color("estado:N", scale=alt.Scale(
                    domain=["pendiente", "en_progreso", "completada"],
                    range=["#ff6b6b", "#ffd93d", "#6bcf7f"]
                )),
                tooltip=["estado:N", "cantidad:Q"]
            ).properties(height=250)
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            st.write("—")
    
    # Gráfico 2: Tareas por usuario asignado
    with colg2:
        st.caption("Tareas por Usuario Asignado")
        try:
            df_asignadas = df[df["asignado_a_correo"].notna()].copy()
            if not df_asignadas.empty:
                usuario_data = df_asignadas.groupby("asignado_a_correo").size().reset_index(name="cantidad")
                # Tomar top 10
                usuario_data = usuario_data.nlargest(10, "cantidad")
                chart = alt.Chart(usuario_data).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta("cantidad:Q", stack=True),
                    color=alt.Color("asignado_a_correo:N", legend=None),
                    tooltip=["asignado_a_correo:N", "cantidad:Q"]
                ).properties(height=250)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.write("Sin tareas asignadas")
        except Exception:
            st.write("—")
    
    # Gráfico 3: Creación de tareas por semana
    with colg3:
        st.caption("Creación de Tareas por Semana")
        try:
            df_fechas = df.copy()
            df_fechas["fecha_creacion_dt"] = pd.to_datetime(df_fechas["fecha_creacion"], errors="coerce")
            df_fechas = df_fechas.dropna(subset=["fecha_creacion_dt"])
            df_fechas["semana"] = df_fechas["fecha_creacion_dt"].dt.to_period("W").astype(str)
            semana_data = df_fechas.groupby("semana").size().reset_index(name="cantidad")
            
            chart = alt.Chart(semana_data).mark_line(point=True, color="#4a90e2").encode(
                x=alt.X("semana:N", title="Semana"),
                y=alt.Y("cantidad:Q", title="Tareas Creadas"),
                tooltip=["semana:N", "cantidad:Q"]
            ).properties(height=250)
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            st.write("—")
    
    st.divider()
    
    # -------- FILTROS --------
    subtitulo_pagina("buscar", "Filtros y Búsqueda")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        filtro_busqueda = st.text_input("Buscar en tareas/reuniones", placeholder="Escribe para buscar...")
    
    with col_f2:
        filtro_estado = st.selectbox("Estado", ["Todos", "pendiente", "en_progreso", "completada"])
    
    with col_f3:
        # Obtener lista de correos únicos (quitando valores nulos)
        correos_unicos = [x for x in df["asignado_a_correo"].dropna().unique() if x]
        filtro_asignado = st.selectbox(
            "Asignado a",
            ["Todos"] + sorted(correos_unicos, key=str.lower)
        )
        
    with col_f4:
        # Obtener reuniones únicas para el filtro
        reuniones_unicas = ["Todas"] + sorted(df["reunion_nombre"].unique().tolist())
        filtro_reunion = st.selectbox(
            "Reunión",
            reuniones_unicas
        )
    
    # Obtener lista de reuniones únicas para el filtro
    reuniones_unicas = df['reunion_nombre'].unique()
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    # Filtro de búsqueda
    if filtro_busqueda:
        df_filtrado = df_filtrado[
            df_filtrado["descripcion"].str.contains(filtro_busqueda, case=False, na=False) |
            df_filtrado["reunion_nombre"].str.contains(filtro_busqueda, case=False, na=False)
        ]
    
    # Filtro de estado
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["estado"] == filtro_estado]
    
    # Filtro de asignado
    if filtro_asignado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["asignado_a_correo"] == filtro_asignado]
    
    # Convertir fechas a formato datetime
    df_filtrado['fecha_vencimiento'] = pd.to_datetime(df_filtrado['fecha_vencimiento'], errors='coerce').dt.date
    
    # Ordenar por fecha de vencimiento
    df_filtrado = df_filtrado.sort_values(by="fecha_vencimiento", ascending=True)
    
    st.caption(f"Mostrando {len(df_filtrado)} de {len(df)} tareas")
    
    # -------- TABLA DE TAREAS --------
    subtitulo_pagina("lista", "Tabla de Tareas")
    
    # Configuración de columnas
    column_config = {
        "reunion_id": st.column_config.TextColumn("ID Reunión", width="medium"),
        "reunion_nombre": st.column_config.TextColumn("Reunión", width="large"),
        "descripcion": st.column_config.TextColumn("Tarea", width="xlarge"),
        "asignado_a_correo": st.column_config.TextColumn("Asignado a", width="medium"),
        "estado": st.column_config.SelectboxColumn(
            "Estado",
            options=["pendiente", "en_progreso", "completada"],
            width="small"
        ),
        "fecha_vencimiento": st.column_config.DateColumn("Vencimiento", format="DD/MM/YYYY", width="small"),
        "fecha_creacion": st.column_config.DatetimeColumn("Creación", format="DD/MM/YYYY HH:mm", width="medium"),
        "id": None  # Ocultar columna ID
    }
    
    # Ordenar columnas para mejor visualización
    column_order = [
        'reunion_id', 'reunion_nombre', 'descripcion', 'asignado_a_correo', 
        'estado', 'fecha_vencimiento', 'fecha_creacion'
    ]
    
    # Asegurarse de que todas las columnas existan en el DataFrame
    column_order = [col for col in column_order if col in df_filtrado.columns]
    
    # Aplicar filtro de reunión si se seleccionó una específica
    if 'filtro_reunion' in locals() and filtro_reunion != "Todas":
        df_filtrado = df_filtrado[df_filtrado['reunion_nombre'] == filtro_reunion]
    
    # Asegurarse de que no haya valores NaN en las columnas clave
    for col in ['descripcion', 'asignado_a_correo', 'estado', 'reunion_nombre']:
        if col in df_filtrado.columns:
            df_filtrado[col] = df_filtrado[col].fillna('' if col != 'estado' else 'pendiente')
    
    # Mostrar el editor de datos
    try:
        # Para admin: puede editar todo excepto reunion_nombre y fecha_creacion
        # Para usuario regular: solo puede editar estado
        if admin:
            disabled_cols = ["reunion_nombre", "fecha_creacion", "reunion_id"]
        else:
            # Usuario regular solo puede editar estado
            disabled_cols = [col for col in column_order if col != "estado"]
        
        edited_df = st.data_editor(
            df_filtrado[column_order],
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
            disabled=disabled_cols,
            height=min(600, 100 + len(df_filtrado) * 35),  # Altura dinámica
            key=f"tareas_editor_{len(df_filtrado)}"  # Clave única para forzar actualización
        )
    except Exception as e:
        st.error(f"Error al mostrar la tabla de tareas: {str(e)}")
        # Mostrar los datos en formato de tabla simple como respaldo
        st.dataframe(df_filtrado[column_order], use_container_width=True)
    
    # -------- EXPORTAR PDF --------
    st.divider()
    col_exp1, col_exp2 = st.columns([1, 3])
    with col_exp1:
        if st.button("Exportar a PDF"):
            try:
                # Preparar DataFrame para PDF (convertir fechas a string)
                df_pdf = df_filtrado.copy()
                if 'fecha_vencimiento' in df_pdf.columns:
                    df_pdf['fecha_vencimiento'] = df_pdf['fecha_vencimiento'].astype(str)
                
                pdf_bytes = tareas_to_pdf_bytes("Reporte de Tareas", df_pdf)
                st.session_state["tareas_pdf_bytes"] = pdf_bytes
                st.success("PDF generado")
            except Exception as e:
                st.error(f"Error generando PDF: {e}")
    with col_exp2:
        if "tareas_pdf_bytes" in st.session_state:
            st.download_button(
                label="⬇️ Descargar reporte PDF",
                data=st.session_state["tareas_pdf_bytes"],
                file_name=f"tareas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )
    
    # -------- GUARDAR CAMBIOS --------
    st.divider()
    
    # Crear un mapeo de índice a ID para encontrar las tareas originales
    id_map = {i: row['id'] for i, row in df_filtrado.reset_index(drop=True).iterrows()}
    
    if admin:
        # Admin puede guardar todos los cambios
        if st.button("Guardar cambios", type="primary", use_container_width=True):
            cambios_realizados = 0
            for i, row in edited_df.iterrows():
                # Obtener el ID de la tarea desde el mapeo
                tarea_id = id_map.get(i)
                if not tarea_id:
                    continue
                    
                original = next((t for t in tareas if t["id"] == tarea_id), None)
                if not original:
                    continue
                    
                updates = {}
                
                # Verificar cambios en el estado
                if "estado" in row and row["estado"] != original.get("estado"):
                    updates["estado"] = row["estado"]
                    
                # Verificar cambios en el asignado
                if "asignado_a_correo" in row and row["asignado_a_correo"] != original.get("asignado_a_correo"):
                    updates["asignado_a_correo"] = row["asignado_a_correo"] if pd.notna(row["asignado_a_correo"]) else None
                    
                # Verificar cambios en la descripción
                if "descripcion" in row and row["descripcion"] != original.get("descripcion"):
                    updates["descripcion"] = row["descripcion"]
                
                # Verificar cambios en fecha de vencimiento
                if "fecha_vencimiento" in row:
                    fecha_nueva = str(row["fecha_vencimiento"]) if pd.notna(row["fecha_vencimiento"]) else None
                    fecha_original = original.get("fecha_vencimiento", "")[:10] if original.get("fecha_vencimiento") else None
                    if fecha_nueva != fecha_original:
                        updates["fecha_vencimiento"] = fecha_nueva
                
                # Si hay cambios, actualizar
                if updates:
                    try:
                        response = requests.patch(
                            f"{SUPABASE_URL}/rest/v1/tareas",
                            headers={
                                **HEADERS, 
                                "Prefer": "return=representation",
                                "Content-Type": "application/json"
                            },
                            params={"id": f"eq.{tarea_id}"},
                            data=json.dumps(updates)
                        )
                        response.raise_for_status()
                        cambios_realizados += 1
                    except Exception as e:
                        st.error(f"Error actualizando tarea {tarea_id}: {str(e)}")
                        continue
                        
            if cambios_realizados > 0:
                st.success(f"{cambios_realizados} tarea(s) actualizada(s)")
                st.rerun()
            else:
                st.info("No hay cambios para guardar")
    else:
        # Usuario regular solo puede cambiar estado
        if st.button("Guardar cambios de estado", type="primary", use_container_width=True):
            cambios_realizados = 0
            for i, row in edited_df.iterrows():
                # Obtener el ID de la tarea desde el mapeo
                tarea_id = id_map.get(i)
                if not tarea_id:
                    continue
                    
                original = next((t for t in tareas if t["id"] == tarea_id), None)
                if not original:
                    continue
                
                # Solo verificar cambios en el estado
                if "estado" in row and row["estado"] != original.get("estado"):
                    try:
                        response = requests.patch(
                            f"{SUPABASE_URL}/rest/v1/tareas",
                            headers={
                                **HEADERS, 
                                "Prefer": "return=representation",
                                "Content-Type": "application/json"
                            },
                            params={"id": f"eq.{tarea_id}"},
                            data=json.dumps({"estado": row["estado"]})
                        )
                        response.raise_for_status()
                        cambios_realizados += 1
                    except Exception as e:
                        st.error(f"Error actualizando tarea {tarea_id}: {str(e)}")
                        continue
            
            if cambios_realizados > 0:
                st.success(f"{cambios_realizados} tarea(s) actualizada(s)")
                st.rerun()
            else:
                st.info("No hay cambios de estado para guardar")
    
    # -------- CREAR NUEVA TAREA --------
    if admin:
        st.divider()
        subtitulo_pagina("agregar", "Crear nueva tarea")
        
        with st.form("nueva_tarea"):
            try:
                reuniones = sb_select("reuniones", {
                    "select": "id,tema,fecha_inicio",
                    "order": "fecha_inicio.desc",
                    "limit": "50"
                })
                opciones_reuniones = {f"{r['tema']} ({r['fecha_inicio'][:10]})": r['id'] for r in reuniones}
                
                reunion_sel = st.selectbox("Reunión", list(opciones_reuniones.keys()))
                descripcion = st.text_area("Descripción de la tarea", height=100)
                
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    asignado = st.text_input("Asignado a (correo)")
                with col_a2:
                    estado = st.selectbox("Estado", ["pendiente", "en_progreso", "completada"])
                
                fecha_venc = st.date_input("Fecha de vencimiento")
                submit = st.form_submit_button("Crear tarea", use_container_width=True)
                
                if submit:
                    if not descripcion:
                        st.warning("Ingresa una descripción")
                    else:
                        sb_insert("tareas", [{
                            "reunion_id": opciones_reuniones[reunion_sel],
                            "descripcion": descripcion,
                            "asignado_a_correo": asignado if asignado else None,
                            "estado": estado,
                            "fecha_vencimiento": fecha_venc.isoformat()
                        }])
                        st.success("Tarea creada")
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


# -------- Estadísticas --------
def view_estadisticas():
    titulo_pagina("metricas", "Estadísticas")

    # Reuniones base
    try:
        reuniones = sb_select("reuniones", {"select": "id,tema,fecha_inicio,tipo,estado,duracion_minutos,creador_id"})
    except Exception as e:
        st.error(f"Error cargando reuniones: {e}")
        reuniones = []

    df_r = pd.DataFrame(reuniones)
    if not df_r.empty:
        if "fecha_inicio" in df_r.columns:
            df_r["fecha_dt"] = pd.to_datetime(df_r["fecha_inicio"], errors="coerce")
        else:
            df_r["fecha_dt"] = pd.NaT
        df_r["tipo"] = df_r.get("tipo", pd.Series(dtype=str)).astype(str).str.lower()
        df_r["estado"] = df_r.get("estado", pd.Series(dtype=str)).astype(str).str.lower()

        # Filtros de fecha
        min_date = df_r["fecha_dt"].min()
        max_date = df_r["fecha_dt"].max()
        if pd.isna(min_date) or pd.isna(max_date):
            rango = st.date_input("Rango de fechas", value=None)
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                fi = st.date_input("Desde", value=min_date.date())
            with col_f2:
                ff = st.date_input("Hasta", value=max_date.date())
            mask = (df_r["fecha_dt"].dt.date >= fi) & (df_r["fecha_dt"].dt.date <= ff)
            df_r = df_r[mask]

        # Métricas rápidas
        total_reu = len(df_r)
        dur_total = int(df_r.get("duracion_minutos", pd.Series(dtype=int)).fillna(0).sum()) if not df_r.empty else 0
        dur_prom = int(df_r.get("duracion_minutos", pd.Series(dtype=int)).fillna(0).mean()) if total_reu > 0 else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Reuniones", f"{total_reu}")
        c2.metric("Duración total (min)", f"{dur_total}")
        c3.metric("Duración promedio (min)", f"{dur_prom}")

        # Reuniones por mes
        st.subheader("Reuniones por mes")
        if not df_r.empty:
            df_r["ym"] = df_r["fecha_dt"].dt.to_period("M").astype(str)
            by_month = df_r.groupby("ym").size().reset_index(name="reuniones")
            by_month = by_month.sort_values("ym")
            st.bar_chart(by_month.set_index("ym"))

        # Por tipo y por estado
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Reuniones por tipo")
            if not df_r.empty:
                by_tipo = df_r.groupby("tipo").size().reset_index(name="reuniones")
                st.bar_chart(by_tipo.set_index("tipo"))
        with col_b:
            st.subheader("Reuniones por estado")
            if not df_r.empty:
                by_estado = df_r.groupby("estado").size().reset_index(name="reuniones")
                st.bar_chart(by_estado.set_index("estado"))

        # Duración promedio por tipo
        st.subheader("Duración promedio por tipo (min)")
        if not df_r.empty and "duracion_minutos" in df_r.columns:
            dur_tipo = df_r.groupby("tipo")["duracion_minutos"].mean().reset_index()
            st.bar_chart(dur_tipo.set_index("tipo"))

    # Participantes por reunión y estado de invitaciones
    try:
        partes = sb_select("participantes", {"select":"id,reunion_id,estado_invitacion"})
    except Exception:
        partes = []
    df_p = pd.DataFrame(partes)
    if not df_p.empty:
        st.subheader("Top 10 reuniones por número de participantes")
        top = df_p.groupby("reunion_id").size().reset_index(name="participantes").sort_values("participantes", ascending=False).head(10)
        st.bar_chart(top.set_index("reunion_id"))

        st.subheader("Estado de invitaciones")
        by_inv = df_p.groupby("estado_invitacion").size().reset_index(name="conteo")
        st.bar_chart(by_inv.set_index("estado_invitacion"))

    # Resúmenes: cobertura
    try:
        res = sb_select("resumenes", {"select":"id,reunion_id,fecha_creacion"})
    except Exception:
        res = []
    df_s = pd.DataFrame(res)
    if not df_s.empty and not df_r.empty:
        st.subheader("Cobertura de resúmenes")
        reuniones_con_resumen = df_s["reunion_id"].nunique()
        total_reu_base = len(df_r)
        cobertura = (reuniones_con_resumen / total_reu_base * 100) if total_reu_base > 0 else 0
        cc1, cc2 = st.columns(2)
        cc1.metric("Reuniones con resumen", f"{reuniones_con_resumen}")
        cc2.metric("Cobertura (%)", f"{cobertura:.1f}%")

        # Cobertura por tipo
        m = df_r[["id","tipo"]].merge(df_s, left_on="id", right_on="reunion_id", how="left")
        has_res = m.groupby("tipo").apply(lambda g: g["reunion_id"].notna().mean()*100 if len(g)>0 else 0).reset_index(name="cobertura_%")
        st.bar_chart(has_res.set_index("tipo"))

# -------- Métricas y Análisis --------
def view_metricas():
    titulo_pagina("metricas", "Métricas y Estadísticas")
    st.markdown("---")
    
    try:
        # Obtener las métricas de la base de datos
        metricas = sb_select("metricas_n8n", {
            "select": "*",
            "order": "fecha.desc",
            "limit": "1000"  # Últimos 1000 registros
        })
        
        if not metricas:
            st.info("No hay métricas registradas aún. Realiza algunas acciones para ver las estadísticas.")
            return
            
        # Convertir a DataFrame para facilitar el análisis
        df = pd.DataFrame(metricas)
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Mostrar filtros en la barra lateral
        st.sidebar.header("Filtros")
        
        # Filtro de fechas
        fecha_min = df['fecha'].min().date()
        fecha_max = df['fecha'].max().date()
        
        # Asegurar que la fecha de inicio predeterminada esté dentro del rango permitido
        fecha_inicio_predeterminada = fecha_max - timedelta(days=min(30, (fecha_max - fecha_min).days))
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            fecha_inicio = st.date_input(
                "Fecha de inicio",
                value=min(fecha_inicio_predeterminada, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max
            )
        with col2:
            fecha_fin = st.date_input(
                "Fecha de fin",
                value=fecha_max,
                min_value=fecha_inicio,  # No permitir fechas anteriores a la fecha de inicio
                max_value=fecha_max
            )
        
        # Filtrar por rango de fechas
        df_filtrado = df[(df['fecha'].dt.date >= fecha_inicio) & 
                        (df['fecha'].dt.date <= fecha_fin)]
        
        if df_filtrado.empty:
            st.warning("No hay datos para el rango de fechas seleccionado.")
            return
            
        # Mostrar métricas generales
        subtitulo_pagina("grafico", "Resumen General")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total = len(df_filtrado)
            st.metric("Total de peticiones", total)
            
        with col2:
            exito = len(df_filtrado[df_filtrado['estado'] == 'éxito'])
            st.metric("Peticiones exitosas", f"{exito} ({exito/max(total,1)*100:.1f}%)")
            
        with col3:
            error = len(df_filtrado[df_filtrado['estado'] == 'error'])
            st.metric("Errores", f"{error} ({error/max(total,1)*100:.1f}%)")
        
        st.markdown("---")
        
        # Gráfico 1: Peticiones por día
        subtitulo_pagina("reuniones", "Peticiones por día")
        df_diario = df_filtrado.set_index('fecha').resample('D').size().reset_index(name='count')
        if not df_diario.empty:
            fig1 = px.line(df_diario, x='fecha', y='count', 
                          title='Evolución de peticiones a n8n',
                          labels={'count': 'Número de peticiones', 'fecha': 'Fecha'})
            st.plotly_chart(fig1, use_container_width=True)
        
        # Gráfico 2: Distribución por endpoint
        subtitulo_pagina("web", "Distribución por endpoint")
        df_endpoint = df_filtrado.groupby('endpoint').size().reset_index(name='count')
        if not df_endpoint.empty:
            fig2 = px.pie(df_endpoint, values='count', names='endpoint', 
                         title='Peticiones por tipo de endpoint',
                         hole=0.3)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Gráfico 3: Tiempo de respuesta por endpoint
        subtitulo_pagina("tiempo", "Tiempo de respuesta promedio")
        df_tiempo = df_filtrado.groupby('endpoint')['tiempo_respuesta'].agg(['mean', 'count']).reset_index()
        df_tiempo = df_tiempo.sort_values('mean', ascending=False)
        if not df_tiempo.empty:
            fig3 = px.bar(df_tiempo, x='endpoint', y='mean',
                         title='Tiempo de respuesta promedio por endpoint (segundos)',
                         labels={'mean': 'Tiempo (s)', 'endpoint': 'Endpoint', 'count': 'Número de peticiones'},
                         hover_data=['count'])
            st.plotly_chart(fig3, use_container_width=True)
        
        # Gráfico 4: Estado de las peticiones
        subtitulo_pagina("correcto", "Estado de las peticiones")
        df_estado = df_filtrado.groupby('estado').size().reset_index(name='count')
        if not df_estado.empty:
            fig4 = px.bar(df_estado, x='estado', y='count', color='estado',
                         title='Distribución por estado de las peticiones',
                         labels={'count': 'Número de peticiones', 'estado': 'Estado'})
            st.plotly_chart(fig4, use_container_width=True)
        
        # Tabla con los últimos registros
        subtitulo_pagina("lista", "Registros recientes")
        st.dataframe(df_filtrado[['fecha', 'endpoint', 'estado', 'tiempo_respuesta', 'detalles']]
                    .sort_values('fecha', ascending=False)
                    .head(20), 
                    use_container_width=True,
                    column_config={
                        'fecha': 'Fecha y Hora',
                        'endpoint': 'Endpoint',
                        'estado': 'Estado',
                        'tiempo_respuesta': 'Tiempo (s)',
                        'detalles': 'Detalles'
                    })
        
    except Exception as e:
        st.error(f"Error al cargar las métricas: {str(e)}")
        st.exception(e)


# -------- Inteligencia artificial --------
def view_inteligencia_artificial():
    titulo_pagina("ia", "Inteligencia artificial para reuniones")
    st.caption("Clasificación de actos de diálogo entrenada con el dataset público MRDA.")

    # El plan gratuito de Render duerme la API tras inactividad. Durante el
    # arranque en frío el proxy responde 502 de inmediato (no retiene la
    # conexión), por lo que hay que reintentar en bucle hasta que despierte
    # (~1-2 minutos por la carga de torch). El resultado exitoso se guarda en
    # la sesión: Streamlit rerenderiza en cada interacción y sin caché cada
    # clic dentro del módulo volvía a consultar la API.
    model_status = st.session_state.get("modelo_status_ok")
    ultimo_error = None
    if model_status is None:
        try:
            status = requests.get(f"{FASTAPI_URL}/model/status", timeout=8)
            status.raise_for_status()
            model_status = status.json()
        except Exception as exc:
            ultimo_error = exc
            with st.spinner("Despertando la API de predicción (arranque en frío, puede tardar 2-3 minutos)..."):
                limite = time.time() + 180
                while time.time() < limite:
                    time.sleep(8)
                    try:
                        status = requests.get(f"{FASTAPI_URL}/model/status", timeout=15)
                        status.raise_for_status()
                        model_status = status.json()
                        ultimo_error = None
                        break
                    except Exception as exc2:
                        ultimo_error = exc2
        if model_status is not None:
            st.session_state["modelo_status_ok"] = model_status

    if model_status is not None:
        if model_status.get("available"):
            metadata = model_status.get("metadata") or {}
            st.success(f"Modelo disponible: {metadata.get('model_name', 'sin nombre')} · artefacto HDF5 activo: {'sí' if model_status.get('h5_available') else 'no'}")
        else:
            st.warning(model_status.get("message", "Modelo no disponible"))
    else:
        st.info(f"La API no está accesible en {FASTAPI_URL}. Inicie FastAPI para realizar predicciones. Detalle: {ultimo_error}")

    tab_pred, tab_models, tab_eda, tab_cv, tab_reports = st.tabs([
        "Predicción", "Comparación de modelos", "EDA", "Validación y estadística", "Reportes"
    ])

    with tab_pred:
        text = st.text_area(
            "Intervención de una reunión",
            value="¿Puedes enviar el informe final mañana?",
            height=120,
            help="El modelo fue entrenado con MRDA (reuniones en inglés). Puede escribir en español: el texto se traduce automáticamente al inglés antes de clasificar.",
        )
        st.caption("Puede escribir en español o inglés. El corpus MRDA es en inglés, por lo que el texto en español se traduce automáticamente antes de la predicción.")
        if st.button("Clasificar intervención", type="primary"):
            try:
                texto_modelo = text
                traducido = False
                if parece_espanol(text):
                    try:
                        from deep_translator import GoogleTranslator
                        texto_modelo = GoogleTranslator(source="auto", target="en").translate(text) or text
                        traducido = texto_modelo != text
                    except Exception:
                        st.warning(
                            "No se pudo traducir automáticamente; se clasificará el texto original. "
                            "El modelo fue entrenado en inglés, por lo que la predicción puede ser poco fiable."
                        )
                try:
                    response = requests.post(f"{FASTAPI_URL}/predict", json={"text": texto_modelo}, timeout=20)
                    response.raise_for_status()
                except Exception:
                    # La API pudo dormirse mientras la página estaba abierta:
                    # reintentar en bucle mientras despierta.
                    with st.spinner("La API estaba dormida; despertándola (hasta 3 minutos)..."):
                        limite = time.time() + 180
                        response = None
                        while time.time() < limite:
                            time.sleep(8)
                            try:
                                response = requests.post(f"{FASTAPI_URL}/predict", json={"text": texto_modelo}, timeout=20)
                                response.raise_for_status()
                                break
                            except Exception:
                                response = None
                    if response is None:
                        raise RuntimeError("La API no respondió tras el arranque en frío. Intente nuevamente en un minuto.")
                result = response.json()
                if traducido:
                    st.caption(f"Traducción enviada al modelo (corpus MRDA en inglés): “{texto_modelo}”")
                colores_clase = {
                    "Declaración": ("rgba(59,130,246,0.14)", "#2563EB"),
                    "Pregunta": ("rgba(245,158,11,0.16)", "#D97706"),
                    "Pregunta declarativa": ("rgba(16,185,129,0.15)", "#059669"),
                    "Retroalimentación breve": ("rgba(74,222,128,0.20)", "#4ADE80"),
                    "Continuación / seguimiento": ("rgba(251,191,36,0.20)", "#FBBF24"),
                }
                fondo, borde = colores_clase.get(result["label"], ("rgba(37,99,235,0.14)", "#2563EB"))
                st.markdown(
                    f"""<div style="margin:10px 0 4px 0;">
                    <span class="pred-badge" style="background:{fondo}; border:1.5px solid {borde}; color:{borde};">{result['label']}</span>
                    <span style="margin-left:12px; color:#667085; font-weight:600;">confianza {result['confidence']:.1%}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
                probs = pd.DataFrame({"Clase": list(result["probabilities"].keys()), "Probabilidad": list(result["probabilities"].values())})
                st.bar_chart(probs.set_index("Clase"), color="#2563EB")
                st.caption(f"Modelo empleado: {result['model']} · artefacto {result.get('artifact_file', 'best_model.h5')}")
            except Exception as exc:
                st.error(f"No se pudo ejecutar la predicción: {exc}")

    with tab_models:
        path = PROJECT_ROOT / "reports" / "tables" / "comparacion_modelos.csv"
        if path.exists():
            frame = leer_csv_cacheado(str(path))
            st.dataframe(frame, use_container_width=True, hide_index=True)
            st.bar_chart(frame.set_index("modelo")[["f1_macro", "accuracy"]])
            best = frame.iloc[0]
            st.info(f"Mejor modelo por F1 macro: {best['modelo']} ({best['f1_macro']:.4f}).")
        else:
            st.warning("Todavía no existe la tabla comparativa.")

    with tab_eda:
        summary_path = PROJECT_ROOT / "reports" / "tables" / "eda_resumen.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Intervenciones", f"{summary['total_registros']:,}")
            c2.metric("Reuniones", summary["reuniones_unicas"])
            c3.metric("Hablantes", summary["hablantes_unicos"])
            c4.metric("Textos vacíos", summary["textos_vacios"])
        for filename, caption in [
            ("eda_distribucion_clases.png", "Distribución de clases"),
            ("eda_longitud_textos.png", "Longitud de intervenciones"),
            ("eda_heatmap_clases_split.png", "Mapa de calor por partición"),
            ("eda_palabras_frecuentes.png", "Palabras frecuentes"),
        ]:
            image = PROJECT_ROOT / "reports" / "figures" / filename
            if image.exists():
                st.image(str(image), caption=caption, use_container_width=True)

    with tab_cv:
        cv_path = PROJECT_ROOT / "reports" / "tables" / "validacion_cruzada_resumen.csv"
        friedman_path = PROJECT_ROOT / "reports" / "tables" / "prueba_friedman.csv"
        wilcoxon_path = PROJECT_ROOT / "reports" / "tables" / "wilcoxon_holm.csv"
        if cv_path.exists():
            st.subheader("Validación cruzada de 5 folds")
            st.dataframe(leer_csv_cacheado(str(cv_path)), use_container_width=True, hide_index=True)
        if friedman_path.exists():
            st.subheader("Prueba de Friedman")
            st.dataframe(leer_csv_cacheado(str(friedman_path)), use_container_width=True, hide_index=True)
        if wilcoxon_path.exists():
            st.subheader("Comparaciones Wilcoxon con corrección de Holm")
            st.dataframe(leer_csv_cacheado(str(wilcoxon_path)), use_container_width=True, hide_index=True)

    with tab_reports:
        report_dir = PROJECT_ROOT / "reports"
        available = [p for p in report_dir.iterdir() if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".xlsx"}]
        if not available:
            st.info("Los reportes finales aún no fueron generados.")
        for report in sorted(available):
            mime = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}[report.suffix.lower()]
            st.download_button(f"Descargar {report.name}", data=report.read_bytes(), file_name=report.name, mime=mime)

# -------- Router --------
token_invitacion = str(st.query_params.get("aceptar_invitacion", "") or "")
correo_invitacion = str(st.query_params.get("correo", "") or "").strip().lower()

if st.session_state.session is None and token_invitacion and correo_invitacion:
    view_aceptar_invitacion(correo_invitacion, token_invitacion)
elif st.session_state.session is None:
    st.markdown('<div class="auth-page-marker"></div>', unsafe_allow_html=True)
    panel_visual, panel_acceso = st.columns([1.66, 1], gap=None)
    with panel_visual:
        st.markdown(
            f"""
            <div class="auth-visual-panel" style="background-image:url('{LOGIN_REFERENCE_DATA_URI}');"></div>
            """,
            unsafe_allow_html=True,
        )
    with panel_acceso:
        st.markdown('<div class="auth-panel-marker"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="auth-brand">
                <img src="{LOGO_DATA_URI}" alt="Logo de VINCORA Meet">
                <div>
                    <div class="auth-wordmark">VINCORA</div>
                    <div class="auth-tagline">Conecta. Reúnete. Avanza.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        modo_registro = str(st.query_params.get("auth", "login")) == "register"
        if modo_registro:
            st.markdown(
                """
                <h1 class="auth-register-title">Crea tu cuenta</h1>
                <div class="auth-register-description">Regístrate para comenzar a reunirte con tu equipo.</div>
                """,
                unsafe_allow_html=True,
            )
            view_register(mostrar_titulo=False)
            st.markdown(
                '<div class="auth-register-prompt">¿Ya tienes una cuenta? <a href="?" target="_self">Inicia sesión</a></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <h1 class="auth-heading">Bienvenido de nuevo</h1>
                <div class="auth-description">Ingresa a tu cuenta para continuar</div>
                """,
                unsafe_allow_html=True,
            )
            view_login(mostrar_titulo=False)
            st.markdown('<div class="auth-divider">O continúa con</div>', unsafe_allow_html=True)
            if st.button("Continuar con Google", key="google_login", use_container_width=True):
                st.info("El inicio con Google se habilitará cuando se configure OAuth.")
            st.markdown(
                '<div class="auth-register-prompt">¿No tienes una cuenta? <a href="?auth=register" target="_self">Regístrate</a></div>',
                unsafe_allow_html=True,
            )
elif str(st.query_params.get("sala_previa", "") or ""):
    view_sala_previa(str(st.query_params.get("sala_previa", "") or ""))
else:
    admin = is_admin()
    nombre_usuario = st.session_state.session["nombre"]
    iniciales = "".join(p[0] for p in nombre_usuario.split()[:2]).upper() or "U"
    nivel_txt = st.session_state.session["nivel"] + (" · Admin" if admin else "")
    st.sidebar.markdown(
        f"""
        <div class="brand-box">
            <div class="brand-logo"><img src="{LOGO_DATA_URI}" alt="Logo de VINCORA Meet"></div>
            <div>
                <div class="brand-name">VINCORA Meet</div>
                <div class="brand-sub">Conecta. Reúnete. Avanza.</div>
            </div>
        </div>
        <div class="user-chip">
            <div class="user-avatar">{iniciales}</div>
            <div>
                <div class="user-name">{nombre_usuario}</div>
                <div class="user-level">{nivel_txt}</div>
            </div>
            <span class="user-chevron" aria-hidden="true"></span>
        </div>
        <div class="nav-label">NAVEGACIÓN</div>
        """,
        unsafe_allow_html=True,
    )
    opciones_menu = ["Inicio", "Chat", "Reuniones", "Tareas", "Resumen de reuniones", "Participantes", "Inteligencia artificial", "Métricas", "Cerrar sesión"]
    if admin:
        opciones_menu.insert(2, "Usuarios")

    destino_query = str(st.query_params.get("pagina", "") or "")
    if destino_query in opciones_menu:
        st.session_state["main_navigation"] = destino_query
        del st.query_params["pagina"]
    if st.session_state.get("main_navigation") not in opciones_menu:
        st.session_state["main_navigation"] = "Inicio"

    page = st.sidebar.radio("Navegación", opciones_menu, key="main_navigation")
    if page == "Inicio":
        view_inicio()
    elif page == "Chat":
        view_chat()
    elif page == "Usuarios":
        view_usuarios()
    elif page == "Reuniones":
        view_reuniones()
    elif page == "Tareas":
        view_tareas()
    elif page == "Resumen de reuniones":
        view_resumen_reuniones()
    elif page == "Participantes":
        view_participantes()
    elif page == "Inteligencia artificial":
        view_inteligencia_artificial()
    elif page == "Métricas":
        view_metricas()
    elif page == "Cerrar sesión":
        st.session_state.clear()
        st.rerun()
