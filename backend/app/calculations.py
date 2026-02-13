from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MaturityResult:
    maturity_date: date
    maturity_amount: float


def add_months(start: date, months: int) -> date:
    # add months without external deps
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    # clamp day to end of month
    import calendar

    last_day = calendar.monthrange(year, month)[1]
    day = min(start.day, last_day)
    return date(year, month, day)


def calculate_maturity_amount(principal: float, annual_rate_percent: float, tenure_months: int, interest_type: str) -> float:
    years = tenure_months / 12.0
    r = annual_rate_percent / 100.0

    if interest_type == "SIMPLE":
        return float(principal * (1.0 + r * years))

    # COMPOUND annual
    return float(principal * ((1.0 + r) ** years))


def calculate_maturity(principal: float, annual_rate_percent: float, tenure_months: int, start_date: date, interest_type: str) -> MaturityResult:
    maturity_date = add_months(start_date, tenure_months)
    maturity_amount = calculate_maturity_amount(
        principal=principal,
        annual_rate_percent=annual_rate_percent,
        tenure_months=tenure_months,
        interest_type=interest_type,
    )
    return MaturityResult(maturity_date=maturity_date, maturity_amount=maturity_amount)


def years_between(start: date, end: date) -> float:
    # approximate year fraction by days/365
    delta_days = (end - start).days
    return max(0.0, delta_days / 365.0)


def simulate_premature_closure(
    principal: float,
    annual_rate_percent: float,
    start_date: date,
    closure_date: date,
    interest_type: str,
    penalty_percent: float,
) -> tuple[float, float, float, float, float]:
    elapsed_years = years_between(start_date, closure_date)
    r = annual_rate_percent / 100.0

    if interest_type == "SIMPLE":
        accrued_interest = principal * r * elapsed_years
    else:
        accrued_interest = principal * ((1.0 + r) ** elapsed_years - 1.0)

    penalty = accrued_interest * (penalty_percent / 100.0)
    net_interest = max(0.0, accrued_interest - penalty)
    payable_amount = principal + net_interest

    return (
        float(accrued_interest),
        float(penalty),
        float(net_interest),
        float(payable_amount),
        float(elapsed_years),
    )
