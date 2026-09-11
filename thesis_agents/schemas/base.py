# Tipi e regole comuni a tutti i contratti di dominio. Non dipende da CAMEL:
# gli stessi modelli possono essere usati da test, tool locali o futuri adapter.
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Annotated associa a un tipo Python i vincoli che Pydantic applica ai valori.
# Identifier ammette ID leggibili come E1, S_UPGRADE e graph:<run>, senza spazi.
Identifier = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9_.:-]+$")]
# Text richiede almeno un carattere; non controlla il significato della frase.
Text = Annotated[str, Field(min_length=1)]
# Le stime devono essere finite e normalizzate: NaN e infinito renderebbero
# ambiguo il confronto e l'ordinamento delle strategie.
UnitScore = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class Message(BaseModel):
    # extra="forbid" intercetta anche campi inventati dal modello.
    # validate_assignment ricontrolla le assegnazioni ai campi, ma non rende
    # immutabili le liste annidate: la sessione usa copie profonde per isolarle.
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


def require_unique(values: list[str], label: str) -> None:
    # Un set elimina i duplicati: una lunghezza diversa segnala collisioni di ID.
    # Il nome del campo nel messaggio rende l'errore utilizzabile anche dall'agente.
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label}")
