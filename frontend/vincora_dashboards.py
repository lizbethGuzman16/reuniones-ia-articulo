"""Vistas operativas VINCORA inspiradas en las referencias, siempre con datos reales."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import pandas as pd
import plotly.express as px


def _head(st, icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""<div class="vx-head"><span>{icon}</span><div><h1>{escape(title)}</h1>
        <p>{escape(subtitle)}</p></div></div>""", unsafe_allow_html=True,
    )


def _css(st) -> None:
    st.markdown("""<style>
    .vx-head{display:flex;align-items:center;gap:18px;margin:4px 0 24px;color:#0b193e}.vx-head>span{font-size:40px;color:#1765ed}.vx-head h1{margin:0!important;font:800 34px/1.1 Segoe UI!important}.vx-head p{margin:8px 0 0;color:#65738d}
    .vx-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-bottom:20px}.vx-kpi{padding:22px;border:1px solid #dce4ef;border-radius:14px;background:#fff;box-shadow:0 7px 20px #1b37600b}.vx-kpi b{font-size:30px;color:#071641}.vx-kpi span{display:block;color:#66748d;font-size:13px;margin-top:7px}
    .vx-board{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:12px;border:1px solid #dce4ef;border-radius:14px;background:#fff}.vx-col{min-height:390px;padding:12px;border:1px solid #dde5f0;border-radius:12px;background:#f7f9ff}.vx-col:nth-child(2){background:#fffaf0}.vx-col:nth-child(3){background:#f3f7ff}.vx-col:nth-child(4){background:#f2fbf7}.vx-col h3{font-size:15px!important;margin:0 0 12px!important}.vx-task{padding:13px;margin:9px 0;border:1px solid #d8e1ed;border-radius:9px;background:#fff}.vx-task b{display:block;color:#13213f;font-size:13px}.vx-task small{display:block;color:#68758c;margin-top:8px}.vx-person{display:grid;grid-template-columns:1.6fr 1fr .55fr .65fr .8fr;gap:14px;align-items:center;padding:16px;border-bottom:1px solid #dce4ef;background:#fff}.vx-person:first-child{border-radius:12px 12px 0 0}.vx-person:last-child{border-radius:0 0 12px 12px}.vx-person b{color:#12203e}.vx-person small{display:block;color:#78849a}.vx-empty{padding:34px;text-align:center;border:1px dashed #b9c7da;border-radius:12px;color:#65738d}.vx-ai-card{padding:18px;border:1px solid #dce4ef;border-radius:13px;background:#fff}.vx-ai-card h3{font-size:17px!important;color:#102044!important}
    @media(max-width:1000px){.vx-kpis,.vx-board{grid-template-columns:repeat(2,1fr)}}@media(max-width:620px){.vx-kpis,.vx-board{grid-template-columns:1fr}.vx-person{grid-template-columns:1fr 1fr}}
    </style>""", unsafe_allow_html=True)


def tareas(st, rows: list[dict], meetings: dict[str, str], patch_task, create_task, meeting_rows: list[dict], admin: bool) -> None:
    _css(st); _head(st, "☑", "Tareas y seguimiento", "Convierte los acuerdos de tus reuniones en acciones verificables.")
    now = datetime.now(timezone.utc).date()
    normalized=[]
    for row in rows:
        state=str(row.get("estado") or "pendiente").lower()
        due=str(row.get("fecha_vencimiento") or "")[:10]
        overdue=bool(due and due < now.isoformat() and state != "completada")
        normalized.append({**row,"estado":state,"due":due or "Sin fecha","overdue":overdue})
    counts={"pendiente":0,"en_progreso":0,"completada":0}
    for row in normalized: counts[row["estado"]] = counts.get(row["estado"],0)+1
    overdue=sum(1 for r in normalized if r["overdue"])
    st.markdown(f"""<div class="vx-kpis"><div class="vx-kpi"><b>{counts.get('pendiente',0)}</b><span>pendientes</span></div><div class="vx-kpi"><b>{counts.get('en_progreso',0)}</b><span>en progreso</span></div><div class="vx-kpi"><b>{counts.get('completada',0)}</b><span>completadas</span></div><div class="vx-kpi"><b>{overdue}</b><span>vencidas</span></div></div>""", unsafe_allow_html=True)
    search=st.text_input("Buscar tareas", placeholder="Buscar tareas", label_visibility="collapsed")
    shown=[r for r in normalized if search.lower() in str(r.get("descripcion") or "").lower()]
    groups=[("Por confirmar", "detectado"),("Pendientes","pendiente"),("En progreso","en_progreso"),("Completadas","completada")]
    html='<div class="vx-board">'
    for label,state in groups:
        subset=[r for r in shown if r["estado"]==state]
        html+=f'<section class="vx-col"><h3>{label} ({len(subset)})</h3>'
        for r in subset:
            desc=escape(str(r.get("descripcion") or "Sin descripción")); owner=escape(str(r.get("asignado_a_correo") or "No asignado")); meeting=escape(meetings.get(str(r.get("reunion_id")),"Reunión no disponible"))
            html+=f'<div class="vx-task"><b>{desc}</b><small>{owner}　·　{escape(r["due"])}</small><small>{meeting}</small></div>'
        html+='</section>'
    st.markdown(html+'</div>', unsafe_allow_html=True)
    st.caption("Selecciona una tarea para cambiar su estado. Los cambios se guardan mediante PATCH.")
    if normalized:
        labels={f"{r.get('descripcion')} · {r.get('asignado_a_correo') or 'No asignado'}":r for r in normalized}
        c1,c2,c3=st.columns([2,1,1]); selected=c1.selectbox("Tarea", list(labels)); new_state=c2.selectbox("Estado",["pendiente","en_progreso","completada"])
        if c3.button("Guardar estado", type="primary", use_container_width=True): patch_task(str(labels[selected]["id"]),new_state); st.rerun()
    if admin:
        with st.expander("＋ Nueva tarea"):
            with st.form("vx-new-task"):
                options={str(r.get("tema") or r.get("id")):str(r.get("id")) for r in meeting_rows}
                meeting=st.selectbox("Reunión",list(options)); description=st.text_area("Descripción"); owner=st.text_input("Responsable (correo)"); due=st.date_input("Fecha límite")
                if st.form_submit_button("Crear tarea",type="primary"):
                    create_task(options[meeting],description,owner,due.isoformat()); st.rerun()


def participantes(st, rows: list[dict], users: dict[str, dict], meetings: dict[str, str], tasks: list[dict]) -> None:
    _css(st); _head(st,"♧","Participantes","Consulta la actividad y el seguimiento de quienes intervienen en tus reuniones.")
    emails={str(r.get("correo") or "").lower() for r in rows if r.get("correo")}
    accepted=sum(1 for r in rows if str(r.get("estado_invitacion"))=="aceptado")
    st.markdown(f"""<div class="vx-kpis"><div class="vx-kpi"><b>{len(emails)}</b><span>participantes únicos</span></div><div class="vx-kpi"><b>{accepted}</b><span>asistencias aceptadas</span></div><div class="vx-kpi"><b>{len(rows)}</b><span>participaciones</span></div><div class="vx-kpi"><b>{len([t for t in tasks if t.get('asignado_a_correo')])}</b><span>tareas asignadas</span></div></div>""",unsafe_allow_html=True)
    search=st.text_input("Buscar participante",placeholder="Buscar participante",label_visibility="collapsed")
    aggregate={}
    for r in rows:
        email=str(r.get("correo") or "No especificado").lower(); item=aggregate.setdefault(email,{"meetings":set(),"accepted":0}); item["meetings"].add(str(r.get("reunion_id"))); item["accepted"]+=str(r.get("estado_invitacion"))=="aceptado"
    html='<div>'
    for email,data in aggregate.items():
        user=users.get(email,{}) ; name=escape(str(user.get("nombre") or email));
        if search.lower() not in (name+email).lower(): continue
        assigned=[t for t in tasks if str(t.get("asignado_a_correo") or "").lower()==email]; completed=sum(str(t.get("estado"))=="completada" for t in assigned); rate=round(completed*100/len(assigned)) if assigned else 0
        html+=f'<div class="vx-person"><div><b>{name}</b><small>{escape(email)}</small></div><span>{len(data["meetings"])} reuniones</span><span>{data["accepted"]} aceptadas</span><span>{len(assigned)} tareas</span><span>{rate}% completadas</span></div>'
    st.markdown(html+'</div>',unsafe_allow_html=True)


def metricas(st, meetings: list[dict], tasks: list[dict], participants: list[dict], reports: list[dict], n8n: list[dict]) -> None:
    _css(st); _head(st,"◉","Métricas de reuniones","Analiza la colaboración, el cumplimiento y el funcionamiento real de VINCORA.")
    done=sum(str(t.get("estado"))=="completada" for t in tasks); task_rate=round(done*100/len(tasks)) if tasks else 0
    approved=len(reports); completed_meetings=sum(str(m.get("estado") or "").lower() in {"completada","finalizada"} for m in meetings)
    success=sum(str(x.get("estado") or "").lower() in {"éxito","exito","success"} for x in n8n); api_rate=round(success*100/len(n8n)) if n8n else 0
    st.markdown(f"""<div class="vx-kpis"><div class="vx-kpi"><b>{len(meetings)}</b><span>reuniones</span></div><div class="vx-kpi"><b>{completed_meetings}</b><span>reuniones finalizadas</span></div><div class="vx-kpi"><b>{approved}</b><span>informes disponibles</span></div><div class="vx-kpi"><b>{task_rate}%</b><span>tareas completadas</span></div></div>""",unsafe_allow_html=True)
    c1,c2=st.columns(2)
    if tasks:
        frame=pd.DataFrame(tasks); states=frame.groupby("estado").size().reset_index(name="cantidad"); c1.plotly_chart(px.pie(states,values="cantidad",names="estado",hole=.55,title="Estado de tareas"),use_container_width=True)
    if n8n:
        frame=pd.DataFrame(n8n); frame["fecha"]=pd.to_datetime(frame["fecha"],errors="coerce"); daily=frame.dropna(subset=["fecha"]).groupby(frame["fecha"].dt.date).size().reset_index(name="peticiones"); c2.plotly_chart(px.line(daily,x="fecha",y="peticiones",markers=True,title="Actividad de automatizaciones"),use_container_width=True)
    st.info(f"Disponibilidad observada de automatizaciones: {api_rate}% sobre {len(n8n)} registros reales.")


def ia_config(st, render_model) -> None:
    _css(st); _head(st,"✦","Configuración de VINCORA IA","Define cómo se transcriben, analizan y presentan tus reuniones.")
    defaults={"ai_enabled":True,"transcription":True,"speakers":True,"timestamps":True,"agreements":True,"tasks":True,"decisions":True,"risks":True,"confidence":.95,"template":"Informe ejecutivo"}
    for key,value in defaults.items(): st.session_state.setdefault("vx_"+key,value)
    c1,c2=st.columns(2)
    with c1:
        with st.container(border=True):
            st.subheader("1. Transcripción"); st.toggle("Transcripción automática",key="vx_transcription"); st.toggle("Identificación de hablantes",key="vx_speakers"); st.toggle("Marcas de tiempo",key="vx_timestamps")
        with st.container(border=True):
            st.subheader("3. Informe automático"); st.selectbox("Plantilla",["Informe ejecutivo","Acta formal","Reunión de proyecto","Entrevista"],key="vx_template")
    with c2:
        with st.container(border=True):
            st.subheader("2. Detección durante la reunión"); st.toggle("Acuerdos",key="vx_agreements"); st.toggle("Tareas",key="vx_tasks"); st.toggle("Decisiones",key="vx_decisions"); st.toggle("Riesgos y bloqueos",key="vx_risks")
        with st.container(border=True):
            st.subheader("4. Reglas de confianza"); st.slider("Umbral de confianza",.50,1.0,key="vx_confidence",format="%.0f%%")
    if st.button("Guardar configuración",type="primary"):
        st.session_state["vx_ai_saved"]=True; st.success("Configuración guardada para esta sesión.")
    with st.expander("Modelo de clasificación y validación científica"):
        st.caption("La configuración anterior controla el informe. El clasificador científico se carga bajo demanda para no bloquear la pantalla durante el arranque de Render.")
        if st.button("Abrir clasificador", key="vx_open_classifier"):
            st.session_state["vx_classifier_open"] = True
        if st.session_state.get("vx_classifier_open"):
            render_model()
