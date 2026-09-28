"""Plugin configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FormBuilderPluginConfig:
    navigation_group: str = "Forms"
    bind_tenant_resolver: bool = True
    cluster: type[Any] | str | None = None
    fill_path_prefix: str = "forms"
    resources: list[type[Any]] = field(default_factory=list)
