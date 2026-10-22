from fastapi.testclient import TestClient
from main import app


def test_items():
    with TestClient(app) as client:
        response = client.get('/v1/shop/items')
        assert response.status_code == 200
        assert response.json()['items'] == [{'name': 'offline-demo-user'}]
