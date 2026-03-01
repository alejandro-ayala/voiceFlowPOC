"""Clientes para APIs externas (Azure, OpenAI, NER).

Avoid eager imports at package init time to prevent circular import chains.
"""

from __future__ import annotations

from importlib import import_module


def __getattr__(name: str):
    if name == "NERServiceFactory":
        return import_module("integration.external_apis.ner_factory").NERServiceFactory
    if name == "NLUServiceFactory":
        return import_module("integration.external_apis.nlu_factory").NLUServiceFactory
    if name == "SpacyNERService":
        return import_module("integration.external_apis.spacy_ner_service").SpacyNERService
    if name == "OpenAINLUService":
        return import_module("integration.external_apis.openai_nlu_service").OpenAINLUService
    if name == "KeywordNLUService":
        return import_module("integration.external_apis.keyword_nlu_service").KeywordNLUService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "NERServiceFactory",
    "NLUServiceFactory",
    "SpacyNERService",
    "OpenAINLUService",
    "KeywordNLUService",
]
