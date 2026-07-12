# Módulo científico

## Flujo

```bash
python -m ml.download_mrda
python -m ml.eda
python -m ml.train_all
python -m ml.cross_validation
python -m ml.tuning
python -m ml.statistical_tests
```

## Componentes

- `download_mrda.py`: descarga los tres splits públicos y registra SHA-256.
- `eda.py`: limpieza, estadísticos, tablas y figuras.
- `models.py`: MLP-TFIDF, CNN-1D, LSTM, CNN-BiLSTM y BiLSTM-Atención.
- `train_all.py`: entrenamiento principal y evaluación en test oficial.
- `cross_validation.py`: StratifiedGroupKFold configurable.
- `tuning.py`: búsqueda de hiperparámetros para CNN-BiLSTM.
- `statistical_tests.py`: Friedman y Wilcoxon con corrección Holm.
- `config.py`: semilla y parámetros de reproducción.

## Resultados incluidos

El mejor modelo por F1 macro en test fue MLP-TFIDF (0,6219). La API consume directamente `models/best_model.h5`; no es necesario reentrenar para ejecutar predicciones.

Los CSV de `reports/tables/` son la fuente numérica de los reportes. Las figuras se guardan en `reports/figures/`.
