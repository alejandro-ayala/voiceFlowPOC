"""Integration tests for spaCy NER provider behavior."""

from types import SimpleNamespace

import pytest

from integration.configuration.settings import Settings
from integration.external_apis import spacy_ner_service
from integration.external_apis.spacy_ner_service import SpacyNERService


def _build_doc(entities: list[tuple[str, str]]):
    ents = [SimpleNamespace(text=text, label_=label) for text, label in entities]
    return SimpleNamespace(ents=ents)


def _build_fake_nlp(entities: list[tuple[str, str]]):
    def _nlp(_text: str):
        return _build_doc(entities)

    return _nlp


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spacy_service_extracts_locations_spanish(monkeypatch):
    """Service extracts LOC/GPE/FAC entities and deduplicates locations."""
    settings = Settings(
        ner_enabled=True,
        ner_default_language="es",
        ner_model_map='{"es":"es_core_news_md","en":"en_core_web_sm"}',
        ner_fallback_model="es_core_news_sm",
    )
    service = SpacyNERService(settings=settings)

    monkeypatch.setattr(spacy_ner_service, "SPACY_AVAILABLE", True)
    monkeypatch.setattr(
        spacy_ner_service,
        "spacy",
        SimpleNamespace(
            load=lambda model: _build_fake_nlp(
                [
                    ("Barcelona", "GPE"),
                    ("Barcelona", "LOC"),
                    ("Palacio Real", "FAC"),
                    ("lunes", "DATE"),
                ]
            )
        ),
    )

    result = await service.extract_locations("Quiero visitar Barcelona y el Palacio Real", language="es")

    assert result["status"] == "ok"
    assert result["language"] == "es"
    assert result["provider"] == "spacy"
    assert result["top_location"] == "Barcelona"
    assert result["locations"] == ["Barcelona", "Palacio Real"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spacy_service_supports_english_model_map(monkeypatch):
    """Service should resolve English model when language=en."""
    settings = Settings(
        ner_enabled=True,
        ner_default_language="es",
        ner_model_map='{"es":"es_core_news_md","en":"en_core_web_sm"}',
        ner_fallback_model="es_core_news_sm",
    )
    service = SpacyNERService(settings=settings)

    monkeypatch.setattr(spacy_ner_service, "SPACY_AVAILABLE", True)
    monkeypatch.setattr(
        spacy_ner_service,
        "spacy",
        SimpleNamespace(load=lambda model: _build_fake_nlp([("London", "GPE"), ("Paris", "GPE")])),
    )

    result = await service.extract_locations("Trip from London to Paris", language="en")

    assert result["status"] == "ok"
    assert result["language"] == "en"
    assert result["model"] == "en_core_web_sm"
    assert result["locations"] == ["London", "Paris"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spacy_service_fallback_when_primary_model_missing(monkeypatch):
    """If primary model fails, service should fallback to configured fallback model."""
    settings = Settings(
        ner_enabled=True,
        ner_default_language="es",
        ner_model_map='{"es":"es_core_news_md"}',
        ner_fallback_model="es_core_news_sm",
    )
    service = SpacyNERService(settings=settings)

    def _load(model_name: str):
        if model_name == "es_core_news_md":
            raise OSError("model not found")
        return _build_fake_nlp([("Madrid", "GPE")])

    monkeypatch.setattr(spacy_ner_service, "SPACY_AVAILABLE", True)
    monkeypatch.setattr(spacy_ner_service, "spacy", SimpleNamespace(load=_load))

    result = await service.extract_locations("Quiero ir a Madrid", language="es")

    assert result["status"] == "ok"
    assert result["locations"] == ["Madrid"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spacy_service_returns_model_unavailable_when_no_model_loads(monkeypatch):
    """If all model loads fail, service should degrade gracefully."""
    settings = Settings(
        ner_enabled=True,
        ner_default_language="es",
        ner_model_map='{"es":"es_core_news_md"}',
        ner_fallback_model="es_core_news_sm",
    )
    service = SpacyNERService(settings=settings)

    monkeypatch.setattr(spacy_ner_service, "SPACY_AVAILABLE", True)
    monkeypatch.setattr(
        spacy_ner_service,
        "spacy",
        SimpleNamespace(load=lambda _model: (_ for _ in ()).throw(OSError("model not found"))),
    )

    result = await service.extract_locations("Sevilla", language="es")

    assert result["status"] == "model_unavailable"
    assert result["locations"] == []
