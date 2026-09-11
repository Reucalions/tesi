# Formato della provenienza locale: entità, attività e produttori del run.
# È una rappresentazione preparatoria al futuro collegamento PROV-O/Fabric;
# non è un'ontologia serializzata né un insieme di transazioni blockchain.
from typing import Literal

from .base import Identifier, Message, Text


class ProvenanceEntity(Message):
    # Collega un artefatto logico al file che lo rappresenta e al suo digest SHA-256.
    # Il digest è una stringa nello schema; viene calcolato sui byte dalla sessione.
    id: Identifier
    filename: Text
    sha256: Text


class ProvenanceActivity(Message):
    # used e generated contengono ID di entità: permettono di risalire dagli output
    # ai dati consumati. agent indica il ruolo responsabile dell'attività di dominio.
    id: Identifier
    agent: Text
    used: list[Identifier]
    generated: list[Identifier]


class ProvenanceRecord(Message):
    # run_id distingue le esecuzioni. mode e model distinguono uso reale di CAMEL,
    # inferenza programmata nei test e fixture senza modello. created_at è registrato
    # dalla sessione alla sua creazione, non è un timestamp per ciascuna attività.
    run_id: Identifier
    mode: Literal["camel", "fixtures"]
    backend: Literal["local-provenance-mock-v1"] = "local-provenance-mock-v1"
    model: str | None
    created_at: Text
    entities: list[ProvenanceEntity]
    # Il record elenca input e sette output di dominio; non include l'hash di se stesso,
    # che creerebbe un riferimento circolare impossibile da stabilizzare in questo modo.
    activities: list[ProvenanceActivity]
    agents: list[Text]
