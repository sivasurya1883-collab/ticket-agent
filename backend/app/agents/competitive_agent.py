from __future__ import annotations

from typing import Any

from ..llm_service import LLMConnectionError, LLMNotConfigured, get_chat_llm
from .types import CompetitiveAdvantage, RiskAssessment


def compute_loyalty_score(history_rows: list[dict[str, Any]]) -> int:
    if not history_rows:
        return 30

    active = sum(1 for r in history_rows if (r.get("status") or "").upper() == "ACTIVE")
    closed = sum(1 for r in history_rows if (r.get("status") or "").upper() == "CLOSED")

    premature = 0
    for r in history_rows:
        if (r.get("status") or "").upper() == "CLOSED":
            closed_at = r.get("closed_at")
            maturity_date = r.get("maturity_date")
            if closed_at and maturity_date and str(closed_at) < str(maturity_date):
                premature += 1

    base = 50
    base += min(25, active * 8)
    base += min(15, closed * 3)
    base -= min(40, premature * 15)

    return max(0, min(100, int(round(base))))


def compute_penalty_reduction_percent(*, loyalty_score: int, risk: RiskAssessment) -> float:
    if risk.risk_category == "Low" and loyalty_score >= 80:
        return 1.0
    if risk.risk_category in {"Low", "Moderate"} and loyalty_score >= 65:
        return 0.5
    return 0.0


async def run_competitive_agent(
    *,
    history_rows: list[dict[str, Any]],
    risk: RiskAssessment,
    penalty_percent: float,
) -> CompetitiveAdvantage:
    loyalty_score = compute_loyalty_score(history_rows)
    reduction = compute_penalty_reduction_percent(loyalty_score=loyalty_score, risk=risk)
    adaptive_penalty = max(0.0, float(penalty_percent) - float(reduction))

    eligibility = (
        f"Eligible for {reduction:.1f}% reduced penalty" if reduction > 0 else "Not eligible for penalty reduction"
    )

    prompt = (
        "You are a competitive positioning agent for Twenty1 Bank. "
        "Write a professional, enterprise-style summary comparing Twenty1 Bank vs traditional banks. "
        "Do not invent features beyond the provided differentiators. "
        "Return JSON matching the schema exactly.\n\n"
        f"Differentiators (authoritative): Dynamic penalty reduction, risk-based flexibility, personalized FD strategy, AI-powered advisory, smart renewal forecasting.\n"
        f"Traditional banks baseline (authoritative): fixed premature closure penalty = 1.0%.\n"
        f"Twenty1 adaptive penalty (authoritative): base_penalty_percent={penalty_percent:.2f}%, reduction={reduction:.1f}%, effective_penalty_percent={adaptive_penalty:.2f}%.\n"
        f"Customer context (authoritative): loyalty_score={loyalty_score}, risk_category={risk.risk_category}, behavior_pattern={risk.behavior_pattern}.\n"
        "Requirements:\n"
        "- twenty1_advantage_summary should be 4-7 sentences, concise and professional.\n"
    )

    try:
        llm = get_chat_llm(temperature=0.0)
        structured = llm.with_structured_output(CompetitiveAdvantage)
        out = await structured.ainvoke(prompt)
        out.loyalty_score = loyalty_score
        out.penalty_reduction_eligibility = eligibility
        return out
    except (LLMNotConfigured, LLMConnectionError):
        raise
    except Exception as e:
        raise LLMConnectionError("Competitive agent failed") from e
