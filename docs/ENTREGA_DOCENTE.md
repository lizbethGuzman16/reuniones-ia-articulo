# Entrega al docente

## Archivos principales

1. `reports/articulo_cientifico_reuniones_ia.docx`
2. `reports/articulo_cientifico_reuniones_ia.pdf`
3. `reports/reporte_resultados_modelos.xlsx`
4. Código completo de Streamlit, FastAPI y aprendizaje automático.
5. `models/best_model.h5`.
6. Figuras y tablas en `reports/`.
7. Backlog Jira en `docs/JIRA_BACKLOG.csv`.

## Antes de presentar

- Agregar los nombres, correos y ORCID de los demás integrantes si el formato del curso lo exige.
- Rotar las credenciales originales y completar el `.env` únicamente en el entorno privado.
- Crear y pegar las URLs reales de GitHub, Render, frontend, Vercel y Jira en la guía de despliegue.
- No afirmar que el modelo fue validado en español: MRDA está en inglés.
- Explicar que el entrenamiento principal usó 30 000 registros estratificados y el test oficial completo.

## Guion mínimo de demostración

1. Mostrar el manifiesto del dataset y el EDA.
2. Mostrar la comparación de seis modelos: tres base y tres híbridos.
3. Explicar por qué se seleccionó F1 macro.
4. Mostrar validación cruzada, tuning y Friedman/Wilcoxon-Holm.
5. Ejecutar `/health` y `/model/status`.
6. Ingresar una intervención en inglés y mostrar que responde desde `best_model.h5`.
7. Descargar Word, PDF y Excel desde el dashboard.
