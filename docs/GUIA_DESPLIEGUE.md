# Guía de despliegue

## Estado del despliegue (2026-07-12)

El despliegue fue ejecutado con las cuentas del equipo. URLs reales:

- GitHub: https://github.com/lizbethGuzman16/reuniones-ia-articulo (CI en verde, release v1.0.0 con Word/PDF/Excel)
- FastAPI Render: https://reuniones-ia-api.onrender.com
- Streamlit Render: https://reuniones-ia-frontend.onrender.com
- Landing Vercel: https://reuniones-ia-articulo.vercel.app
- Supabase: proyecto `reuniones-ia-articulo` (us-east-1) con tablas y políticas RLS aplicadas (query1, query2, query4, query5)

Los pasos siguientes documentan cómo se realizó y cómo reproducirlo.

## 1. Publicar en GitHub

1. Cree un repositorio privado durante la revisión inicial.
2. Copie el proyecto sin `.env`.
3. Verifique:

```bash
git status
git grep -n "SUPABASE_ANON_KEY\|password\|eyJ"
pytest -q
```

4. Publique:

```bash
git init
git add .
git commit -m "Entrega científica MRDA con Streamlit y FastAPI"
git branch -M main
git remote add origin <URL_DEL_REPOSITORIO>
git push -u origin main
```

GitHub Actions ejecutará las pruebas mediante `.github/workflows/ci.yml`.

## 2. Backend FastAPI en Render

Opción A: Blueprint con `render.yaml`.

1. En Render, seleccione **New > Blueprint**.
2. Conecte el repositorio.
3. Seleccione `render.yaml`.
4. Confirme el servicio `reuniones-ia-api`.
5. Compruebe `/health` y `/docs`.

Opción B: Web Service manual.

- Runtime: Python 3.11.
- Build: `pip install -r requirements.txt`.
- Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- Health check: `/health`.
- Variable: `CORS_ORIGINS=https://DOMINIO-FRONTEND`.
- Variable privada solo si se necesita para tareas administrativas de backend: `SUPABASE_SERVICE_ROLE_KEY`.

## 3. Frontend Streamlit

Streamlit requiere un proceso persistente con WebSockets. Use el segundo servicio definido en `render.yaml` o Streamlit Community Cloud.

Variables:

- `FASTAPI_URL=https://URL-API.onrender.com`
- `DEMO_MODE=false`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `ADMIN_EMAILS=correo-admin-1@dominio,correo-admin-2@dominio`
- Webhooks n8n utilizados por las funciones originales.

No configure `SUPABASE_SERVICE_ROLE_KEY` en Streamlit, Vercel ni ningún cliente visible por navegador.

Comando:

```bash
streamlit run frontend/app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```

## 4. Landing en Vercel

La carpeta `vercel_landing/` contiene una landing estática. Antes de publicar, edite `vercel_landing/config.js`:

```javascript
window.STREAMLIT_APP_URL = "https://URL-REAL-DEL-FRONTEND";
```

Conecte el repositorio a Vercel. `vercel.json` sirve la landing. Esta página no reemplaza el proceso Python de Streamlit; lo enlaza.

## 5. Supabase y seguridad

- Rotar todas las claves que estuvieron dentro del RAR original.
- No subir `.env` ni `.streamlit/secrets.toml`.
- Crear usuarios mediante un mecanismo seguro.
- Restringir Row Level Security por usuario/rol.
- No dejar políticas de acceso total.
- Aplicar `docs/querys para supabase/query4.txt` solo después de migrar el login a Supabase Auth o de adaptar `auth.uid()` al modelo de usuarios.
- En el despliegue actual la app usa autenticación propia (bcrypt) con la anon key desde el servidor de Render; por eso se aplicó también `query5.txt` (tabla `metricas_n8n` + políticas para el rol `anon`). La anon key vive solo en variables de entorno del servidor; ver el comentario de `query5.txt` para la migración futura a Supabase Auth.
- Restringir CORS en producción.

## 6. Evidencias para la exposición

URLs registradas:

- GitHub: https://github.com/lizbethGuzman16/reuniones-ia-articulo
- FastAPI Render: https://reuniones-ia-api.onrender.com
- Streamlit Render/Cloud: https://reuniones-ia-frontend.onrender.com
- Landing Vercel: https://reuniones-ia-articulo.vercel.app
- Proyecto Jira: _______________________ (pendiente)

Capturar `/health`, `/docs`, pantalla autenticada, predicción y descarga de reportes.
