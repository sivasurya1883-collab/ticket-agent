from __future__ import annotations

import json
from datetime import date
from typing import Any, Optional
from uuid import UUID

import certifi
import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import calculations
from .auth import create_access_token, require_role
from .config import CORS_ORIGINS
from .database import SupabaseError, sb_insert, sb_rpc, sb_select, sb_update
from .llm_service import LLMConnectionError, LLMNotConfigured, generate_fd_explanation, get_chat_llm
from .agents.orchestrator import analyze_customer
from .schemas import (
    ClosureSimulateRequest,
    ClosureSimulateResponse,
    CustomerAnalysisResponse,
    CustomerAIProfileV2Response,
    DashboardResponse,
    ExplanationRequest,
    ExplanationResponse,
    FDCompetitorComparisonRequest,
    FDCompetitorComparisonResponse,
    CompetitorBankCard,
    FDCreateRequest,
    FDListResponse,
    FDResponse,
    LoginRequest,
    LoginResponse,
    SettingsResponse,
    SettingsUpdateRequest,
)

app = FastAPI(title="FD Management API", version="1.0.0")


COMPETITOR_SOURCES: list[dict[str, str]] = [
    {"bank": "SBI", "url": "https://sbi.co.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits"},
    {"bank": "HDFC Bank", "url": "https://www.hdfcbank.com/personal/resources/rates"},
    {"bank": "ICICI Bank", "url": "https://www.icicibank.com/personal-banking/deposits/fixed-deposit"},
    {"bank": "Axis Bank", "url": "https://www.axisbank.com/interest-rate-on-deposits"},
    {"bank": "Punjab National Bank", "url": "https://www.pnbindia.in/Interest-Rates-Deposit.html"},
]


COMPETITOR_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "SBI": {
        "min_tenure_months": 7,
        "max_tenure_years": 10,
        "premature_penalty_percent": 1.0,
        "senior_citizen_extra": 0.5,
        "security": "DICGC insured",
        "features": ["Loan against FD", "Auto renewal"],
    },
    "HDFC Bank": {
        "min_tenure_months": 7,
        "max_tenure_years": 10,
        "premature_penalty_percent": 1.0,
        "senior_citizen_extra": 0.5,
        "security": "DICGC insured",
        "features": ["Sweep-in facility", "Digital FD"],
    },
    "ICICI Bank": {
        "min_tenure_months": 7,
        "max_tenure_years": 10,
        "premature_penalty_percent": 1.0,
        "senior_citizen_extra": 0.5,
        "security": "DICGC insured",
        "features": ["FD against overdraft", "Online management"],
    },
    "Axis Bank": {
        "min_tenure_months": 7,
        "max_tenure_years": 10,
        "premature_penalty_percent": 1.0,
        "senior_citizen_extra": 0.5,
        "security": "DICGC insured",
        "features": ["Express FD", "Auto renewal"],
    },
    "Punjab National Bank": {
        "min_tenure_months": 7,
        "max_tenure_years": 10,
        "premature_penalty_percent": 1.0,
        "senior_citizen_extra": 0.5,
        "security": "DICGC insured",
        "features": ["Tax saver FD", "Loan facility"],
    },
}


async def _fetch_competitor_rates() -> list[dict[str, Any]]:
    headers = {"User-Agent": "Mozilla/5.0"}
    timeout = httpx.Timeout(timeout=15.0)
    verify = certifi.where()

    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True, verify=verify) as client:
        out: list[dict[str, Any]] = []
        for src in COMPETITOR_SOURCES:
            bank_name = src["bank"]
            url = src["url"]
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                text = (resp.text or "").lower()

                detected = None
                for rate in ["6.5", "6.75", "7.0", "7.25", "7.5", "7.6", "7.7", "7.8", "8.0"]:
                    if rate in text:
                        detected = rate
                        break

                out.append({"bank": bank_name, "fd_rate_detected": detected, "source_url": url, "status": "success"})
            except Exception as e:
                out.append({"bank": bank_name, "fd_rate_detected": None, "source_url": url, "status": f"failed: {str(e)}"})
        return out


def _build_our_bank_data(*, settings: dict[str, Any], payload: FDCompetitorComparisonRequest) -> dict[str, Any]:
    rates = settings.get("default_interest_rates") or {}
    default_rate = None
    if isinstance(rates, dict):
        default_rate = rates.get(str(payload.tenure_months))

    return {
        "bank": "Our Bank",
        "selected_fd": {
            "deposit_amount": float(payload.deposit_amount),
            "interest_rate": float(payload.interest_rate),
            "tenure_months": int(payload.tenure_months),
        },
        "default_rate_by_tenure": default_rate,
        "premature_penalty_percent": float(settings.get("penalty_percent") or 0),
        "interest_type": settings.get("interest_type"),
        "security": "DICGC insured",
        "features": ["Digital FD booking", "Auto renewal", "Easy premature closure"],
    }


@app.post("/fd-competitor-comparison", response_model=FDCompetitorComparisonResponse)
async def fd_competitor_comparison(
    payload: FDCompetitorComparisonRequest,
    user: dict = Depends(require_role("OFFICER", "SUPERVISOR")),
):
    settings = await get_settings()
    our_bank = _build_our_bank_data(settings=settings, payload=payload)

    competitors_live = await _fetch_competitor_rates()
    enriched: list[dict[str, Any]] = []
    for row in competitors_live:
        name = row.get("bank")
        static_info = COMPETITOR_KNOWLEDGE.get(str(name), {})
        enriched.append({**row, **static_info})

    prompt = (
        "You are a senior banking business analyst helping a branch officer compare FD offerings. "
        "Return STRICT JSON only (no markdown, no extra text).\n\n"
        "JSON schema:\n"
        "{\n"
        '  "why_choose_our_bank": ["..."],\n'
        '  "best_fit_customers": ["..."],\n'
        '  "officer_pitch": "..."\n'
        "}\n\n"
        "Rules:\n"
        "- Keep it short and officer-friendly.\n"
        "- If competitors have higher rates, highlight our strengths: security, penalty flexibility, digital experience.\n"
        "- Do not invent competitor data beyond what is provided.\n\n"
        f"OUR BANK DATA (authoritative):\n{json.dumps(our_bank, ensure_ascii=False)}\n\n"
        f"COMPETITOR DATA (authoritative):\n{json.dumps(enriched, ensure_ascii=False)}\n"
    )

    try:
        llm = get_chat_llm(temperature=0.0)
        try:
            resp = await llm.ainvoke(prompt)
        finally:
            http_client = getattr(llm, "http_async_client", None)
            if http_client is not None:
                try:
                    await http_client.aclose()
                except Exception:
                    pass

        raw = str(resp.content or "").strip()
        competitors_cards = [CompetitorBankCard(**c) for c in enriched]

        try:
            parsed = json.loads(raw)
            return FDCompetitorComparisonResponse(
                our_bank=our_bank,
                competitors=competitors_cards,
                why_choose_our_bank=list(parsed.get("why_choose_our_bank") or []),
                best_fit_customers=list(parsed.get("best_fit_customers") or []),
                officer_pitch=str(parsed.get("officer_pitch") or ""),
            )
        except Exception:
            snippet = raw[:280].replace("\n", " ")
            return FDCompetitorComparisonResponse(
                our_bank=our_bank,
                competitors=competitors_cards,
                why_choose_our_bank=[
                    "LLM response could not be parsed as JSON. Showing competitor cards only.",
                    f"LLM raw (truncated): {snippet}",
                ],
                best_fit_customers=[],
                officer_pitch="",
            )
    except (LLMNotConfigured, LLMConnectionError) as e:
        competitors_cards = [CompetitorBankCard(**c) for c in enriched]
        return FDCompetitorComparisonResponse(
            our_bank=our_bank,
            competitors=competitors_cards,
            why_choose_our_bank=["LLM is not available. Showing competitor cards only."],
            best_fit_customers=[],
            officer_pitch="",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)


async def get_settings() -> dict:
    rows = await sb_select("system_settings", select="*", order="updated_at.desc", limit=1)
    if not rows:
        raise HTTPException(status_code=500, detail="System settings not initialized")
    return rows[0]


async def resolve_customer_uuid(customer_ref: str) -> str:
    try:
        UUID(customer_ref)
        return customer_ref
    except Exception:
        pass

    try:
        rows = await sb_select(
            "customers",
            select="id,customer_code,id_number",
            filters={"or": f"(customer_code.eq.{customer_ref},id_number.eq.{customer_ref})"},
            limit=1,
        )
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not rows:
        raise HTTPException(status_code=404, detail="Customer not found")

    return rows[0]["id"]


@app.get("/customer-ai-profile-v2/{customer_id}", response_model=CustomerAIProfileV2Response)
async def read_customer_ai_profile_v2(
    customer_id: str,
    user: dict = Depends(require_role("OFFICER", "SUPERVISOR")),
):
    resolved_uuid = await resolve_customer_uuid(customer_id)

    try:
        rows = await sb_select(
            "customer_ai_profiles_v2",
            select="*",
            filters={"customer_id": f"eq.{resolved_uuid}"},
            limit=1,
        )
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not rows:
        raise HTTPException(status_code=404, detail="No stored analysis found for this customer")

    r = rows[0]
    return CustomerAIProfileV2Response(
        customer_id=customer_id,
        last_risk_score=int(r.get("last_risk_score") or 0),
        last_analysis_date=str(r.get("last_analysis_date") or ""),
        loyalty_score=int(r.get("loyalty_score") or 0),
        penalty_reduction_percent=float(r.get("penalty_reduction_percent") or 0.0),
    )


@app.get("/settings", response_model=SettingsResponse)
async def read_settings(user: dict = Depends(require_role("OFFICER", "SUPERVISOR"))):
    settings = await get_settings()
    return SettingsResponse(**settings)


@app.get("/dashboard", response_model=DashboardResponse)
async def read_dashboard(user: dict = Depends(require_role("OFFICER", "SUPERVISOR"))):
    try:
        active = await sb_select("fixed_deposits", select="maturity_amount", filters={"status": "eq.ACTIVE"})
        closed = await sb_select("fixed_deposits", select="id", filters={"status": "eq.CLOSED"})
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    total_maturity = 0.0
    for r in active:
        try:
            total_maturity += float(r.get("maturity_amount") or 0)
        except (TypeError, ValueError):
            total_maturity += 0.0

    return DashboardResponse(
        total_active_fds=len(active),
        total_maturity_value_active=float(total_maturity),
        total_closed_fds=len(closed),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    try:
        rows = await sb_rpc("authenticate_user", {"p_email": payload.email, "p_password": payload.password})
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not rows:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = rows[0]

    token = create_access_token(user_id=user["id"], email=user["email"], role=user["role"])
    return LoginResponse(access_token=token, role=user["role"], user_id=user["id"], email=user["email"])


@app.post("/create-fd", response_model=FDResponse)
async def create_fd(
    payload: FDCreateRequest,
    user: dict = Depends(require_role("OFFICER", "SUPERVISOR")),
):
    settings = await get_settings()

    maturity = calculations.calculate_maturity(
        principal=payload.deposit_amount,
        annual_rate_percent=payload.interest_rate,
        tenure_months=payload.tenure_months,
        start_date=payload.start_date,
        interest_type=settings["interest_type"],
    )

    year = payload.start_date.year
    existing = await sb_select("fixed_deposits", select="id", filters={"fd_number": f"like.FD-{year}-%"})
    seq = len(existing) + 1
    fd_number = f"FD-{year}-{seq:04d}"

    record = {
        "fd_number": fd_number,
        "customer_name": payload.customer_name,
        "id_type": payload.id_type,
        "id_number": payload.id_number,
        "deposit_amount": payload.deposit_amount,
        "interest_rate": payload.interest_rate,
        "tenure_months": payload.tenure_months,
        "start_date": payload.start_date.isoformat(),
        "maturity_date": maturity.maturity_date.isoformat(),
        "maturity_amount": maturity.maturity_amount,
        "status": "ACTIVE",
        "created_by": user["user_id"],
    }

    try:
        row = await sb_insert("fixed_deposits", record)
        return FDResponse(**row)
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/fds", response_model=FDListResponse)
async def list_fds(
    status: Optional[str] = Query(default=None),
    customer_name: Optional[str] = Query(default=None),
    start_from: Optional[date] = Query(default=None),
    start_to: Optional[date] = Query(default=None),
    user: dict = Depends(require_role("OFFICER", "SUPERVISOR")),
):
    filters: dict[str, str] = {}
    filter_items: list[tuple[str, str]] = []
    if status:
        filters["status"] = f"eq.{status}"
    if customer_name:
        filters["customer_name"] = f"ilike.%{customer_name}%"
    if start_from:
        filter_items.append(("start_date", f"gte.{start_from.isoformat()}"))
    if start_to:
        filter_items.append(("start_date", f"lte.{start_to.isoformat()}"))

    try:
        rows = await sb_select("fixed_deposits", select="*", filters=filters, filter_items=filter_items, order="created_at.desc")
        return FDListResponse(items=[FDResponse(**r) for r in rows])
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/simulate-closure/{fd_id}", response_model=ClosureSimulateResponse)
async def simulate_closure(
    fd_id: str,
    payload: ClosureSimulateRequest,
    user: dict = Depends(require_role("OFFICER", "SUPERVISOR")),
):
    settings = await get_settings()

    try:
        rows = await sb_select("fixed_deposits", select="*", filters={"id": f"eq.{fd_id}"}, limit=1)
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not rows:
        raise HTTPException(status_code=404, detail="FD not found")

    fd = rows[0]
    if fd["status"] == "CLOSED":
        raise HTTPException(status_code=400, detail="FD already closed")

    penalty_percent_used = float(settings["penalty_percent"])
    accrued_interest, penalty, net_interest, payable_amount, elapsed_years = calculations.simulate_premature_closure(
        principal=float(fd["deposit_amount"]),
        annual_rate_percent=float(fd["interest_rate"]),
        start_date=date.fromisoformat(fd["start_date"]),
        closure_date=payload.closure_date,
        interest_type=settings["interest_type"],
        penalty_percent=penalty_percent_used,
    )

    return ClosureSimulateResponse(
        accrued_interest=accrued_interest,
        penalty=penalty,
        penalty_percent_used=penalty_percent_used,
        net_interest=net_interest,
        payable_amount=payable_amount,
        elapsed_years=elapsed_years,
    )


@app.post("/confirm-closure/{fd_id}", response_model=FDResponse)
async def confirm_closure(
    fd_id: str,
    payload: ClosureSimulateRequest,
    user: dict = Depends(require_role("OFFICER", "SUPERVISOR")),
):
    try:
        rows = await sb_select("fixed_deposits", select="*", filters={"id": f"eq.{fd_id}"}, limit=1)
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not rows:
        raise HTTPException(status_code=404, detail="FD not found")

    fd = rows[0]
    if fd["status"] == "CLOSED":
        raise HTTPException(status_code=400, detail="FD already closed")

    try:
        updated = await sb_update(
            "fixed_deposits",
            match={"id": f"eq.{fd_id}"},
            payload={"status": "CLOSED", "closed_at": payload.closure_date.isoformat()},
        )
        return FDResponse(**updated)
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/analyze-customer/{customer_id}", response_model=CustomerAnalysisResponse)
async def analyze_customer_endpoint(
    customer_id: str,
    user: dict = Depends(require_role("OFFICER", "SUPERVISOR")),
):
    settings = await get_settings()

    customer_ref = customer_id
    resolved_customer_uuid = await resolve_customer_uuid(customer_ref)

    try:
        result = await analyze_customer(customer_id=resolved_customer_uuid, settings=settings)
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except LLMNotConfigured as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except LLMConnectionError as e:
        raise HTTPException(
            status_code=502,
            detail="LLM service is unreachable from this machine/network. Disable it with LLM_ENABLED=false or set LLM_SSL_VERIFY=false if using a corporate TLS proxy.",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Customer analysis failed") from e

    penalty_reduction_percent = 0.0
    try:
        text = result.competitive.penalty_reduction_eligibility
        if isinstance(text, str) and "%" in text:
            maybe = text.split("Eligible for", 1)[-1].split("%", 1)[0].strip()
            penalty_reduction_percent = float(maybe)
    except Exception:
        penalty_reduction_percent = 0.0

    try:
        await sb_update(
            "customer_ai_profiles",
            match={"customer_id": f"eq.{resolved_customer_uuid}"},
            payload={
                "customer_id": resolved_customer_uuid,
                "last_risk_score": int(result.risk.risk_score),
                "last_analysis_date": result.analyzed_at.isoformat(),
                "loyalty_score": int(result.competitive.loyalty_score),
                "penalty_reduction_percent": float(penalty_reduction_percent),
            },
            returning="minimal",
        )
    except SupabaseError:
        try:
            await sb_insert(
                "customer_ai_profiles",
                {
                    "customer_id": resolved_customer_uuid,
                    "last_risk_score": int(result.risk.risk_score),
                    "last_analysis_date": result.analyzed_at.isoformat(),
                    "loyalty_score": int(result.competitive.loyalty_score),
                    "penalty_reduction_percent": float(penalty_reduction_percent),
                },
                returning="minimal",
            )
        except Exception:
            pass
    except Exception:
        pass

    return CustomerAnalysisResponse(
        customer_id=customer_ref,
        analyzed_at=result.analyzed_at.isoformat(),
        risk=result.risk.model_dump(),
        recommendation=result.recommendation.model_dump(),
        competitive=result.competitive.model_dump(),
    )


@app.put("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdateRequest,
    user: dict = Depends(require_role("SUPERVISOR")),
):
    settings = await get_settings()

    try:
        updated = await sb_update(
            "system_settings",
            match={"id": f"eq.{settings['id']}"},
            payload={
                "interest_type": payload.interest_type,
                "penalty_percent": payload.penalty_percent,
                "default_interest_rates": payload.default_interest_rates,
            },
        )
        return SettingsResponse(**updated)
    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/generate-explanation", response_model=ExplanationResponse)
async def explanation(
    payload: ExplanationRequest,
    user: dict = Depends(require_role("OFFICER", "SUPERVISOR")),
):
    prompt = (
        "You are an assistant for a bank FD module. "
        "Explain FD maturity / closure impact in simple customer-friendly language. "
        "Be concise, avoid jargon, and show key numbers when present. "
        "Output MUST be plain text only: no markdown, no headings, no bullet points, no special formatting characters (like #, *, backticks), and no math blocks. "
        "Use short paragraphs.\n\n"
        f"Context: {payload.context or ''}"
    )

    try:
        text = await generate_fd_explanation(prompt)
        return ExplanationResponse(explanation=text)
    except LLMNotConfigured as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except LLMConnectionError as e:
        raise HTTPException(
            status_code=502,
            detail="LLM service is unreachable from this machine/network. Disable it with LLM_ENABLED=false or set LLM_SSL_VERIFY=false if using a corporate TLS proxy.",
        ) from e
