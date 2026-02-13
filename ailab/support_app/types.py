from __future__ import annotations

from typing import Literal, TypedDict


Severity = Literal["Low", "Medium", "High", "Critical"]


class TicketDraft(TypedDict):
    ticket_title: str
    issue_description: str
    severity: Severity


class SimilarityHit(TypedDict):
    ticket_id: str
    user_id: str
    issue_description: str
    solution: str
    score: float
