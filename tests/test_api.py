from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_model_status():
    response = client.get('/model/status')
    assert response.status_code == 200
    payload = response.json()
    assert payload['available'] is True
    assert payload['model_file'] == 'best_model.h5'
    assert payload['h5_available'] is True


def test_prediction_uses_h5():
    response = client.post('/predict', json={'text': 'can you send the report tomorrow ?'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['label_code'] in {'s', 'd', 'b', 'f', 'q'}
    assert 0 <= payload['confidence'] <= 1
    assert payload['artifact_file'] == 'best_model.h5'
    assert len(payload['probabilities']) == 5


def test_metrics_contains_five_models():
    response = client.get('/metrics')
    assert response.status_code == 200
    payload = response.json()
    assert payload['best_model']['modelo'] == 'MLP-TFIDF'
    assert len(payload['models']) == 5


def test_reports_list_final_formats():
    response = client.get('/reports')
    assert response.status_code == 200
    files = set(response.json()['files'])
    assert 'articulo_cientifico_reuniones_ia.docx' in files
    assert 'articulo_cientifico_reuniones_ia.pdf' in files
    assert 'reporte_resultados_modelos.xlsx' in files


def test_download_excel_report():
    response = client.get('/reports/reporte_resultados_modelos.xlsx')
    assert response.status_code == 200
    assert response.content[:2] == b'PK'
