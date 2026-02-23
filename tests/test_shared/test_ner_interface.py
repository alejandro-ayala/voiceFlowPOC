"""Unit tests for NER interface contract and NER settings parsing."""

import inspect

import pytest

from integration.configuration.settings import get_ner_model_map
from shared.interfaces.ner_interface import NERServiceInterface


@pytest.mark.unit
def test_ner_interface_is_abstract_contract():
    """NERServiceInterface must stay abstract and expose the expected API."""
    assert inspect.isabstract(NERServiceInterface)

    expected_methods = {
        "extract_locations",
        "is_service_available",
        "get_supported_languages",
        "get_service_info",
    }
    assert expected_methods.issubset(set(NERServiceInterface.__abstractmethods__))


@pytest.mark.unit
def test_get_ner_model_map_parses_and_normalizes():
    """Model map should parse valid JSON and normalize language keys."""
    parsed = get_ner_model_map('{"ES":"es_core_news_md","en":"en_core_web_sm"}')

    assert parsed["es"] == "es_core_news_md"
    assert parsed["en"] == "en_core_web_sm"


@pytest.mark.unit
def test_get_ner_model_map_fallback_on_invalid_json():
    """Invalid JSON should return the safe default model map."""
    parsed = get_ner_model_map("not-json")

    assert parsed == {"es": "es_core_news_md", "en": "en_core_web_sm"}
