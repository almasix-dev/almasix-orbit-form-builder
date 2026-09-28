"""Custom pages for the form builder."""

from __future__ import annotations

from typing import Any, ClassVar

from almasix.orbit.panels.page import Page

from almasix_orbit_form_builder.hosts.designer_host import FormDesignerHost


class FormDesignerPage(Page):
    slug = "form-builder"
    title = "Form builder"
    navigation_label = "Form builder"
    navigation_icon = "heroicon-o-puzzle-piece"
    navigation_group: ClassVar[str | None] = "Forms"
    navigation_sort = 10

    @classmethod
    def get_conduit_host(cls) -> type[Any] | None:
        return FormDesignerHost

    @classmethod
    def render(cls, **ctx: Any) -> str:
        return '<div class="or-page">Form builder requires Conduit.</div>'
