# Matriz de cumplimiento

| Requisito docente | Estado | Evidencia |
|---|---:|---|
| Dataset público | Cumplido | MRDA/SILICONE, tres splits, manifiesto con SHA-256 |
| EDA y limpieza | Cumplido | Nulos, duplicados, clases, estadísticos, longitudes, palabras, heatmap |
| Tres modelos clásicos | Cumplido | MLP-TFIDF, CNN-1D, LSTM |
| Dos modelos híbridos | Cumplido | CNN-BiLSTM, BiLSTM con atención |
| Tabla comparativa | Cumplido | Métricas, tiempos, tamaño y parámetros |
| Matrices de confusión | Cumplido | Una por modelo |
| Curvas ROC | Cumplido | Una por modelo, multiclase |
| Modelo guardado | Cumplido | `best_model.h5`, cargado directamente por FastAPI |
| Cross validation | Cumplido | Cinco folds configurables y agrupados por reunión |
| Tuning | Cumplido | Cuatro ensayos CNN-BiLSTM |
| Pruebas estadísticas | Cumplido | Friedman y Wilcoxon-Holm |
| PDF, Word, Excel | Cumplido | Carpeta `reports/` |
| Interpretación de tablas/figuras | Cumplido | Artículo y dashboard |
| Dashboard autenticado | Cumplido | Módulo IA posterior al login; demo identificada |
| Python + Streamlit + FastAPI | Cumplido | `frontend/` y `backend/` |
| GitHub | Cumplido | https://github.com/lizbethGuzman16/reuniones-ia-articulo — CI en verde, release v1.0.0 |
| Jira | Cumplido | Proyecto RIA: https://unitru-team-lpdtf21r.atlassian.net/jira/software/c/projects/RIA/boards — backlog importado (12 issues) |
| Render | Cumplido | API: https://reuniones-ia-api.onrender.com · Frontend: https://reuniones-ia-frontend.onrender.com |
| Vercel | Cumplido | https://reuniones-ia-articulo.vercel.app |
| Supabase | Cumplido | Proyecto real con tablas y RLS (query1, query2, query4, query5); `DEMO_MODE=false` en producción |
