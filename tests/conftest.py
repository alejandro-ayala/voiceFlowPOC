"""
Shared test fixtures for VoiceFlow PoC tests.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from presentation.fastapi_factory import create_application

    app = create_application()
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    from integration.configuration.settings import Settings

    return Settings(
        debug=True,
        use_real_agents=False,
    )


@pytest.fixture
def nlu_evaluation_corpus():
    """Load labeled corpus used by NLU evaluation tests."""
    corpus_path = Path(__file__).resolve().parent / "fixtures" / "nlu_evaluation_corpus.json"
    with corpus_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
