# Costruzione del grafo dimostrativo e ranking numerico del mock.
# Sono due operazioni distinte: build_graph organizza le stime delle candidate,
# rank_graph le valuta con una somma pesata a un passo, senza inferenza LLM.
# La formula è didattica e non ricostruisce l'algoritmo del contratto BWAF reale.
from thesis_agents.schemas import ArgumentationGraph, CandidateStrategies, RankingResult
from thesis_agents.schemas.argumentation import Argument, RankedStrategy, Relation


def build_graph(candidates: CandidateStrategies, graph_id: str) -> ArgumentationGraph:
    """Explicit graph projection of candidate estimates; no LLM ranking."""
    arguments, relations = [], []
    for s in candidates.strategies:
        # Ogni candidata genera tre nodi: radice strategia, beneficio e impatto.
        # I prefissi evitano collisioni fra i diversi nodi della medesima strategia.
        root = f"strategy:{s.id}"
        arguments.append(Argument(id=root, kind="strategy", strategy_id=s.id, weight=0.5))
        for kind, weight, relation in [
            ("benefit", s.security_benefit, "support"),
            ("impact", s.operational_impact, "attack"),
        ]:
            node_id = f"{kind}:{s.id}"
            arguments.append(Argument(id=node_id, kind=kind, strategy_id=s.id, weight=weight))
            relations.append(Relation(source=node_id, target=root, kind=relation, weight=0.5))
            # Tutti gli archi hanno intensità 0.5; i pesi dei nodi sorgente portano
            # le stime di beneficio/impatto. Si ottiene 0.5 + 0.5*beneficio - 0.5*impatto.
    return ArgumentationGraph(id=graph_id, arguments=arguments, relations=relations)


class MockRankingTool:
    """One-hop signed weighted sum, NOT the BWAF smart-contract algorithm."""

    def rank_graph(self, graph: ArgumentationGraph) -> RankingResult:
        # Indicizzazione per ID per recuperare il peso sorgente di ciascun arco.
        arguments = {a.id: a for a in graph.arguments}
        ranked = []
        for node in graph.arguments:
            if node.kind != "strategy":
                # Solo le radici diventano voci di classifica; gli altri nodi
                # contribuiscono allo score ma non sono strategie selezionabili.
                continue
            score = node.weight
            for edge in graph.relations:
                # Si considerano solo archi entranti e i pesi originali delle sorgenti:
                # non c'è propagazione iterativa né risoluzione di cicli argomentativi.
                if edge.target == node.id:
                    sign = 1 if edge.kind == "support" else -1
                    score += sign * edge.weight * arguments[edge.source].weight
            ranked.append(
                # Clamp nell'intervallo ammesso, poi arrotondamento a otto decimali.
                RankedStrategy(strategy_id=node.strategy_id, score=round(max(0, min(1, score)), 8))
            )
        return RankingResult(
            graph_id=graph.id,
            backend="signed-one-hop-mock-v1",
            ranking=sorted(ranked, key=lambda r: (-r.score, r.strategy_id)),
            # Il segno meno ordina per score decrescente; l'ID risolve i pareggi.
        )
