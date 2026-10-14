"""ChatAgent CAMEL con memoria integrale per i contratti del prototipo.

CAMEL 0.2.90 riattiva il default summarize_threshold=50 in clone(). I worker
del pool sono cloni: configurare soltanto l'agente iniziale non è sufficiente.
Si preservano qui le opzioni costruttive dei nostri agenti anche nei cloni.
"""

from camel.agents import ChatAgent


class ArtifactChatAgent(ChatAgent):
    def __init__(self, system_message=None, model=None, *, tool_policy=None, **kwargs):
        self.tool_policy = tool_policy
        kwargs["summarize_threshold"] = None
        self._clone_options = dict(kwargs)
        if tool_policy is not None:
            kwargs["response_terminators"] = [tool_policy]
        super().__init__(system_message=system_message, model=model, **kwargs)

    def clone(self, with_memory=False):
        tools, toolkits = self._clone_tools()
        options = self._clone_options | {
            "tools": tools,
            "toolkits_to_register_agent": toolkits,
            "token_limit": self.token_limit,
            "stop_event": self.stop_event,
            "pause_event": self.pause_event,
            "tool_policy": self.tool_policy.clone() if self.tool_policy else None,
        }
        # Ogni clone riceve memoria nuova. Gli artefatti restano nella sessione
        # condivisa; non diventano riassunti generativi nella memoria del worker.
        options.pop("memory", None)
        options.pop("agent_id", None)
        cloned = type(self)(
            system_message=self.system_message,
            model=self.model_backend.models,
            **options,
        )
        if with_memory:
            cloned.memory.clear()
            for record in self.memory.retrieve():
                cloned.memory.write_record(record.memory_record)
        return cloned

    def _get_full_tool_schemas(self):
        schemas = super()._get_full_tool_schemas()
        if self.tool_policy is None:
            return schemas
        next_tool = self.tool_policy.next_tool()
        return [schema for schema in schemas if schema["function"]["name"] == next_tool]

    def _phase_messages(self, messages):
        if self.tool_policy is None:
            return messages
        # Indicazione per la singola richiesta: non modifica artefatti o memoria
        # e viene conteggiata nel budget del backend insieme al payload completo.
        return [*messages, {"role": "user", "content": self.tool_policy.instruction()}]

    def _get_model_response(self, openai_messages, **kwargs):
        return super()._get_model_response(self._phase_messages(openai_messages), **kwargs)

    async def _aget_model_response(self, openai_messages, **kwargs):
        return await super()._aget_model_response(self._phase_messages(openai_messages), **kwargs)

    def _reject_out_of_phase(self, request):
        if self.tool_policy and request.tool_name != self.tool_policy.next_tool():
            return self._record_tool_calling(
                request.tool_name,
                request.args,
                "Tool execution failed: " + self.tool_policy.instruction(),
                request.tool_call_id,
                extra_content=request.extra_content,
            )
        return None

    def _execute_tool(self, request):
        rejected = self._reject_out_of_phase(request)
        if rejected is not None:
            return rejected
        result = super()._execute_tool(request)
        if self.tool_policy:
            self.tool_policy.observe(request.tool_name, result.result)
        return result

    async def _aexecute_tool(self, request):
        rejected = self._reject_out_of_phase(request)
        if rejected is not None:
            return rejected
        result = await super()._aexecute_tool(request)
        if self.tool_policy:
            self.tool_policy.observe(request.tool_name, result.result)
        return result
