from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from ..database import sb_select
from .competitive_agent import run_competitive_agent
from .recommendation_agent import run_recommendation_agent
from .risk_agent import run_risk_agent
from .types import CustomerAnalysisResult, RiskAssessment


class AnalysisState(TypedDict, total=False):
    customer_id: str
    deposits: list[dict[str, Any]]
    settings: dict[str, Any]
    risk: RiskAssessment
    recommendation: Any
    competitive: Any


async def _fetch_deposits(state: AnalysisState) -> AnalysisState:
    customer_id = state["customer_id"]
    rows = await sb_select(
        "fixed_deposits",
        select="*",
        filters={"customer_id": f"eq.{customer_id}"},
        order="start_date.desc",
    )
    state["deposits"] = rows
    return state


async def _risk(state: AnalysisState) -> AnalysisState:
    state["risk"] = await run_risk_agent(state.get("deposits", []))
    return state


async def _recommend(state: AnalysisState) -> AnalysisState:
    state["recommendation"] = await run_recommendation_agent(
        history_rows=state.get("deposits", []),
        risk=state["risk"],
        settings=state["settings"],
    )
    return state


async def _competitive(state: AnalysisState) -> AnalysisState:
    penalty_percent = float(state["settings"].get("penalty_percent") or 1.0)
    state["competitive"] = await run_competitive_agent(
        history_rows=state.get("deposits", []),
        risk=state["risk"],
        penalty_percent=penalty_percent,
    )
    return state


def build_graph():
    g = StateGraph(AnalysisState)
    g.add_node("fetch_deposits", _fetch_deposits)
    g.add_node("risk", _risk)
    g.add_node("recommend", _recommend)
    g.add_node("competitive", _competitive)

    g.set_entry_point("fetch_deposits")
    g.add_edge("fetch_deposits", "risk")
    g.add_edge("risk", "recommend")
    g.add_edge("recommend", "competitive")
    g.add_edge("competitive", END)

    return g.compile()


async def analyze_customer(*, customer_id: str, settings: dict[str, Any]) -> CustomerAnalysisResult:
    graph = build_graph()
    final: AnalysisState = await graph.ainvoke({"customer_id": customer_id, "settings": settings})

    return CustomerAnalysisResult(
        customer_id=customer_id,
        analyzed_at=datetime.now(timezone.utc),
        risk=final["risk"],
        recommendation=final["recommendation"],
        competitive=final["competitive"],
    )
