"""Clientes para APIs externas (Azure, OpenAI, NER)."""

from integration.external_apis.keyword_nlu_service import KeywordNLUService
from integration.external_apis.ner_factory import NERServiceFactory
from integration.external_apis.nlu_factory import NLUServiceFactory
from integration.external_apis.openai_nlu_service import OpenAINLUService
from integration.external_apis.spacy_ner_service import SpacyNERService

__all__ = [
    "NERServiceFactory",
    "NLUServiceFactory",
    "SpacyNERService",
    "OpenAINLUService",
    "KeywordNLUService",
]
