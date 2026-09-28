"""Orbit Form Builder plugin."""

from __future__ import annotations

from typing import Any, Self

from almasix.orbit.panels.hooks import Plugin

from almasix_orbit_form_builder.config import FormBuilderPluginConfig


class FormBuilderPlugin(Plugin):
    """Register form definition resources, designer, fill page, and tenant resolver."""

    def __init__(self) -> None:
        super().__init__("orbit-form-builder")
        self.config = FormBuilderPluginConfig()

    @classmethod
    def make(cls) -> FormBuilderPlugin:
        return cls()

    def navigation_group(self, name: str) -> Self:
        self.config.navigation_group = str(name)
        return self

    def cluster(self, cluster: type[Any] | str | None) -> Self:
        self.config.cluster = cluster
        return self

    def without_tenant_resolver(self) -> Self:
        self.config.bind_tenant_resolver = False
        return self

    def fill_path_prefix(self, prefix: str) -> Self:
        self.config.fill_path_prefix = str(prefix).strip("/") or "forms"
        return self

    def register(self, panel: Any) -> None:
        from almasix_orbit_form_builder.pages.designer import FormDesignerPage
        from almasix_orbit_form_builder.pages.fill import FormFillPage
        from almasix_orbit_form_builder.resources.form_resource import FormDefinitionResource
        from almasix_orbit_form_builder.resources.submission_resource import (
            FormSubmissionResource,
        )

        group = self.config.navigation_group
        FormDefinitionResource.navigation_group = group
        FormSubmissionResource.navigation_group = group
        FormDesignerPage.navigation_group = group
        FormFillPage.navigation_group = None  # hidden from nav; linked by slug
        FormFillPage.slug_prefix = self.config.fill_path_prefix

        if self.config.cluster is not None:
            FormDefinitionResource.cluster = self.config.cluster
            FormSubmissionResource.cluster = self.config.cluster

        resources = list(panel.get_resources())
        for res in (FormDefinitionResource, FormSubmissionResource):
            if res not in resources:
                resources.append(res)
        panel.resources(resources)

        pages = list(panel.get_pages())
        for page in (FormDesignerPage, FormFillPage):
            if page not in pages:
                pages.append(page)
        panel.pages(pages)

    def boot(self, panel: Any) -> None:
        if not self.config.bind_tenant_resolver:
            return
        tenancy = getattr(panel, "get_tenancy", lambda: None)()
        if tenancy is None or not getattr(tenancy, "is_enabled", lambda: False)():
            return
        from almasix_orbit_form_builder.tenant import set_tenant_resolver

        def resolve() -> Any:
            getter = getattr(panel, "get_tenant", None)
            return getter() if callable(getter) else None

        set_tenant_resolver(resolve)
