"""Published form fill page."""

from __future__ import annotations

from typing import Any, ClassVar

from almasix.orbit.panels.page import Page

from almasix_orbit_form_builder.hosts.fill_host import FormFillHost


class FormFillPage(Page):
    slug = "forms/fill"
    title = "Fill form"
    navigation_label = None
    should_register_navigation: ClassVar[bool] = False
    slug_prefix: ClassVar[str] = "forms"

    @classmethod
    def get_conduit_host(cls) -> type[Any] | None:
        return FormFillHost

    @classmethod
    def render(cls, **ctx: Any) -> str:
        return '<div class="or-page">Form fill requires Conduit.</div>'
