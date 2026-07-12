# Manual técnico

## 1. Arquitectura

```text
Navegador
   │
   ▼
Streamlit - autenticación, gestión, EDA, resultados y reportes
   │ HTTP
   ▼
FastAPI - estado, predicción, métricas y descargas
   │
   ├── best_model.h5
   ├── tfidf_vectorizer.joblib
   ├── labels.json
   └── best_model_metadata.json
```

Las funciones originales de usuarios, reuniones, tareas, participantes, resúmenes y métricas utilizan solicitudes HTTP hacia Supabase y n8n. El módulo científico no necesita reentrenar para responder: FastAPI carga directamente `models/best_model.h5` y conserva `best_model.pt` como respaldo técnico.

`models/best_model.h5` fue creado por el código PyTorch del proyecto: contiene un `state_dict` almacenado en HDF5 mediante `h5py`; no es un modelo Keras ni se debe tratar como tal. La API reconstruye la arquitectura PyTorch, carga ese `state_dict`, usa `models/tfidf_vectorizer.joblib` cuando el metadato indica `type=tfidf`, y reutiliza la instancia mediante caché para no recargar el modelo en cada predicción.

## 2. Requisitos

- Python 3.11 recomendado.
- 8 GB de RAM para reproducir la configuración incluida.
- Git.
- Acceso a Internet únicamente para descargar dependencias/dataset o usar Supabase/n8n.

## 3. Instalación

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Copiar `.env.example` como `.env` y completar solo credenciales renovadas.

## 4. Dataset y reproducibilidad

```bash
python -m ml.download_mrda
python -m ml.eda
python -m ml.train_all
python -m ml.cross_validation
python -m ml.tuning
python -m ml.statistical_tests
```

`data/raw/dataset_manifest.json` conserva URL, cantidad de filas y SHA-256 de cada split. `ml/config.py` permite modificar semilla, épocas, tamaño de muestra, vocabulario, folds y ensayos.

Para ejecutar el perfil completo de 83 943 registros oficiales de entrenamiento sin sobrescribir resultados vigentes:

```bash
python -m ml.run_full_training_profile
```

El runner escribe en `runs/full_train_*` la configuración, versiones de librerías, logs, modelos, tablas y figuras. Solo copia a `models/` y `reports/` si se ejecuta con `--promote` y todo el flujo termina correctamente.

## 5. Configuración reportada

- Semilla: 42.
- Muestra principal de entrenamiento: 30 000 registros estratificados.
- Test oficial completo: 15 470 registros.
- Vocabulario máximo: 12 000.
- Longitud: 40 tokens.
- TF-IDF: 2 500 atributos.
- Épocas: 2.
- Lote: 256.
- Cross validation: 5 folds configurables, agrupados por `Dialogue_ID`.
- Tuning: 4 combinaciones CNN-BiLSTM.

## 6. FastAPI

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`
- `GET /model/status`
- `POST /predict`
- `POST /predict/batch`
- `GET /metrics`
- `GET /reports`
- `GET /reports/{filename}`

`/model/status` debe informar `model_file: best_model.h5`. La respuesta de `/predict` incluye `artifact_file: best_model.h5`, lo que demuestra que la API consume el H5.

## 7. Streamlit

```bash
streamlit run frontend/app.py
```

Modo de demostración:

```powershell
$env:DEMO_MODE="true"
$env:FASTAPI_URL="http://localhost:8000"
streamlit run frontend/app.py
```

El menú de inteligencia artificial se muestra después de una sesión autenticada. El modo demostración usa una autenticación local exclusivamente para pruebas y aparece identificado en la pantalla.

## 8. Reportes

- Word: `reports/articulo_cientifico_reuniones_ia.docx`
- PDF: `reports/articulo_cientifico_reuniones_ia.pdf`
- Excel: `reports/reporte_resultados_modelos.xlsx`

Las tablas del artículo se basan en los CSV de `reports/tables/` y las figuras se encuentran en `reports/figures/`.

## 9. Pruebas

```bash
pytest -q
```

Se prueban salud, disponibilidad del H5, inferencia, métricas, listado de reportes y descarga.

## 10. Producción

- Definir `CORS_ORIGINS` con una lista separada por comas.
- Configurar `FASTAPI_URL` en el frontend.
- Definir Supabase y n8n solo desde variables de entorno.
- Definir `ADMIN_EMAILS` para habilitar funciones administrativas.
- Mantener `SUPABASE_SERVICE_ROLE_KEY` fuera de Streamlit y de cualquier cliente de navegador.
- Rotar credenciales que estuvieron presentes en el archivo original.
- Mantener `DEMO_MODE=false`.
