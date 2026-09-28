"""Almasix provider entry for smith discovery."""

from __future__ import annotations

from typing import Any


class OrbitFormBuilderProvider:
    """Register smith commands when Almasix boots providers."""

    def register(self) -> None:
        return None

    def boot(self) -> None:
        try:
            from almasix.smith import smith
        except Exception:
            return
        from almasix_orbit_form_builder.commands import register_commands

        register_commands(smith)

    def register_commands(self, smith: Any) -> None:
        from almasix_orbit_form_builder.commands import register_commands

        register_commands(smith)
