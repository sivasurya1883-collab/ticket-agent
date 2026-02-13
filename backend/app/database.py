from __future__ import annotations

from datetime import date
from typing import Any, Optional, Sequence, Tuple

import certifi
import httpx

from .config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_SSL_VERIFY, SUPABASE_URL


class SupabaseError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise SupabaseError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY not configured")

    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def _rest_url(path: str) -> str:
    return f"{SUPABASE_URL}/rest/v1{path}"


def _verify_setting():
    if not SUPABASE_SSL_VERIFY:
        return False
    return certifi.where()


async def sb_select(
    table: str,
    select: str = "*",
    filters: Optional[dict[str, str]] = None,
    filter_items: Optional[Sequence[Tuple[str, str]]] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    params_list: list[tuple[str, str]] = [("select", select)]
    if filters:
        params_list.extend(list(filters.items()))
    if filter_items:
        params_list.extend(list(filter_items))
    if order:
        params_list.append(("order", order))
    if limit is not None:
        params_list.append(("limit", str(limit)))

    async with httpx.AsyncClient(timeout=20.0, verify=_verify_setting()) as client:
        res = await client.get(_rest_url(f"/{table}"), headers=_headers(), params=params_list)

    if res.status_code >= 400:
        raise SupabaseError(f"Supabase select failed: {res.status_code} {res.text}")

    return res.json()


async def sb_insert(table: str, payload: dict[str, Any], returning: str = "representation") -> dict[str, Any]:
    headers = _headers() | {"Prefer": f"return={returning}"}

    async with httpx.AsyncClient(timeout=20.0, verify=_verify_setting()) as client:
        res = await client.post(_rest_url(f"/{table}"), headers=headers, json=payload)

    if res.status_code >= 400:
        raise SupabaseError(f"Supabase insert failed: {res.status_code} {res.text}")

    if returning == "minimal":
        return {}

    if not res.text:
        return {}

    data = res.json()
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    raise SupabaseError("Unexpected insert response")


async def sb_update(table: str, match: dict[str, str], payload: dict[str, Any], returning: str = "representation") -> dict[str, Any]:
    headers = _headers() | {"Prefer": f"return={returning}"}

    async with httpx.AsyncClient(timeout=20.0, verify=_verify_setting()) as client:
        res = await client.patch(_rest_url(f"/{table}"), headers=headers, params=match, json=payload)

    if res.status_code >= 400:
        raise SupabaseError(f"Supabase update failed: {res.status_code} {res.text}")

    if returning == "minimal":
        return {}

    if not res.text:
        return {}

    data = res.json()
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    raise SupabaseError("Unexpected update response")


async def sb_rpc(function_name: str, payload: dict[str, Any]) -> Any:
    headers = _headers()

    async with httpx.AsyncClient(timeout=20.0, verify=_verify_setting()) as client:
        res = await client.post(_rest_url(f"/rpc/{function_name}"), headers=headers, json=payload)

    if res.status_code >= 400:
        raise SupabaseError(f"Supabase rpc failed: {res.status_code} {res.text}")

    return res.json()


def to_iso_date(d: date) -> str:
    return d.isoformat()
