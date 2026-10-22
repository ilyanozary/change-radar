from fastapi.testclient import TestClient
from app.main import app

def test_login_contract():
    with TestClient(app) as client:
        response = client.post('/v1/auth/login', json={'username':'demo','password':'demo-only'})
        assert response.status_code == 200
        assert set(response.json()) == {'access_token','user_id'}
