# Validación de ejecución realizada

Fecha: 12 de julio de 2026.

## Dataset y EDA

- Los tres CSV públicos de MRDA/SILICONE fueron descargados y verificados mediante SHA-256.
- Registros: 83 943 train, 9 815 dev y 15 470 test.
- Total procesado: 109 228.
- Reuniones: 73; hablantes: 52.
- Textos vacíos: 0; identificadores duplicados: 0.
- Se generaron distribución, mapa de calor, longitud, palabras frecuentes y estadísticos.

## Entrenamiento

Se ejecutaron cinco modelos con resultados reales:

| Modelo | Accuracy test | F1 macro test |
|---|---:|---:|
| MLP-TFIDF | 0,6427 | 0,6219 |
| CNN-1D | 0,6488 | 0,5977 |
| BiLSTM-Atención | 0,5822 | 0,5801 |
| CNN-BiLSTM | 0,5537 | 0,5626 |
| LSTM | 0,5014 | 0,2204 |

El mejor modelo por F1 macro fue guardado en `models/best_model.h5`.

## Validación, tuning y estadística

- Cross validation: cinco folds configurables, agrupados por reunión.
- Mejor F1 macro promedio CV: CNN-1D, 0,4982.
- Tuning CNN-BiLSTM: cuatro ensayos.
- Friedman: estadístico 17,28; p=0,001705.
- Wilcoxon-Holm: ninguna comparación pareada significativa después del ajuste.

## FastAPI

Verificado mediante pruebas automáticas:

- `GET /health` -> 200.
- `GET /model/status` -> modelo disponible, `best_model.h5`.
- `POST /predict` -> 200 y `artifact_file=best_model.h5`.
- `GET /metrics` -> cinco modelos.
- `GET /reports` -> Word, PDF y Excel.
- Descarga de Excel -> 200.

Resultado final: **6 pruebas aprobadas**.

## Streamlit

Se ejecutó el dashboard en modo demostración local identificado. Se capturaron:

- predicción real mediante la API;
- comparación de cinco modelos;
- EDA;
- validación y estadística;
- descarga de Word, PDF y Excel.

El modo demostración sustituye únicamente la autenticación/datos externos de Supabase; los resultados científicos y la inferencia proceden de los artefactos MRDA reales.

## Reportes

- DOCX renderizado y revisado: 29 páginas.
- PDF renderizado y revisado: 29 páginas.
- Excel verificado sin errores de fórmula.
