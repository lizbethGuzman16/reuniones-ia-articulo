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
| GitHub | Preparado | CI, gitignore y documentación; falta cuenta/URL |
| Jira | Preparado | `JIRA_BACKLOG.csv`; falta cuenta/URL |
| Render | Preparado | Blueprint de backend y frontend; falta cuenta/URL |
| Vercel | Preparado | Landing estática; falta cuenta/URL |
