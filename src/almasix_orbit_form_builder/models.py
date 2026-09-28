"""Form definition and submission records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from almasix_orbit_form_builder.tenant import GLOBAL_TENANT_ID


def _now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid4().hex


@dataclass
class FormDefinition:
    slug: str
    title: str
    definition: dict[str, Any]
    settings: dict[str, Any] = field(default_factory=dict)
    status: str = "draft"  # draft | published
    tenant_id: str = GLOBAL_TENANT_ID
    id: str = field(default_factory=new_id)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "status": self.status,
            "definition": dict(self.definition),
            "settings": dict(self.settings),
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class FormSubmission:
    form_id: str
    payload: dict[str, Any]
    meta: dict[str, Any] = field(default_factory=dict)
    tenant_id: str = GLOBAL_TENANT_ID
    id: str = field(default_factory=new_id)
    created_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "form_id": self.form_id,
            "payload": dict(self.payload),
            "meta": dict(self.meta),
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
        }
