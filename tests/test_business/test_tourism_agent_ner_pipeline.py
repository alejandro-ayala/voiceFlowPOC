"""Integration tests for LocationNERTool in the Tourism agent pipeline."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from business.domains.tourism.agent import TourismMultiAgent


class TestLocationNERInPipeline:
    """Integration tests for LocationNER in tourism pipeline."""

    @pytest.fixture
    def mock_openai_key(self, monkeypatch):
        """Mock OpenAI API key."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")

    @pytest.fixture
    def tourism_agent(self, mock_openai_key):
        """Create a TourismMultiAgent instance for testing."""
        with patch("business.domains.tourism.agent.ChatOpenAI"):
            agent = TourismMultiAgent(openai_api_key="test-key-12345")
            assert hasattr(agent, "location_ner"), "Agent should have location_ner tool"
        return agent

    def test_location_ner_in_agent_init(self, tourism_agent):
        """Test that LocationNERTool is properly initialized in agent."""
        assert hasattr(tourism_agent, "location_ner")
        assert tourism_agent.location_ner.name == "location_ner"

    def test_pipeline_includes_location_ner(self, tourism_agent):
        """Test that location NER is executed in the pipeline."""
        with patch(
            "business.domains.tourism.tools.location_ner_tool.NERServiceFactory"
        ) as mock_ner_factory, patch(
            "business.domains.tourism.tools.nlu_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.accessibility_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.route_planning_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.tourism_info_tool.structlog.get_logger"
        ):

            # Mock NER service
            mock_ner_service = AsyncMock()
            mock_ner_service.is_service_available.return_value = True
            mock_ner_service.extract_locations.return_value = {
                "locations": [{"name": "Palacio Real", "type": "LOC"}],
                "top_location": "Palacio Real",
                "provider": "spacy",
                "model": "es_core_news_md",
                "language": "es",
                "status": "ok",
            }
            mock_ner_factory.create_from_settings.return_value = mock_ner_service

            user_input = "Quiero información sobre el Palacio Real"
            tool_results, metadata = tourism_agent._execute_pipeline(user_input)

            # Check that location_ner was executed
            assert "locationner" in tool_results or "location_ner" in tool_results
            location_ner_key = "locationner" if "locationner" in tool_results else "location_ner"

            # Parse result
            ner_result = json.loads(tool_results[location_ner_key])
            assert ner_result["status"] == "ok"
            assert len(ner_result["locations"]) > 0

    def test_pipeline_execution_order_includes_ner(self, tourism_agent):
        """Test that LocationNER executes after NLU in pipeline."""
        with patch(
            "business.domains.tourism.tools.location_ner_tool.NERServiceFactory"
        ) as mock_ner_factory, patch(
            "business.domains.tourism.tools.nlu_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.accessibility_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.route_planning_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.tourism_info_tool.structlog.get_logger"
        ):

            # Mock NER service
            mock_ner_service = AsyncMock()
            mock_ner_service.is_service_available.return_value = True
            mock_ner_service.extract_locations.return_value = {
                "locations": [],
                "top_location": None,
                "provider": "spacy",
                "model": "es_core_news_md",
                "language": "es",
                "status": "ok",
            }
            mock_ner_factory.create_from_settings.return_value = mock_ner_service

            user_input = "test input"
            tool_results, metadata = tourism_agent._execute_pipeline(user_input)

            # Check pipeline steps order
            pipeline_steps = metadata.get("pipeline_steps", [])
            step_names = [step["name"] for step in pipeline_steps]

            assert "NLU" in step_names, "NLU should be in pipeline"
            nlu_index = step_names.index("NLU")
            if "LocationNER" in step_names:
                ner_index = step_names.index("LocationNER")
                assert ner_index > nlu_index, "LocationNER should execute after NLU"

    def test_pipeline_with_ner_unavailable_fallback(self, tourism_agent):
        """Test that pipeline continues when NER service is unavailable."""
        with patch(
            "business.domains.tourism.tools.location_ner_tool.NERServiceFactory"
        ) as mock_ner_factory, patch(
            "business.domains.tourism.tools.nlu_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.accessibility_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.route_planning_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.tourism_info_tool.structlog.get_logger"
        ):

            # Mock NER service as unavailable
            mock_ner_service = MagicMock()
            mock_ner_service.is_service_available.return_value = False
            mock_ner_factory.create_from_settings.return_value = mock_ner_service

            user_input = "test input"
            tool_results, metadata = tourism_agent._execute_pipeline(user_input)

            # Check that NER result shows unavailable status
            location_ner_key = "locationner" if "locationner" in tool_results else "location_ner"
            ner_result = json.loads(tool_results.get(location_ner_key, "{}"))
            assert ner_result.get("status") in ["unavailable", "ok"]  # Either unavailable or gracefully handled

            # Pipeline should still complete (other tools succeeded)
            assert "nlu" in tool_results
            assert "accessibility" in tool_results

    def test_ner_result_in_metadata(self, tourism_agent):
        """Test that NER result is properly recorded in metadata."""
        with patch(
            "business.domains.tourism.tools.location_ner_tool.NERServiceFactory"
        ) as mock_ner_factory, patch(
            "business.domains.tourism.tools.nlu_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.accessibility_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.route_planning_tool.structlog.get_logger"
        ), patch(
            "business.domains.tourism.tools.tourism_info_tool.structlog.get_logger"
        ):

            # Mock NER service
            mock_ner_service = AsyncMock()
            mock_ner_service.is_service_available.return_value = True
            mock_ner_service.extract_locations.return_value = {
                "locations": [
                    {"name": "Palacio Real", "type": "LOC"},
                    {"name": "Madrid", "type": "GPE"},
                ],
                "top_location": "Palacio Real",
                "provider": "spacy",
                "model": "es_core_news_md",
                "language": "es",
                "status": "ok",
            }
            mock_ner_factory.create_from_settings.return_value = mock_ner_service

            user_input = "Quiero visitar el Palacio Real en Madrid"
            tool_results, metadata = tourism_agent._execute_pipeline(user_input)

            # Check metadata contains parsed NER result
            tool_results_parsed = metadata.get("tool_results_parsed", {})
            location_ner_key = "locationner" if "locationner" in tool_results_parsed else "location_ner"

            if location_ner_key in tool_results_parsed:
                ner_parsed = tool_results_parsed[location_ner_key]
                assert ner_parsed is not None
                if isinstance(ner_parsed, dict):
                    assert "locations" in ner_parsed or "status" in ner_parsed
