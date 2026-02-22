"""Clientes para APIs externas (Azure, OpenAI, NER)."""

from integration.external_apis.ner_factory import NERServiceFactory
from integration.external_apis.spacy_ner_service import SpacyNERService

__all__ = ["NERServiceFactory", "SpacyNERService"]
