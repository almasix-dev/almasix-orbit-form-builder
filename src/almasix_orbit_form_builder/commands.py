"""Smith commands for Orbit Form Builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_STUB = '''\
"""Dynamic form fill helper (generated)."""

from almasix_orbit_form_builder import FormBuilderPlugin

# Register on your panel:
# panel.plugin(FormBuilderPlugin.make().navigation_group("Forms"))
'''


def register_commands(smith: Any) -> None:
    @smith.command("make:orbit-form")
    def make_orbit_form(name: str = "contact", panel: str = "app") -> None:
        """Stub a reminder file for wiring Orbit Form Builder on a panel."""
        root = Path("app") / "orbit" / panel
        root.mkdir(parents=True, exist_ok=True)
        target = root / f"{name}_form_builder.py"
        if not target.exists():
            target.write_text(_STUB)
            print(f"Created {target}")
        else:
            print(f"Exists {target}")
