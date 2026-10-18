import pytest
from fastapi.testclient import TestClient

from patientshield.app import create_app
from patientshield.core.config import Settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings(environment="test", max_request_bytes=1024, enable_docs=False)))


@pytest.fixture
def api_client() -> TestClient:
    """A client with production-sized limits, for upload tests."""
    return TestClient(create_app(Settings(environment="test", max_request_bytes=4 * 1024 * 1024, enable_docs=False)))
