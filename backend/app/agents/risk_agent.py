from __future__ import annotations

import statistics
from typing import Any

from ..llm_service import LLMConnectionError, LLMNotConfigured, get_chat_llm
from .types import CustomerFDHistoryItem, RiskAssessment


def _basic_features(history: list[CustomerFDHistoryItem]) -> dict[str, Any]:
    deposits = [float(h.deposit_amount) for h in history]
    tenures = [int(h.tenure_months) for h in history]

    avg_deposit = statistics.mean(deposits) if deposits else 0.0
    avg_tenure = statistics.mean(tenures) if tenures else 0.0

    premature_closures = 0
    for h in history:
        if (h.status or "").upper() == "CLOSED":
            if h.closed_at and h.maturity_date and h.closed_at < h.maturity_date:
                premature_closures += 1

    high_value_anomalies = 0
    for d in deposits:
        if avg_deposit > 0 and d > 2 * avg_deposit:
            high_value_anomalies += 1

    tenure_std = 0.0
    if len(tenures) >= 2:
        try:
            tenure_std = float(statistics.pstdev(tenures))
        except statistics.StatisticsError:
            tenure_std = 0.0

    return {
        "fd_count": len(history),
        "avg_deposit": float(avg_deposit),
        "avg_tenure_months": float(avg_tenure),
        "premature_closure_count": premature_closures,
        "high_value_anomaly_count": high_value_anomalies,
        "tenure_std_months": tenure_std,
    }


async def run_risk_agent(history_rows: list[dict[str, Any]]) -> RiskAssessment:
    history = [CustomerFDHistoryItem(**r) for r in history_rows]
    feats = _basic_features(history)

    prompt = (
        "You are a bank risk analysis agent. You MUST only use the numeric features provided. "
        "Return a JSON object that matches the schema exactly. Do not include any extra keys.\n\n"
        "Features (authoritative):\n"
        f"- fd_count: {feats['fd_count']}\n"
        f"- avg_deposit: {feats['avg_deposit']:.2f}\n"
        f"- avg_tenure_months: {feats['avg_tenure_months']:.2f}\n"
        f"- premature_closure_count: {feats['premature_closure_count']}\n"
        f"- high_value_anomaly_count: {feats['high_value_anomaly_count']}\n"
        f"- tenure_std_months: {feats['tenure_std_months']:.2f}\n\n"
        "Rules:\n"
        "- risk_score is 0..100, higher means more risk/instability.\n"
        "- risk_category is Low/Moderate/High.\n"
        "- flags should be short strings derived from counts (e.g., 'Frequent premature closure').\n"
        "- behavior_pattern should be one of: Conservative investor, Short-term churner, Long-term loyal, Short-term rollover investor, Mixed behavior.\n"
        "- recommendation_to_officer should be a single actionable sentence.\n"
    )

    try:
        llm = get_chat_llm(temperature=0.0)
        structured = llm.with_structured_output(RiskAssessment)
        return await structured.ainvoke(prompt)
    except (LLMNotConfigured, LLMConnectionError):
        raise
    except Exception as e:
        raise LLMConnectionError("Risk agent failed") from e
