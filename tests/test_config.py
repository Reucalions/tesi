"""Configurazione esplicita del campionamento senza richieste al provider."""

import pytest

from thesis_agents.config import ModelSettings


@pytest.mark.parametrize("value", ["nan", "inf", "-0.1", "2.1"])
def test_invalid_temperature(monkeypatch, value):
    monkeypatch.setenv("LLM_MODEL", "local-test")
    monkeypatch.setenv("LLM_API_KEY", "local")
    monkeypatch.setenv("LLM_TEMPERATURE", value)
    with pytest.raises(ValueError, match="LLM_TEMPERATURE"):
        ModelSettings.from_env()


@pytest.mark.parametrize("value, expected", [("", {}), ("0", {"temperature": 0.0})])
def test_temperature_is_sent_only_when_configured(monkeypatch, value, expected):
    from camel.models import ModelFactory

    monkeypatch.setenv("LLM_MODEL", "local-test")
    monkeypatch.setenv("LLM_API_KEY", "local")
    monkeypatch.setenv("LLM_TEMPERATURE", value)
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
    monkeypatch.setattr(ModelFactory, "create", lambda **kwargs: kwargs)
    backend_arguments = ModelSettings.from_env().create_backend()
    assert backend_arguments["model_config_dict"] == expected


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "nan", "unlimited"])
def test_invalid_max_tokens(monkeypatch, value):
    monkeypatch.setenv("LLM_MODEL", "local-test")
    monkeypatch.setenv("LLM_API_KEY", "local")
    monkeypatch.setenv("LLM_TEMPERATURE", "")
    monkeypatch.setenv("LLM_MAX_TOKENS", value)
    with pytest.raises(ValueError, match="LLM_MAX_TOKENS"):
        ModelSettings.from_env()


def test_max_tokens_is_sent_to_model_backend(monkeypatch):
    from camel.models import ModelFactory

    monkeypatch.setenv("LLM_MODEL", "local-test")
    monkeypatch.setenv("LLM_API_KEY", "local")
    monkeypatch.setenv("LLM_TEMPERATURE", "0")
    monkeypatch.setenv("LLM_MAX_TOKENS", "2048")
    monkeypatch.setattr(ModelFactory, "create", lambda **kwargs: kwargs)
    backend_arguments = ModelSettings.from_env().create_backend()
    assert backend_arguments["model_config_dict"] == {"temperature": 0.0, "max_tokens": 2048}
