"""Request-local tenant for form definitions and submissions."""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

GLOBAL_TENANT_ID = ""

_current: ContextVar[str | None] = ContextVar("orbit_form_builder_tenant", default=None)
_resolver: Callable[[], Any] | None = None


def normalize_tenant_id(tenant: Any) -> str:
    if tenant is None or tenant is False:
        return GLOBAL_TENANT_ID
    if isinstance(tenant, str):
        return tenant.strip()
    for attr in ("id", "slug", "key"):
        value = getattr(tenant, attr, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    text = str(tenant).strip()
    return text if text and text != "None" else GLOBAL_TENANT_ID


def set_tenant_resolver(resolver: Callable[[], Any] | None) -> None:
    global _resolver
    _resolver = resolver


def set_current_tenant(tenant: Any) -> None:
    _current.set(normalize_tenant_id(tenant))


def clear_current_tenant() -> None:
    _current.set(None)


def current_tenant_id(*, scoped: bool = True) -> str:
    if not scoped:
        return GLOBAL_TENANT_ID
    explicit = _current.get()
    if explicit is not None:
        return explicit
    if _resolver is not None:
        return normalize_tenant_id(_resolver())
    return GLOBAL_TENANT_ID
