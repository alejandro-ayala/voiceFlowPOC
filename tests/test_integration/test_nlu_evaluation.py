"""Corpus-based evaluation tests for NLU providers."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from integration.configuration.settings import Settings
from integration.external_apis.keyword_nlu_service import KeywordNLUService
from integration.external_apis.openai_nlu_service import OpenAINLUService

CORPUS_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "nlu_evaluation_corpus.json"
)


def _load_corpus() -> list[dict]:
    with CORPUS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


async def _evaluate_accuracy(service, corpus: list[dict]) -> float:
    total = 0
    correct = 0
    for sample in corpus:
        text = sample.get("text", "")
        expected_intent = sample.get("intent", "general_query")
        result = await service.analyze_text(text, language="es")

        total += 1
        if result.intent == expected_intent:
            correct += 1

    return correct / total if total else 0.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_keyword_nlu_accuracy_on_evaluation_corpus():
    """Keyword fallback provider should keep baseline intent accuracy."""
    corpus = _load_corpus()
    service = KeywordNLUService(settings=Settings())

    accuracy = await _evaluate_accuracy(service, corpus)

    assert accuracy >= 0.70, f"Keyword accuracy below baseline: {accuracy:.2%}"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not configured"
)
async def test_openai_nlu_accuracy_on_evaluation_corpus():
    """OpenAI provider should meet target intent accuracy on the labeled corpus."""
    corpus = _load_corpus()
    service = OpenAINLUService(settings=Settings(nlu_provider="openai"))

    if not service.is_service_available():
        pytest.skip("OpenAI NLU provider unavailable in runtime")

    accuracy = await _evaluate_accuracy(service, corpus)

    assert accuracy >= 0.90, f"OpenAI accuracy target not met: {accuracy:.2%}"
