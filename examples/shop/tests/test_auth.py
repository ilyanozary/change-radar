from app.services import authenticate, normalize_user
from app.models import LoginRequest

def test_login():
    result = authenticate(LoginRequest(username=' DEMO ', password='demo-only'))
    assert result.user_id == 'demo'

def test_normalize_user():
    assert normalize_user(' Alice ') == 'alice'
