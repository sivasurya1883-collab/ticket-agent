from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


RiskCategory = Literal["Low", "Moderate", "High"]


class RiskAssessment(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_category: RiskCategory
    behavior_pattern: str
    flags: list[str]
    recommendation_to_officer: str


class FDRecommendation(BaseModel):
    suggested_tenure: str
    strategy: str
    reasoning: str
    expected_maturity_projection: float
    renewal_probability: Literal["Low", "Medium", "High"]


class CompetitiveAdvantage(BaseModel):
    twenty1_advantage_summary: str
    penalty_reduction_eligibility: str
    loyalty_score: int = Field(ge=0, le=100)


class CustomerAnalysisResult(BaseModel):
    customer_id: str
    analyzed_at: datetime
    risk: RiskAssessment
    recommendation: FDRecommendation
    competitive: CompetitiveAdvantage


class CustomerFDHistoryItem(BaseModel):
    id: str
    fd_number: str
    customer_name: str
    id_number: str
    deposit_amount: float
    interest_rate: float
    tenure_months: int
    start_date: str
    maturity_date: str
    status: str
    maturity_amount: float
    closed_at: Optional[str] = None
