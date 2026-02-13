from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from .config import settings


TicketStatus = Literal["Open", "In Progress", "Closed"]


@dataclass
class UserRow:
    user_id: str
    username: str
    password: str
    email: str | None
    created_at: str | None


@dataclass
class TicketRow:
    ticket_id: str
    user_id: str
    ticket_title: str | None
    issue_description: str | None
    severity: str | None
    status: TicketStatus | None
    solution: str | None
    created_at: str | None
    resolved_at: str | None


def get_supabase() -> Client:
    settings.validate()
    options = SyncClientOptions(
        httpx_client=httpx.Client(verify=settings.supabase_verify_ssl)
    )
    return create_client(settings.supabase_url, settings.supabase_key, options=options)


def authenticate_user(username: str, password: str) -> UserRow | None:
    sb = get_supabase()
    res = (
        sb.table("users")
        .select("user_id, username, password, email, created_at")
        .eq("username", username)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    user = res.data[0]
    if user.get("password") != password:
        return None
    return UserRow(**user)


def get_user_by_id(user_id: str) -> UserRow | None:
    sb = get_supabase()
    res = (
        sb.table("users")
        .select("user_id, username, password, email, created_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return UserRow(**res.data[0])


def list_user_tickets(user_id: str, limit: int = 50) -> list[TicketRow]:
    sb = get_supabase()
    res = (
        sb.table("tickets")
        .select(
            "ticket_id, user_id, ticket_title, issue_description, severity, status, solution, created_at, resolved_at"
        )
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [TicketRow(**row) for row in (res.data or [])]


def list_closed_tickets_for_user(user_id: str, limit: int = 200) -> list[TicketRow]:
    sb = get_supabase()
    res = (
        sb.table("tickets")
        .select(
            "ticket_id, user_id, ticket_title, issue_description, severity, status, solution, created_at, resolved_at"
        )
        .eq("user_id", user_id)
        .eq("status", "Closed")
        .order("resolved_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [TicketRow(**row) for row in (res.data or [])]


def list_closed_tickets_other_users(user_id: str, limit: int = 400) -> list[TicketRow]:
    sb = get_supabase()
    res = (
        sb.table("tickets")
        .select(
            "ticket_id, user_id, ticket_title, issue_description, severity, status, solution, created_at, resolved_at"
        )
        .neq("user_id", user_id)
        .eq("status", "Closed")
        .order("resolved_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [TicketRow(**row) for row in (res.data or [])]


def insert_ticket(
    user_id: str,
    ticket_title: str,
    issue_description: str,
    severity: str,
    status: TicketStatus = "Open",
) -> TicketRow:
    sb = get_supabase()
    ticket_id = str(uuid4())
    sb.table("tickets").insert(
        {
            "ticket_id": ticket_id,
            "user_id": user_id,
            "ticket_title": ticket_title,
            "issue_description": issue_description,
            "severity": severity,
            "status": status,
        }
    ).execute()

    res = (
        sb.table("tickets")
        .select(
            "ticket_id, user_id, ticket_title, issue_description, severity, status, solution, created_at, resolved_at"
        )
        .eq("ticket_id", ticket_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise RuntimeError("Failed to fetch inserted ticket")
    return TicketRow(**res.data[0])


def update_ticket_solution(
    ticket_id: str,
    solution: str,
    status: TicketStatus = "Closed",
    resolved_at: datetime | None = None,
) -> TicketRow:
    sb = get_supabase()
    payload: dict[str, Any] = {
        "solution": solution,
        "status": status,
        "resolved_at": (resolved_at or datetime.utcnow()).isoformat(),
    }
    sb.table("tickets").update(payload).eq("ticket_id", ticket_id).execute()

    res = (
        sb.table("tickets")
        .select(
            "ticket_id, user_id, ticket_title, issue_description, severity, status, solution, created_at, resolved_at"
        )
        .eq("ticket_id", ticket_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise RuntimeError("Failed to fetch updated ticket")
    return TicketRow(**res.data[0])
