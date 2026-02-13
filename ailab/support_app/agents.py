from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .llm import get_chat_llm
from .types import Severity, TicketDraft


class ConversationOutput(BaseModel):
    needs_ticket: bool = Field(
        description="True when the user is reporting a login/authentication problem that should become a ticket."
    )
    message: str = Field(description="Assistant message to show the user.")
    ticket: TicketDraft | None = Field(
        default=None,
        description="If needs_ticket is true, provide a structured ticket draft.",
    )


class TicketDraftModel(BaseModel):
    ticket_title: str
    issue_description: str
    severity: Severity


def run_conversation_agent(user_message: str) -> ConversationOutput:
    llm = get_chat_llm()

    structured_llm = llm.with_structured_output(ConversationOutput)
    prompt = (
        "You are a helpful IT support assistant specializing in login/auth issues. "
        "Classify whether the user's message is a login/authentication issue. "
        "If it is, set needs_ticket=true and create a concise ticket draft with: "
        "ticket_title (short), issue_description (detailed), severity (Low/Medium/High/Critical). "
        "Severity guidance: Critical=production outage or no user can login; High=account locked or 2FA blocking; "
        "Medium=frequent failures, OTP not received; Low=intermittent or browser cache/session issues. "
        "If not a login/auth issue, set needs_ticket=false and answer normally with troubleshooting guidance. "
        "Be brief and actionable.\n\n"
        f"User message: {user_message}"
    )

    return structured_llm.invoke(prompt)


class ClarificationOutput(BaseModel):
    needs_more_info: bool
    clarifying_questions: list[str] = Field(default_factory=list)
    solution: str | None = None


def run_clarification_and_solution(issue_description: str) -> ClarificationOutput:
    llm = get_chat_llm()
    structured_llm = llm.with_structured_output(ClarificationOutput)
    prompt = (
        "You are a ticket resolution agent for login issues. "
        "If the issue description is too vague, ask 2-4 specific clarifying questions and set needs_more_info=true. "
        "If enough info is present, set needs_more_info=false and produce a detailed step-by-step solution. "
        "Solutions must be structured and reusable (use numbered steps, include common causes, and escalation notes).\n\n"
        f"Issue description: {issue_description}"
    )
    return structured_llm.invoke(prompt)


def format_reused_solution(solution: str, source: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"I found a similar resolved ticket ({source}). Here is the proven fix as of {timestamp}:\n\n{solution}"
    )
