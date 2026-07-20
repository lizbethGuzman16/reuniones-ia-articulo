# Auditoría final de la entrega

## Resultado

La entrega fue validada antes del empaquetado final. No se incorporaron métricas simuladas ni credenciales privadas.

## Pruebas funcionales

Comando ejecutado desde la raíz del proyecto:

```bash
pytest -q
```

Resultado:

```text
................                                                         [100%]
16 passed
```

Las pruebas cubren:

1. Estado de salud de FastAPI.
2. Disponibilidad y carga directa de `models/best_model.h5`.
3. Predicción real y probabilidades para las cinco clases.
4. Exposición de resultados de los seis modelos.
5. Listado de los reportes Word, PDF y Excel.
6. Descarga válida del reporte Excel.

## Verificación del artículo

- Word renderizado correctamente: 29 páginas.
- PDF final: 29 páginas.
- Comparación visual Word→PDF: 29 páginas sin diferencias (`changed_pages = 0`).
- No se observaron textos cortados, tablas superpuestas, figuras fuera de margen ni caracteres dañados.

## Verificación del Excel

- 16 hojas: dashboard, EDA, comparación, validación cruzada, tuning, pruebas estadísticas, seis reportes por modelo y fuentes.
- Dashboard revisado con los resultados principales.
- Búsqueda de errores `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` y `#N/A`: cero coincidencias.

## Integridad del dataset

Los tres archivos públicos MRDA conservan los hashes SHA-256 registrados en `data/raw/dataset_manifest.json`:

- entrenamiento: 83 943 registros;
- desarrollo: 9 815 registros;
- prueba: 15 470 registros.

El conjunto procesado contiene 109 228 intervenciones.

## Seguridad

- No existe un archivo `.env` dentro de la entrega.
- Solo se incluye `.env.example` con campos vacíos.
- Las claves y URL privadas presentes en el RAR original fueron reemplazadas por marcadores.
- La búsqueda de patrones comunes de secretos no encontró claves activas.

## Alcance externo pendiente

Los archivos para GitHub, Jira, Render y Vercel están preparados. La creación de repositorios, proyectos y URL públicas requiere iniciar sesión en las cuentas del equipo; por esa razón no se presentan enlaces inventados.

## Actualización de seguridad y reproducibilidad — 2026-07-12

Se aplicó una ronda de endurecimiento sobre seguridad y reproducibilidad, sin alterar métricas ni artefactos de modelo. Pruebas reales ejecutadas ese día:

- `pytest -q`: `6 passed, 4 warnings` (advertencias de compatibilidad de versión de `httpx`/`scikit-learn`/`numpy` frente al entorno original, sin afectar el resultado).
- FastAPI reiniciado por completo y probado por HTTP tras el arranque:
  - `GET /health` → `200 {"status":"ok"}`.
  - `GET /model/status` → `available: true`, artefacto `best_model.h5`, respaldo `.pt` disponible.
  - `POST /predict` (dos llamadas consecutivas) → misma predicción determinista; caché del modelo `maxsize=1, currsize=1, hits=1, misses=1` (confirma carga única, sin reentrenamiento).
  - `GET /docs` y `GET /openapi.json` → `200`.
- Streamlit levantado en modo demo (`DEMO_MODE=true`) apuntando a la URL real de FastAPI vía `FASTAPI_URL`; respondió `200` y el módulo de inteligencia artificial cargó con el modelo disponible. La verificación de clic final ("Clasificar intervención") en un navegador real no pudo completarse en esta ronda porque las herramientas de navegador del entorno de esta sesión no tuvieron acceso de red al servidor local; queda como verificación manual pendiente por el equipo.

Cambios de seguridad/reproducibilidad incluidos:

- CORS de FastAPI restringido por variable de entorno (ya no abierto por defecto); logging y manejo de errores menos verboso.
- Autenticación demo de Streamlit ya no usa un correo hardcodeado; usa `ADMIN_EMAILS` configurable.
- Políticas RLS de Supabase en `docs/querys para supabase/query4.txt` reemplazadas: ya no usan `USING (true)`.
- JSON de n8n (`docs/json n8n/AsistenteIA1.json`) saneado: sin `credentials`, `id` ni `instanceId`, flujo marcado `active=false`.
- `ml/cross_validation.py` y `ml/tuning.py` aceptan `CV_SAMPLE_SIZE`/`TUNING_SAMPLE_SIZE = full` o `0` para correr sobre el dataset completo.
- Nuevo runner `ml/run_full_training_profile.py` para un entrenamiento completo (83 943 registros) que guarda configuración, semilla, versiones de librerías y logs en `runs/`, sin sobrescribir los resultados documentados hasta que termine correctamente.
- `models/best_model_metadata.json` documenta explícitamente que el artefacto es un `state_dict` de PyTorch serializado dentro de un contenedor HDF5 (vía `h5py`), no un modelo Keras, y que existe un respaldo `.pt` equivalente.
- `SHA256SUMS.txt` regenerado para reflejar los archivos modificados en esta ronda (157 entradas, incluye el nuevo `ml/run_full_training_profile.py`).

Ningún cambio de esta ronda modificó `models/best_model.h5`, los reportes Word/PDF/Excel, ni las métricas registradas en `VALIDACION_FINAL.json`.
