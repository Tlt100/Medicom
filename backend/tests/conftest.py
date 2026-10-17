import pytest
from fastapi.testclient import TestClient

from patientshield.app import create_app
from patientshield.config import Settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings(environment="test", max_request_bytes=1024, enable_docs=False)))
