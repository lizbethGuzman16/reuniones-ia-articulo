# Fuentes del dataset público

## Dataset utilizado

- Nombre: ICSI Meeting Recorder Dialog Act Corpus (MRDA).
- Distribución utilizada: configuración `mrda` del benchmark SILICONE.
- Idioma: inglés.
- Tarea: clasificación multiclase de actos de diálogo en reuniones.
- Clases: `s`, `d`, `b`, `f`, `q`.

## Enlaces públicos

- Ficha SILICONE: https://huggingface.co/datasets/eusip/silicone
- Artículo original MRDA: https://aclanthology.org/W04-2319/
- Artículo SILICONE: https://aclanthology.org/2020.findings-emnlp.239/
- Repositorio fuente: https://github.com/eusip/SILICONE-benchmark
- Train: https://raw.githubusercontent.com/eusip/SILICONE-benchmark/main/mrda/train.csv
- Validación: https://raw.githubusercontent.com/eusip/SILICONE-benchmark/main/mrda/dev.csv
- Prueba: https://raw.githubusercontent.com/eusip/SILICONE-benchmark/main/mrda/test.csv

## Integridad de los archivos usados

| Archivo | Filas | SHA-256 |
|---|---:|---|
| mrda_train.csv | 83 943 | d7a963aac70eb80d315b76b9e71d82a7888532ef8c6752c84487e34dfce3b7eb |
| mrda_dev.csv | 9 815 | dc795c60b3825645a20dbb0700e279271fc52eef4bc297564a0227f608a19619 |
| mrda_test.csv | 15 470 | 8426417d316cb0aa57f13e46e866e8964eed71f719212ab1da1c3cbaa23ea414 |

La reproducción se realiza con `python -m ml.download_mrda`. El script no genera datos sintéticos.
