from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from . import db
from .agents import (
    format_reused_solution,
    run_clarification_and_solution,
    run_conversation_agent,
)
from .config import settings
from .similarity import SimilarityIndex
from .types import SimilarityHit, TicketDraft


class GraphState(TypedDict, total=False):
    user_id: str
    user_message: str

    needs_ticket: bool
    assistant_message: str

    ticket_draft: TicketDraft
    created_ticket_id: str

    user_closed_tickets: list[dict[str, Any]]
    other_closed_tickets: list[dict[str, Any]]

    user_similarity_hits: list[SimilarityHit]
    other_similarity_hits: list[SimilarityHit]

    selected_solution: str
    selected_solution_source: Literal["user_history", "other_users", "new_solution"]
    needs_confirmation: bool
    confirmation_question: str


def conversation_agent_node(state: GraphState) -> GraphState:
    out = run_conversation_agent(state["user_message"])
    new_state: GraphState = {
        "needs_ticket": out.needs_ticket,
        "assistant_message": out.message,
    }
    if out.needs_ticket and out.ticket is not None:
        new_state["ticket_draft"] = out.ticket
    return new_state


def ticket_creation_node(state: GraphState) -> GraphState:
    draft = state["ticket_draft"]
    ticket = db.insert_ticket(
        user_id=state["user_id"],
        ticket_title=draft["ticket_title"],
        issue_description=draft["issue_description"],
        severity=draft["severity"],
        status="Open",
    )
    return {
        "created_ticket_id": ticket.ticket_id,
        "assistant_message": (
            state.get("assistant_message", "")
            + f"\n\nCreated ticket `{ticket.ticket_id}` (Severity: {ticket.severity}, Status: {ticket.status})."
        ),
    }


def ticket_resolution_agent_node(state: GraphState) -> GraphState:
    user_closed = db.list_closed_tickets_for_user(state["user_id"], limit=200)
    other_closed = db.list_closed_tickets_other_users(state["user_id"], limit=400)

    return {
        "user_closed_tickets": [t.__dict__ for t in user_closed],
        "other_closed_tickets": [t.__dict__ for t in other_closed],
    }


def similarity_check_node(state: GraphState) -> GraphState:
    issue = state["ticket_draft"]["issue_description"]

    user_index = SimilarityIndex.from_closed_tickets(state.get("user_closed_tickets", []))
    other_index = SimilarityIndex.from_closed_tickets(state.get("other_closed_tickets", []))

    user_hits = user_index.search(issue, k=5)
    other_hits = other_index.search(issue, k=5)

    def best_over_threshold(hits: list[SimilarityHit]) -> SimilarityHit | None:
        if not hits:
            return None
        best = hits[0]
        if best["score"] <= settings.similarity_threshold:
            return best
        return None

    best_user = best_over_threshold(user_hits)
    if best_user is not None:
        return {
            "user_similarity_hits": user_hits,
            "other_similarity_hits": other_hits,
            "selected_solution": format_reused_solution(
                best_user["solution"], source="from your previous ticket history"
            ),
            "selected_solution_source": "user_history",
            "needs_confirmation": False,
            "confirmation_question": "",
        }

    best_other = best_over_threshold(other_hits)
    if best_other is not None:
        return {
            "user_similarity_hits": user_hits,
            "other_similarity_hits": other_hits,
            "selected_solution": format_reused_solution(
                best_other["solution"], source="from other users' resolved tickets"
            ),
            "selected_solution_source": "other_users",
            "needs_confirmation": True,
            "confirmation_question": (
                "Does this match what you're seeing (e.g., same error message / same login method / same device)?"
            ),
        }

    clar = run_clarification_and_solution(issue)
    if clar.needs_more_info and clar.clarifying_questions:
        questions = "\n".join(f"- {q}" for q in clar.clarifying_questions)
        solution_text = (
            "I need a bit more information to resolve this quickly:\n" + questions
        )
        return {
            "selected_solution": solution_text,
            "selected_solution_source": "new_solution",
            "needs_confirmation": False,
            "confirmation_question": "",
        }

    solution = clar.solution or ""
    return {
        "selected_solution": solution,
        "selected_solution_source": "new_solution",
        "needs_confirmation": False,
        "confirmation_question": "",
    }


def solution_response_node(state: GraphState) -> GraphState:
    msg = state.get("assistant_message", "")
    msg = (msg + "\n\n" if msg else "") + state["selected_solution"]
    if state.get("needs_confirmation"):
        msg += "\n\n" + state.get("confirmation_question", "")
    return {"assistant_message": msg}


def update_ticket_node(state: GraphState) -> GraphState:
    if not state.get("created_ticket_id"):
        return {}

    if state.get("selected_solution_source") != "new_solution":
        db.update_ticket_solution(
            ticket_id=state["created_ticket_id"],
            solution=state["selected_solution"],
            status="Closed",
        )
        return {}

    solution_text = state.get("selected_solution", "")
    if solution_text.strip().startswith("I need a bit more information"):
        return {}

    if solution_text.strip():
        db.update_ticket_solution(
            ticket_id=state["created_ticket_id"],
            solution=solution_text,
            status="Closed",
        )
    return {}


def _route_after_conversation(state: GraphState) -> str:
    return "ticket_creation" if state.get("needs_ticket") else END


def build_graph():
    g = StateGraph(GraphState)

    g.add_node("conversation_agent", conversation_agent_node)
    g.add_node("ticket_creation", ticket_creation_node)
    g.add_node("ticket_resolution_agent", ticket_resolution_agent_node)
    g.add_node("similarity_check", similarity_check_node)
    g.add_node("solution_response", solution_response_node)
    g.add_node("update_ticket", update_ticket_node)

    g.set_entry_point("conversation_agent")
    g.add_conditional_edges("conversation_agent", _route_after_conversation)

    g.add_edge("ticket_creation", "ticket_resolution_agent")
    g.add_edge("ticket_resolution_agent", "similarity_check")
    g.add_edge("similarity_check", "solution_response")
    g.add_edge("solution_response", "update_ticket")
    g.add_edge("update_ticket", END)

    return g.compile()


def run_support_flow(user_id: str, user_message: str) -> GraphState:
    app = build_graph()
    return app.invoke({"user_id": user_id, "user_message": user_message})
