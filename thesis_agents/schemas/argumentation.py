# Modelli del grafo argomentativo e del risultato di ranking.
# Descrivono il formato scambiato con il tool; non implementano la semantica BWAF.
# La validità strutturale di un grafo non dimostra la correttezza delle sue stime.
from typing import Literal

from pydantic import model_validator

from .base import Identifier, Message, UnitScore, require_unique


class Argument(Message):
    # Un nodo rappresenta una strategia, il suo beneficio oppure il suo impatto.
    # strategy_id collega anche i nodi ausiliari alla proposta da cui derivano.
    id: Identifier
    kind: Literal["strategy", "benefit", "impact"]
    strategy_id: Identifier
    weight: UnitScore


class Relation(Message):
    # Arco diretto con peso normalizzato: support aumenta lo score nel mock,
    # attack lo riduce. source e target fanno riferimento agli ID dei nodi.
    source: Identifier
    target: Identifier
    kind: Literal["support", "attack"]
    weight: UnitScore


class ArgumentationGraph(Message):
    # L'ID del grafo permette alla sessione di rifiutare un ranking restituito
    # per un'altra analisi. I nodi e gli archi rimangono dati Pydantic serializzabili.
    id: Identifier
    arguments: list[Argument]
    relations: list[Relation]

    @model_validator(mode="after")
    def check_references(self):
        # Controlli fra elementi: unicità dei nodi, una radice per strategia,
        # riferimenti esistenti e assenza di auto-archi. Non è un controllo dei cicli
        # né una validazione della semantica del vero algoritmo BWAF.
        ids = [a.id for a in self.arguments]
        require_unique(ids, "argument IDs")
        strategies = [a.strategy_id for a in self.arguments if a.kind == "strategy"]
        require_unique(strategies, "strategy arguments")
        if any(a.strategy_id not in strategies for a in self.arguments):
            raise ValueError("Every argument must reference a strategy node")
        for r in self.relations:
            if r.source not in ids or r.target not in ids or r.source == r.target:
                raise ValueError("Invalid graph relation")
        return self


class RankedStrategy(Message):
    # Una voce della classifica: l'ID individua la candidata e score è del backend.
    strategy_id: Identifier
    score: UnitScore


class RankingResult(Message):
    # backend rende riconoscibile l'implementazione che ha calcolato la classifica.
    # La sessione verifica inoltre che l'insieme degli ID coincida con le candidate.
    graph_id: Identifier
    backend: str
    ranking: list[RankedStrategy]

    @model_validator(mode="after")
    def check_ranking(self):
        # Lo schema verifica l'ordine, non lo corregge silenziosamente. Il tie-break
        # alfabetico per ID evita che i pareggi dipendano dall'ordine di inserimento.
        require_unique([r.strategy_id for r in self.ranking], "ranked strategy IDs")
        if self.ranking != sorted(self.ranking, key=lambda r: (-r.score, r.strategy_id)):
            raise ValueError("Ranking must use descending score and strategy ID for ties")
        return self
