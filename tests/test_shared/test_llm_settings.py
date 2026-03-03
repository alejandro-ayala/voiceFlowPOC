"""Unit tests for LLM synthesis settings (Phase 0)."""

import pytest

from integration.configuration.settings import Settings


@pytest.mark.unit
class TestLLMSettings:
    def test_defaults(self):
        s = Settings()
        assert s.llm_model == "gpt-4"
        assert s.llm_temperature == pytest.approx(0.3)
        assert s.llm_max_tokens == 2500

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("VOICEFLOW_LLM_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("VOICEFLOW_LLM_TEMPERATURE", "0.7")
        monkeypatch.setenv("VOICEFLOW_LLM_MAX_TOKENS", "1000")
        s = Settings()
        assert s.llm_model == "gpt-4o-mini"
        assert s.llm_temperature == pytest.approx(0.7)
        assert s.llm_max_tokens == 1000
