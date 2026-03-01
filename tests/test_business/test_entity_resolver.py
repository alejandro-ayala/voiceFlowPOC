"""Unit tests for EntityResolver merge rules between NLU and NER outputs."""

import pytest

from business.domains.tourism.entity_resolver import EntityResolver
from shared.models.nlu_models import NLUEntitySet, NLUResult


def _nlu_result(destination: str | None, accessibility: str | None = None) -> NLUResult:
    return NLUResult(
        intent="route_planning",
        confidence=0.9,
        entities=NLUEntitySet(destination=destination, accessibility=accessibility),
        provider="openai",
        model="gpt-4o-mini",
    )


@pytest.mark.unit
def test_entity_resolver_rule_1_both_absent():
    resolver = EntityResolver()

    result = resolver.resolve(_nlu_result(None), [], None)

    assert result.destination is None
    assert result.resolution_source["destination"] == "none"


@pytest.mark.unit
def test_entity_resolver_rule_2_only_ner_available():
    resolver = EntityResolver()

    result = resolver.resolve(_nlu_result(None), ["Prado"], "Prado")

    assert result.destination == "Prado"
    assert result.resolution_source["destination"] == "ner"


@pytest.mark.unit
def test_entity_resolver_rule_3_only_nlu_available():
    resolver = EntityResolver()

    result = resolver.resolve(_nlu_result("Museo del Prado"), [], None)

    assert result.destination == "Museo del Prado"
    assert result.resolution_source["destination"] == "nlu"


@pytest.mark.unit
def test_entity_resolver_rule_4_exact_agreement():
    resolver = EntityResolver()

    result = resolver.resolve(_nlu_result("Museo del Prado"), ["Museo del Prado"], "Museo del Prado")

    assert result.destination == "Museo del Prado"
    assert result.resolution_source["destination"] == "both_agree"


@pytest.mark.unit
def test_entity_resolver_rule_5_nlu_normalized_wins_on_fuzzy_match():
    resolver = EntityResolver()

    result = resolver.resolve(_nlu_result("Museo del Prado"), ["Prado"], "Prado")

    assert result.destination == "Museo del Prado"
    assert result.resolution_source["destination"] == "nlu_normalized"


@pytest.mark.unit
def test_entity_resolver_rule_6_real_conflict_prefers_nlu():
    resolver = EntityResolver()

    result = resolver.resolve(_nlu_result("Museo del Prado"), ["Retiro"], "Retiro")

    assert result.destination == "Museo del Prado"
    assert result.resolution_source["destination"] == "nlu_preferred"
    assert len(result.conflicts) == 1


@pytest.mark.unit
def test_entity_resolver_rule_7_generic_nlu_uses_ner_override():
    resolver = EntityResolver()

    result = resolver.resolve(_nlu_result("general"), ["Retiro"], "Retiro")

    assert result.destination == "Retiro"
    assert result.resolution_source["destination"] == "ner_override"
    assert len(result.conflicts) == 1


@pytest.mark.unit
def test_entity_resolver_preserves_raw_ner_locations_and_sources():
    resolver = EntityResolver()

    result = resolver.resolve(
        _nlu_result("Museo del Prado", accessibility="wheelchair"),
        ["Retiro", "Prado"],
        "Retiro",
    )

    assert result.locations == ["Retiro", "Prado"]
    assert result.resolution_source["accessibility"] == "nlu"
