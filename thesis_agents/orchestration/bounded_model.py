"""Limite esplicito per backend compatibili, senza eliminare messaggi o artefatti.

CAMEL usa un contatore OpenAI anche per modelli compatibili come Qwen: il
controllo è una stima con margine, non la tokenizzazione esatta del provider.
Il num_ctx del server deve essere configurato separatamente allo stesso valore.
"""

import json

from camel.models.openai_compatible_model import OpenAICompatibleModel

CONTEXT_MARGIN = 1024


class BoundedCompatibleModel(OpenAICompatibleModel):
    def __init__(self, *args, context_tokens: int, **kwargs):
        config = kwargs.get("model_config_dict") or {}
        output_tokens = config.get("max_tokens")
        if (
            not isinstance(context_tokens, int)
            or isinstance(context_tokens, bool)
            or not isinstance(output_tokens, int)
            or isinstance(output_tokens, bool)
            or output_tokens <= 0
            or context_tokens <= output_tokens + CONTEXT_MARGIN
        ):
            raise ValueError("Context budget requires positive max_tokens and a 1024-token margin")
        self.context_tokens = context_tokens
        super().__init__(*args, **kwargs)

    @property
    def token_limit(self):
        # Anche i cloni gestionali mantengono questo backend e il limite esplicito.
        return self.context_tokens

    def _check_budget(self, messages, response_format=None, tools=None):
        config = self._prepare_request_config(tools)
        if response_format is not None:
            config["response_format"] = response_format.model_json_schema()
        elif isinstance(config.get("response_format"), type):
            config["response_format"] = config["response_format"].model_json_schema()
        payload = json.dumps(
            {"messages": messages, "model_config_dict": config},
            ensure_ascii=False,
            sort_keys=True,
        )
        estimated = self.token_counter.count_tokens_from_messages(
            [{"role": "user", "content": payload}]
        )
        output_tokens = self.model_config_dict["max_tokens"]
        if estimated + output_tokens + CONTEXT_MARGIN > self.context_tokens:
            raise RuntimeError(
                f"Context budget exceeded: estimated_request={estimated}, "
                f"reserved_output={output_tokens}, margin={CONTEXT_MARGIN}, "
                f"context={self.context_tokens}. No messages truncated; request not sent."
            )

    def _run(self, messages, response_format=None, tools=None):
        self._check_budget(messages, response_format, tools)
        return super()._run(messages, response_format, tools)

    async def _arun(self, messages, response_format=None, tools=None):
        self._check_budget(messages, response_format, tools)
        return await super()._arun(messages, response_format, tools)
