"""Configuration regressions; never connect to a deployment database."""
import pytest
from jobflow_app import create_app
from jobflow_models import db

@pytest.fixture
def clean_environment(monkeypatch):
    for key in ('JOBFLOW_SECRET_KEY', 'JOBFLOW_DATABASE_URL', 'DATABASE_URL'):
        monkeypatch.delenv(key, raising=False)
    return monkeypatch

def test_missing_secret_rejected(clean_environment):
    with pytest.raises(RuntimeError, match='JOBFLOW_SECRET_KEY'):
        create_app()

def test_missing_database_rejected(clean_environment):
    clean_environment.setenv('JOBFLOW_SECRET_KEY', 'test-only-secret')
    with pytest.raises(RuntimeError, match='Database not configured'):
        create_app()

def test_health_redacts_database_and_auth_is_required(clean_environment):
    clean_environment.setenv('JOBFLOW_SECRET_KEY', 'test-only-secret')
    app = create_app({'TESTING': True, 'ENFORCE_AUTH_IN_TESTS': True,
                      'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    try:
        client = app.test_client()
        response = client.get('/api/health')
        assert response.status_code == 200
        assert set(response.get_json()) == {'status', 'timestamp'}
        assert client.get('/api/jobs').status_code == 401
        assert not app.debug
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
