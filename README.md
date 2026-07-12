# Reuniones IA - artículo científico y sistema funcional

Proyecto completo para clasificar actos de diálogo en transcripciones de reuniones. Integra el sistema original de gestión de reuniones con un experimento reproducible de aprendizaje automático, un backend FastAPI y un dashboard autenticado en Streamlit.

## Resultado científico principal

- Dataset público: **ICSI Meeting Recorder Dialogue Act (MRDA)**, distribución SILICONE.
- Registros procesados: **109 228**.
- Reuniones: **73**.
- Hablantes: **52**.
- Modelos clásicos: **MLP-TFIDF, CNN-1D y LSTM**.
- Modelos híbridos: **CNN-BiLSTM y BiLSTM con atención**.
- Mejor modelo en el test oficial: **MLP-TFIDF**.
- Accuracy: **0,6427**.
- F1 macro: **0,6219**.
- ROC-AUC macro: **0,8896**.
- Validación cruzada: **5 folds configurables**, agrupados por reunión.
- Friedman: **p = 0,001705**.
- Artefacto consumido por la API: `models/best_model.h5`.
- Formato del artefacto: `state_dict` de **PyTorch** almacenado en HDF5 con `h5py`; no es un modelo Keras. Se conserva `models/best_model.pt`.

Los resultados corresponden a ejecuciones reales. La comparación principal entrenó con una muestra estratificada de 30 000 registros del split oficial de entrenamiento y evaluó los 15 470 registros completos del split oficial de prueba. Esta limitación se declara en el artículo.

## Entregables

- `reports/articulo_cientifico_reuniones_ia.docx`
- `reports/articulo_cientifico_reuniones_ia.pdf`
- `reports/reporte_resultados_modelos.xlsx`
- `reports/figures/`: EDA, mapas de calor, matrices, ROC, pérdidas, tuning y validación.
- `reports/tables/`: resultados numéricos en CSV.
- `models/best_model.h5`: mejor modelo para inferencia sin reentrenar.
- `docs/JIRA_BACKLOG.csv`: backlog importable en Jira.
- `render.yaml`, `Dockerfile` y `Dockerfile.frontend`: despliegue preparado.
- `.github/workflows/ci.yml`: pruebas automáticas en GitHub.

## Estructura

```text
backend/       FastAPI e inferencia desde best_model.h5
frontend/      Streamlit, autenticación, dashboard y módulo IA
ml/            descarga, EDA, entrenamiento, CV, tuning y estadística
data/          datos públicos originales y dataset procesado
models/        modelos, vectorizador, etiquetas y metadatos
reports/       Word, PDF, Excel, tablas y figuras
docs/          manuales, fuentes, Jira y despliegue
tests/         pruebas automáticas
```

## Instalación local

Se recomienda Python 3.11.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar el sistema

Terminal 1:

```bash
uvicorn backend.main:app --reload --port 8000
```

Terminal 2, modo demostración claramente identificado:

```powershell
$env:DEMO_MODE="true"
$env:FASTAPI_URL="http://localhost:8000"
streamlit run frontend/app.py
```

Con Supabase real, copie `.env.example` como `.env`, coloque credenciales renovadas y mantenga `DEMO_MODE=false`.

## Reproducir el experimento

```bash
python -m ml.download_mrda
python -m ml.eda
python -m ml.train_all
python -m ml.cross_validation
python -m ml.tuning
python -m ml.statistical_tests
```

Los parámetros están en `ml/config.py`: semilla, muestra de entrenamiento, épocas, tamaño de vocabulario, folds y ensayos de tuning.

Perfil completo sin sobrescribir resultados vigentes:

```bash
python -m ml.run_full_training_profile
```

Este perfil usa `TRAIN_SAMPLE_SIZE=full`, `CV_SAMPLE_SIZE=full` y `TUNING_SAMPLE_SIZE=full`, escribe modelos, tablas, figuras, logs, configuración y versiones en `runs/full_train_*`, y no promueve esos resultados a `models/` ni `reports/` salvo que se ejecute con `--promote` después de terminar correctamente.

## API

- `GET /health`
- `GET /model/status`
- `POST /predict`
- `POST /predict/batch`
- `GET /metrics`
- `GET /reports`
- `GET /reports/{filename}`

Ejemplo:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"can you send the report tomorrow?"}'
```

## Pruebas

```bash
pytest -q
```

Las pruebas verifican salud, carga directa del H5, inferencia, métricas y descarga de reportes.

## Seguridad

- No se incluye el `.env` original.
- Las claves encontradas en el RAR fueron retiradas de la copia.
- Las credenciales que estuvieron en el RAR deben rotarse antes de producción.
- No publicar `DEMO_MODE=true` como entorno productivo.
- Configurar `CORS_ORIGINS` con los dominios reales de producción.
- Configurar `ADMIN_EMAILS` con los correos administradores, separados por coma.
- Mantener `SUPABASE_SERVICE_ROLE_KEY` solo en entornos privados de backend/operación; no usarla en Streamlit ni en el navegador.
- Revisar las políticas RLS de Supabase.

## Despliegue

Streamlit requiere un proceso persistente con WebSockets, por lo que el frontend funcional se ejecuta en Render; Vercel aloja la landing estática que enlaza a la aplicación.

URLs públicas (desplegadas el 2026-07-12):

- Repositorio GitHub: https://github.com/lizbethGuzman16/reuniones-ia-articulo
- Release v1.0.0 (Word/PDF/Excel adjuntos): https://github.com/lizbethGuzman16/reuniones-ia-articulo/releases/tag/v1.0.0
- API FastAPI (Render): https://reuniones-ia-api.onrender.com — salud en `/health`, documentación en `/docs`
- Frontend Streamlit (Render): https://reuniones-ia-frontend.onrender.com
- Landing (Vercel): https://reuniones-ia-articulo.vercel.app

Nota: los servicios usan el plan gratuito de Render; tras un periodo de inactividad la primera petición puede tardar ~1 minuto mientras la instancia despierta.

Consulte `docs/GUIA_DESPLIEGUE.md` y `docs/ENTREGA_DOCENTE.md`.
