from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9_.:-]+$")]
Text = Annotated[str, Field(min_length=1)]
UnitScore = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


def require_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label}")
