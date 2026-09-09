import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelSettings:
    model: str
    api_key: str = field(repr=False)
    base_url: str | None = None
    timeout: float = 120

    @classmethod
    def from_env(cls) -> "ModelSettings":
        model = os.getenv("LLM_MODEL", "").strip()
        key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        if not model or not key:
            raise ValueError(
                "Configura LLM_MODEL e LLM_API_KEY nel file .env. "
                "Per verificare solo i tool senza LLM: python main.py --mode fixtures"
            )
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
        if not 0 < timeout <= 600:
            raise ValueError("LLM_TIMEOUT_SECONDS deve essere compreso tra 0 e 600")
        return cls(model, key, os.getenv("LLM_BASE_URL") or None, timeout)

    def create_backend(self):
        from camel.models import ModelFactory

        return ModelFactory.create(
            model_platform="openai-compatible-model" if self.base_url else "openai",
            model_type=self.model,
            api_key=self.api_key,
            url=self.base_url,
            model_config_dict={},
            timeout=self.timeout,
            max_retries=1,
        )
