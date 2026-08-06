from typing import Literal

from pydantic import BaseModel


class SplitParticipant(BaseModel):
    name: str
    amount: float | None = None


class ParsedTransaction(BaseModel):
    transaction_type: Literal["income", "expense", "incoming_payment"]
    amount: float
    currency: Literal["RUB", "USD", "EUR"] | None = None
    date: str | None = None
    counterparty: str | None = None
    organization_id: Literal[1, 2] | None = None
    category: str | None = None
    is_offset: bool = False
    split_participants: list[SplitParticipant] | None = None
    confidence: int
    needs_clarification: list[str] = []
