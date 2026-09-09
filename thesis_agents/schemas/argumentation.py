from typing import Literal

from pydantic import model_validator

from .base import Identifier, Message, UnitScore, require_unique


class Argument(Message):
    id: Identifier
    kind: Literal["strategy", "benefit", "impact"]
    strategy_id: Identifier
    weight: UnitScore


class Relation(Message):
    source: Identifier
    target: Identifier
    kind: Literal["support", "attack"]
    weight: UnitScore


class ArgumentationGraph(Message):
    id: Identifier
    arguments: list[Argument]
    relations: list[Relation]

    @model_validator(mode="after")
    def check_references(self):
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
    strategy_id: Identifier
    score: UnitScore


class RankingResult(Message):
    graph_id: Identifier
    backend: str
    ranking: list[RankedStrategy]

    @model_validator(mode="after")
    def check_ranking(self):
        require_unique([r.strategy_id for r in self.ranking], "ranked strategy IDs")
        if self.ranking != sorted(self.ranking, key=lambda r: (-r.score, r.strategy_id)):
            raise ValueError("Ranking must use descending score and strategy ID for ties")
        return self
