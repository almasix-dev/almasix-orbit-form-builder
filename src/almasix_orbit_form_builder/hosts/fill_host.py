"""Conduit host that renders a published form and accepts answers."""

from __future__ import annotations

from typing import Any, ClassVar

from almasix.orbit.panels.conduit.hosts import FormDataMutations, OrbitPageHost
from almasix.orbit.support.conduit_attrs import conduit_attr
from almasix.orbit.support.html import e

from almasix_orbit_form_builder.handlers import dispatch_handlers
from almasix_orbit_form_builder.hydrate import build_form
from almasix_orbit_form_builder.models import FormSubmission
from almasix_orbit_form_builder.store import get_form_store
from almasix_orbit_form_builder.tenant import current_tenant_id


class FormFillHost(FormDataMutations, OrbitPageHost):
    """Fill and submit a published dynamic form."""

    data: dict[str, Any] = {}
    select_search: dict[str, str] = {}
    morph_search: dict[str, str] = {}
    table_select: dict[str, Any] = {}
    form_slug: str = ""
    error: str = ""
    success: str = ""
    _panel: ClassVar[Any] = None
    _page: ClassVar[Any] = None
    _form_def: ClassVar[Any] = None

    @classmethod
    def bind(cls, *, panel: Any = None, page: Any = None) -> type[FormFillHost]:
        class Bound(FormFillHost):
            pass

        Bound._panel = panel
        Bound._page = page
        panel_id = getattr(panel, "id", None) or "admin"
        Bound._conduit_name = f"orbit.{panel_id}.form-builder.fill"
        return Bound

    @classmethod
    def _public_property_names(cls) -> set[str]:
        return {
            "data",
            "form_slug",
            "error",
            "success",
            "select_search",
            "morph_search",
            "table_select",
        }

    def get_panel(self) -> Any:
        return type(self)._panel

    def get_form(self) -> Any:
        form_def = self._loaded()
        if form_def is None:
            return None
        return build_form(form_def.definition, name=form_def.slug)

    def _loaded(self) -> Any:
        store = get_form_store()
        form = store.get_definition_by_slug(self.form_slug) if self.form_slug else None
        if form is not None and form.status != "published":
            return None
        return form

    def mount(self, **kwargs: Any) -> None:
        self.error = ""
        self.success = ""
        if not self.form_slug:
            self.form_slug = str(kwargs.get("form_slug") or kwargs.get("slug") or "")
        form = self._loaded()
        self.data = {}
        if form is None and self.form_slug:
            self.error = "This form is not available."

    def load(self, slug: str = "") -> None:
        self.form_slug = str(slug or self.form_slug)
        self.error = ""
        self.success = ""
        self.data = {}
        if self._loaded() is None:
            self.error = "This form is not available."

    def submit(self) -> None:
        self.reset_skip_render()
        self.error = ""
        self.success = ""
        form_def = self._loaded()
        if form_def is None:
            self.error = "This form is not available."
            return
        form = build_form(form_def.definition, name=form_def.slug)
        errors = form.validate(dict(self.data))
        if errors:
            self.error = "Please fix the highlighted fields."
            self._form_errors = errors  # type: ignore[attr-defined]
            return
        submission = FormSubmission(
            form_id=form_def.id,
            payload=dict(self.data),
            meta={"slug": form_def.slug},
            tenant_id=current_tenant_id(),
        )
        get_form_store().save_submission(submission)
        dispatch_handlers(form_def, submission)
        message = str(
            (form_def.settings or {}).get("success_message")
            or "Thank you — your response was saved."
        )
        self.success = message
        self.data = {}

    def render(self) -> str:
        form_def = self._loaded()
        title = e(form_def.title if form_def else "Form")
        if self.error and form_def is None:
            return (
                f'<div class="or-page or-page-form-fill"><h1 class="or-page-title">{title}</h1>'
                f'<p class="or-danger">{e(self.error)}</p>'
                f'<label>Form slug <input class="or-input" {conduit_attr("model", "form_slug")} /></label> '
                f'<button type="button" class="or-btn" {conduit_attr("click", "load()")}>Open</button>'
                f"</div>"
            )
        notice = ""
        if self.success:
            notice = f'<p class="or-success">{e(self.success)}</p>'
        elif self.error:
            notice = f'<p class="or-danger">{e(self.error)}</p>'
        form = self.get_form()
        body = form.render(self.data, form_errors=getattr(self, "_form_errors", {})) if form else ""
        return f"""
<div class="or-page or-page-form-fill">
  <h1 class="or-page-title">{title}</h1>
  {notice}
  <form {conduit_attr("submit", "submit")}>
    {body}
    <div class="or-form-actions">
      <button type="submit" class="or-btn or-btn-primary">Submit</button>
    </div>
  </form>
</div>
"""
