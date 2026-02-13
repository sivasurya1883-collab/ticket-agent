from __future__ import annotations

from datetime import date
from typing import Any

from .. import calculations
from ..llm_service import LLMConnectionError, LLMNotConfigured, get_chat_llm
from .types import FDRecommendation, RiskAssessment


def _project_maturity(
    principal: float,
    annual_rate_percent: float,
    tenure_months: int,
    interest_type: str,
) -> float:
    maturity = calculations.calculate_maturity(
        principal=principal,
        annual_rate_percent=annual_rate_percent,
        tenure_months=tenure_months,
        start_date=date.today(),
        interest_type=interest_type,
    )
    return float(maturity.maturity_amount)


def _pick_rate(settings: dict[str, Any], tenure_months: int) -> float:
    rates = settings.get("default_interest_rates") or {}
    if isinstance(rates, dict):
        exact = rates.get(str(tenure_months))
        if exact is not None:
            try:
                return float(exact)
            except Exception:
                pass

        parsed: list[tuple[int, float]] = []
        for k, v in rates.items():
            try:
                parsed.append((int(k), float(v)))
            except Exception:
                continue

        if parsed:
            parsed.sort(key=lambda x: abs(x[0] - tenure_months))
            return float(parsed[0][1])

    return float(settings.get("default_interest_rate") or 7.0)


async def run_recommendation_agent(
    *,
    history_rows: list[dict[str, Any]],
    risk: RiskAssessment,
    settings: dict[str, Any],
) -> FDRecommendation:
    deposits = [float(r.get("deposit_amount") or 0) for r in history_rows]
    tenures = [int(r.get("tenure_months") or 0) for r in history_rows if r.get("tenure_months") is not None]

    avg_deposit = sum(deposits) / len(deposits) if deposits else 100000.0
    avg_tenure = int(round(sum(tenures) / len(tenures))) if tenures else 12

    base_tenure = max(6, min(60, avg_tenure or 12))
    if risk.risk_category == "High":
        suggested_months = max(6, min(24, base_tenure))
        renewal_prob = "Medium"
    elif risk.risk_category == "Moderate":
        suggested_months = max(12, min(36, base_tenure))
        renewal_prob = "High" if suggested_months >= 12 else "Medium"
    else:
        suggested_months = max(12, min(60, base_tenure + 6))
        renewal_prob = "High"

    interest_type = settings.get("interest_type") or "SIMPLE"

    rate = _pick_rate(settings, int(suggested_months))

    expected_projection = _project_maturity(
        principal=float(avg_deposit),
        annual_rate_percent=float(rate),
        tenure_months=int(suggested_months),
        interest_type=str(interest_type),
    )

    prompt = (
        "You are an FD strategy recommendation agent for a bank officer. "
        "You MUST only use the provided facts and avoid making up customer history. "
        "Return JSON that matches the schema exactly with no extra keys.\n\n"
        f"Risk Profile (authoritative): risk_score={risk.risk_score}, risk_category={risk.risk_category}, behavior_pattern={risk.behavior_pattern}.\n"
        f"History aggregates (authoritative): avg_deposit={avg_deposit:.2f}, avg_tenure_months={avg_tenure}.\n"
        f"System settings (authoritative): interest_type={settings.get('interest_type')}, penalty_percent={settings.get('penalty_percent')}.\n"
        f"Computed defaults (authoritative): suggested_months={suggested_months}, expected_maturity_projection={expected_projection:.2f}, renewal_probability={renewal_prob}.\n\n"
        "Requirements:\n"
        "- suggested_tenure must be a human readable string like '24 months'.\n"
        "- strategy should reflect interest type and a compounding cadence if applicable.\n"
        "- reasoning must be 1-2 sentences, professional and concise.\n"
    )

    try:
        llm = get_chat_llm(temperature=0.0)
        structured = llm.with_structured_output(FDRecommendation)
        rec = await structured.ainvoke(prompt)

        rec.expected_maturity_projection = float(expected_projection)
        rec.renewal_probability = renewal_prob  # type: ignore[assignment]
        if not rec.suggested_tenure:
            rec.suggested_tenure = f"{suggested_months} months"
        return rec
    except (LLMNotConfigured, LLMConnectionError):
        raise
    except Exception as e:
        raise LLMConnectionError("Recommendation agent failed") from e
