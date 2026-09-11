# Contratti del dato osservato: input statico e output separato di TelemetryAgent.
# La trasformazione cambia la struttura, non i fatti software/versione/esposizione.
# Un eventuale ingresso OpenTelemetry richiederà un adapter, non presente qui.
from pydantic import Field, StrictBool, model_validator

from .base import Identifier, Message, Text, require_unique


class StaticTelemetry(Message):
    # Un servizio e un pacchetto costituiscono il caso minimo del prototipo.
    service_name: Identifier
    package_name: Text
    package_version: Text
    endpoint_exposed: StrictBool
    # StrictBool rifiuta stringhe come "false": i fatti devono essere booleani JSON.
    deserialization_observed: StrictBool
    available_capabilities: list[Text] = Field(default_factory=list)
    # Le capacità sono prerequisiti operativi; le azioni proibite sono policy del
    # caso. default_factory crea liste nuove per ogni istanza, non liste condivise.
    prohibited_actions: list[Text] = Field(default_factory=list)


class SoftwareObservation(Message):
    # Associa identità software e versione a un evidence_id, che il lookup riporta
    # nelle vulnerabilità trovate per mantenere un riferimento all'osservazione.
    package: Text
    version: Text
    evidence_id: Identifier


class RuntimeEvidence(Message):
    # Artefatto di TelemetryAgent: rimane disponibile separatamente dal report KG.
    # Lo schema ammette più osservazioni, ma ArtifactSession limita il caso a una.
    service_name: Identifier
    software: list[SoftwareObservation] = Field(min_length=1)
    endpoint_exposed: StrictBool
    deserialization_observed: StrictBool
    observations: list[Text]
    # observations aggiunge note descrittive; Pydantic non ne verifica la veridicità.

    @model_validator(mode="after")
    def unique_evidence(self):
        # Il validatore «after» viene eseguito dopo i controlli sui singoli campi.
        # Due osservazioni non possono utilizzare lo stesso riferimento di evidenza.
        require_unique([s.evidence_id for s in self.software], "evidence IDs")
        return self
