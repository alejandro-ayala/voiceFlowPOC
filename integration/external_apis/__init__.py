"""Clientes para APIs externas (Azure, OpenAI, NER)."""

from integration.external_apis.ner_factory import NERServiceFactory
from integration.external_apis.mock_tourism_data_provider import MockTourismDataProvider
from integration.external_apis.spacy_ner_service import SpacyNERService
from integration.external_apis.tourism_data_provider_factory import TourismDataProviderFactory

__all__ = [
	"NERServiceFactory",
	"SpacyNERService",
	"MockTourismDataProvider",
	"TourismDataProviderFactory",
]
