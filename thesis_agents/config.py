# Configurazione del modello separata dagli agenti e dai tool di dominio.
# Il chiamante carica eventualmente .env; questo modulo legge soltanto le variabili
# d'ambiente e costruisce il backend CAMEL richiesto, senza effettuare inferenza.
import math
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelSettings:
    # frozen=True impedisce riassegnazioni accidentali durante un run.
    # repr=False nasconde la chiave nella rappresentazione dell'oggetto, ma non
    # cifra il valore: è comunque una credenziale conservata in memoria.
    model: str
    api_key: str = field(repr=False)
    base_url: str | None = None
    timeout: float = 120
    temperature: float | None = None

    @classmethod
    def from_env(cls) -> "ModelSettings":
        # Il nome del modello è esplicito; per la chiave si accetta prima il nome
        # generico del progetto e poi OPENAI_API_KEY per compatibilità di configurazione.
        model = os.getenv("LLM_MODEL", "").strip()
        key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        if not model or not key:
            raise ValueError(
                "Configura LLM_MODEL e LLM_API_KEY nel file .env. "
                "Per verificare solo i tool senza LLM: python main.py --mode fixtures"
            )
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
        # Il limite riguarda le richieste del backend. La Workforce e ChatAgent
        # hanno anche limiti propri, configurati nel modulo di orchestrazione.
        if not 0 < timeout <= 600:
            raise ValueError("LLM_TIMEOUT_SECONDS deve essere compreso tra 0 e 600")
        value = os.getenv("LLM_TEMPERATURE", "").strip()
        temperature = float(value) if value else None
        if temperature is not None and (
            not math.isfinite(temperature) or not 0 <= temperature <= 2
        ):
            raise ValueError("LLM_TEMPERATURE deve essere compresa tra 0 e 2")
        return cls(model, key, os.getenv("LLM_BASE_URL") or None, timeout, temperature)

    def create_backend(self):
        # L'import locale mantiene la lettura della configurazione indipendente
        # dall'importazione dell'SDK fino alla costruzione effettiva del backend.
        from camel.models import ModelFactory

        return ModelFactory.create(
            # Un URL esplicito seleziona il backend compatibile, utile anche per un
            # server locale. Altrimenti viene scelto il backend OpenAI di CAMEL.
            model_platform="openai-compatible-model" if self.base_url else "openai",
            model_type=self.model,
            api_key=self.api_key,
            url=self.base_url,
            # Omette la temperatura salvo richiesta esplicita: alcuni provider o
            # modelli non la supportano. Per Ollama la passiamo nel payload HTTP,
            # senza dipendere dal default dell'endpoint compatibile OpenAI.
            model_config_dict=(
                {"temperature": self.temperature} if self.temperature is not None else {}
            ),
            timeout=self.timeout,
            max_retries=1,
        )
