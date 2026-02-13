from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


Role = Literal["OFFICER", "SUPERVISOR"]
InterestType = Literal["SIMPLE", "COMPOUND"]
FDStatus = Literal["ACTIVE", "CLOSED"]


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: str
    email: str


class FDCreateRequest(BaseModel):
    customer_name: str
    id_type: str
    id_number: str
    deposit_amount: float = Field(gt=0)
    interest_rate: float = Field(ge=0, le=20)
    tenure_months: int = Field(gt=0)
    start_date: date


class FDResponse(BaseModel):
    id: str
    fd_number: str
    customer_name: str
    id_type: str
    id_number: str
    deposit_amount: float
    interest_rate: float
    tenure_months: int
    start_date: date
    maturity_date: date
    maturity_amount: float
    status: FDStatus
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class FDListResponse(BaseModel):
    items: list[FDResponse]


class DashboardResponse(BaseModel):
    total_active_fds: int
    total_maturity_value_active: float
    total_closed_fds: int


class SettingsResponse(BaseModel):
    id: str
    interest_type: InterestType
    penalty_percent: float
    default_interest_rates: dict[str, float] = {}
    updated_at: Optional[str] = None


class SettingsUpdateRequest(BaseModel):
    interest_type: InterestType
    penalty_percent: float = Field(ge=0, le=100)
    default_interest_rates: dict[str, float] = {}


class ClosureSimulateRequest(BaseModel):
    closure_date: date


class ClosureSimulateResponse(BaseModel):
    accrued_interest: float
    penalty: float
    penalty_percent_used: float
    net_interest: float
    payable_amount: float
    elapsed_years: float


class ExplanationRequest(BaseModel):
    fd_id: Optional[str] = None
    fd_number: Optional[str] = None
    context: Optional[str] = None


class ExplanationResponse(BaseModel):
    explanation: str


class FDCompetitorComparisonRequest(BaseModel):
    deposit_amount: float = Field(gt=0)
    interest_rate: float = Field(ge=0, le=20)
    tenure_months: int = Field(gt=0)


class CompetitorBankCard(BaseModel):
    bank: str
    fd_rate_detected: Optional[str] = None
    source_url: Optional[str] = None
    status: str
    features: list[str] = []
    min_tenure_months: Optional[int] = None
    max_tenure_years: Optional[int] = None
    premature_penalty_percent: Optional[float] = None
    senior_citizen_extra: Optional[float] = None
    security: Optional[str] = None


class FDCompetitorComparisonResponse(BaseModel):
    our_bank: dict[str, Any]
    competitors: list[CompetitorBankCard]
    why_choose_our_bank: list[str]
    best_fit_customers: list[str]
    officer_pitch: str


class RiskAssessmentResponse(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_category: Literal["Low", "Moderate", "High"]
    behavior_pattern: str
    flags: list[str]
    recommendation_to_officer: str


class FDRecommendationResponse(BaseModel):
    suggested_tenure: str
    strategy: str
    reasoning: str
    expected_maturity_projection: float
    renewal_probability: Literal["Low", "Medium", "High"]


class CompetitiveAdvantageResponse(BaseModel):
    twenty1_advantage_summary: str
    penalty_reduction_eligibility: str
    loyalty_score: int = Field(ge=0, le=100)


class CustomerAnalysisResponse(BaseModel):
    customer_id: str
    analyzed_at: str
    risk: RiskAssessmentResponse
    recommendation: FDRecommendationResponse
    competitive: CompetitiveAdvantageResponse


class CustomerAIProfileV2Response(BaseModel):
    customer_id: str
    last_risk_score: int
    last_analysis_date: str
    loyalty_score: int
    penalty_reduction_percent: float
