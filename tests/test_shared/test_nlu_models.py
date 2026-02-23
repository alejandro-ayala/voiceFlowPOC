"""Unit tests for NLU shared models and NLU settings defaults."""

import pytest
from pydantic import ValidationError

from integration.configuration.settings import Settings
from shared.models.nlu_models import NLUEntitySet, NLUResult, ResolvedEntities


@pytest.mark.unit
def test_nlu_result_defaults_and_roundtrip_json():
    """NLUResult should keep defaults and support JSON round-trip."""
    original = NLUResult(
        status="ok",
        intent="event_search",
        confidence=0.92,
        entities=NLUEntitySet(destination="Madrid", accessibility="wheelchair"),
        provider="openai",
        model="gpt-4o-mini",
    )

    serialized = original.model_dump_json()
    restored = NLUResult.model_validate_json(serialized)

    assert restored.intent == "event_search"
    assert restored.confidence == pytest.approx(0.92)
    assert restored.entities.destination == "Madrid"
    assert restored.entities.accessibility == "wheelchair"
    assert restored.status == "ok"


@pytest.mark.unit
def test_nlu_entity_set_all_none_is_valid():
    """Empty entity set should be valid with all optional fields as None."""
    entities = NLUEntitySet()

    assert entities.destination is None
    assert entities.accessibility is None
    assert entities.timeframe is None
    assert entities.transport_preference is None
    assert entities.budget is None
    assert entities.extra == {}


@pytest.mark.unit
def test_resolved_entities_defaults_are_empty_collections():
    """Resolved entities should default to empty conflict/source metadata."""
    resolved = ResolvedEntities()

    assert resolved.conflicts == []
    assert resolved.resolution_source == {}
    assert resolved.locations == []


@pytest.mark.unit
@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_nlu_result_invalid_confidence_raises_validation_error(confidence: float):
    """Confidence must stay in [0,1] range."""
    with pytest.raises(ValidationError):
        NLUResult(confidence=confidence)


@pytest.mark.unit
def test_nlu_settings_defaults_openai_provider_and_model():
    """NLU settings defaults should match plan baseline."""
    settings = Settings()

    assert settings.nlu_provider == "openai"
    assert settings.nlu_openai_model == "gpt-4o-mini"
