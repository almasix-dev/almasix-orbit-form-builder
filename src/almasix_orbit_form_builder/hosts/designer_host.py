"""Conduit host for the visual form designer."""

from __future__ import annotations

import json
from typing import Any, ClassVar

from almasix.orbit.panels.conduit.hosts import OrbitPageHost
from almasix.orbit.support.html import e

from almasix_orbit_form_builder.definition import validate_definition
from almasix_orbit_form_builder.hydrate import build_form
from almasix_orbit_form_builder.models import FormDefinition
from almasix_orbit_form_builder.registry import PALETTE, all_type_names
from almasix_orbit_form_builder.store import get_form_store
from almasix_orbit_form_builder.tenant import current_tenant_id


class FormDesignerHost(OrbitPageHost):
    """Tree + inspector designer with live Orbit preview."""

    form_id: str = ""
    title: str = "Untitled form"
    slug: str = "untitled"
    status: str = "draft"
    definition_json: str = '{"components":[]}'
    settings_json: str = '{"handlers":[{"type":"store"}]}'
    preview_html: str = ""
    error: str = ""
    saved: bool = False
    message: str = ""
    _panel: ClassVar[Any] = None
    _page: ClassVar[Any] = None

    @classmethod
    def bind(cls, *, panel: Any = None, page: Any = None) -> type[FormDesignerHost]:
        class Bound(FormDesignerHost):
            pass

        Bound._panel = panel
        Bound._page = page
        panel_id = getattr(panel, "id", None) or "admin"
        Bound._conduit_name = f"orbit.{panel_id}.form-builder.designer"
        return Bound

    @classmethod
    def _public_property_names(cls) -> set[str]:
        return {
            "form_id",
            "title",
            "slug",
            "status",
            "definition_json",
            "settings_json",
            "preview_html",
            "error",
            "saved",
            "message",
        }

    def mount(self, **kwargs: Any) -> None:
        self.error = ""
        self.saved = False
        self.message = ""
        self._refresh_preview()

    def _parse_definition(self) -> dict[str, Any]:
        try:
            data = json.loads(self.definition_json or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid definition JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Definition must be a JSON object")
        return data

    def _parse_settings(self) -> dict[str, Any]:
        try:
            data = json.loads(self.settings_json or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def load_form(self, form_id: str = "") -> None:
        self.error = ""
        self.saved = False
        store = get_form_store()
        form = store.get_definition(str(form_id or self.form_id))
        if form is None:
            self.error = "Form not found."
            return
        self.form_id = form.id
        self.title = form.title
        self.slug = form.slug
        self.status = form.status
        self.definition_json = json.dumps(form.definition, indent=2)
        self.settings_json = json.dumps(form.settings, indent=2)
        self._refresh_preview()

    def new_form(self) -> None:
        self.form_id = ""
        self.title = "Untitled form"
        self.slug = "untitled"
        self.status = "draft"
        self.definition_json = json.dumps(
            {
                "components": [
                    {
                        "type": "TextInput",
                        "name": "name",
                        "label": "Name",
                        "required": True,
                    }
                ]
            },
            indent=2,
        )
        self.settings_json = json.dumps({"handlers": [{"type": "store"}]}, indent=2)
        self.error = ""
        self.saved = False
        self.message = "New draft ready."
        self._refresh_preview()

    def add_field(self, type_name: str = "TextInput") -> None:
        self.error = ""
        try:
            definition = self._parse_definition()
        except ValueError as exc:
            self.error = str(exc)
            return
        if type_name not in all_type_names():
            self.error = f"Unknown type: {type_name}"
            return
        components = list(definition.get("components") or [])
        base = type_name[0].lower() + type_name[1:]
        name = f"{base}_{len(components) + 1}"
        node: dict[str, Any] = {"type": type_name, "name": name, "label": type_name}
        if type_name in {"Section", "Grid", "Fieldset", "Group", "Flex", "Split"}:
            node["schema"] = []
            if type_name == "Section":
                node["heading"] = type_name
        components.append(node)
        definition["components"] = components
        self.definition_json = json.dumps(definition, indent=2)
        self._refresh_preview()

    def preview(self) -> None:
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        try:
            definition = self._parse_definition()
            problems = validate_definition(definition)
            if problems:
                self.preview_html = '<p class="or-danger">' + e("; ".join(problems)) + "</p>"
                return
            form = build_form(definition, name="preview")
            self.preview_html = form.render({})
            self.error = ""
        except Exception as exc:  # noqa: BLE001 — surface hydrate errors in UI
            self.preview_html = f'<p class="or-danger">{e(str(exc))}</p>'

    def save(self, publish: bool = False) -> None:
        self.error = ""
        self.saved = False
        self.message = ""
        try:
            definition = self._parse_definition()
        except ValueError as exc:
            self.error = str(exc)
            return
        problems = validate_definition(definition)
        if problems:
            self.error = "; ".join(problems)
            return
        settings = self._parse_settings()
        store = get_form_store()
        existing = store.get_definition(self.form_id) if self.form_id else None
        form = existing or FormDefinition(
            slug=self.slug or "untitled",
            title=self.title or "Untitled form",
            definition=definition,
            settings=settings,
            tenant_id=current_tenant_id(),
        )
        form.title = self.title or form.title
        form.slug = self.slug or form.slug
        form.definition = definition
        form.settings = settings
        form.status = "published" if publish else (self.status or "draft")
        if publish:
            form.status = "published"
        form.tenant_id = form.tenant_id or current_tenant_id()
        store.save_definition(form)
        self.form_id = form.id
        self.status = form.status
        self.saved = True
        self.message = "Published." if publish else "Draft saved."
        self._refresh_preview()

    def publish(self) -> None:
        self.save(publish=True)

    def render(self) -> str:
        palette_bits: list[str] = []
        for group in PALETTE:
            buttons_list: list[str] = []
            for t in group["types"]:
                click = self._attr("click", f'add_field("{t}")')
                buttons_list.append(
                    f'<button type="button" class="or-btn or-btn-sm" {click}>{e(t)}</button>'
                )
            buttons = "".join(buttons_list)
            palette_bits.append(
                f'<div class="or-fb-palette-group"><h3>{e(group["label"])}</h3>'
                f'<div class="or-fb-palette-btns">{buttons}</div></div>'
            )
        notice = ""
        if self.message:
            notice = f'<p class="or-success">{e(self.message)}</p>'
        elif self.error:
            notice = f'<p class="or-danger">{e(self.error)}</p>'
        forms = get_form_store().list_definitions()
        form_options = "".join(
            f'<option value="{e(f.id)}"{" selected" if f.id == self.form_id else ""}>'
            f"{e(f.title)} ({e(f.slug)})</option>"
            for f in forms
        )
        return f"""
<div class="or-page or-page-form-builder">
  <h1 class="or-page-title">Form builder</h1>
  {notice}
  <div class="or-fb-toolbar">
    <select class="or-input" {self._attr("model", "form_id")}>
      <option value="">— select form —</option>
      {form_options}
    </select>
    <button type="button" class="or-btn" {self._attr("click", "load_form()")}>Load</button>
    <button type="button" class="or-btn" {self._attr("click", "new_form()")}>New</button>
    <button type="button" class="or-btn or-btn-primary" {self._attr("click", "save()")}>Save draft</button>
    <button type="button" class="or-btn or-btn-primary" {self._attr("click", "publish()")}>Publish</button>
    <button type="button" class="or-btn" {self._attr("click", "preview()")}>Refresh preview</button>
  </div>
  <div class="or-fb-meta">
    <label>Title <input class="or-input" {self._attr("model", "title")} /></label>
    <label>Slug <input class="or-input" {self._attr("model", "slug")} /></label>
    <span class="or-muted">Status: {e(self.status)}</span>
  </div>
  <div class="or-fb-layout">
    <aside class="or-fb-palette">{"".join(palette_bits)}</aside>
    <section class="or-fb-editor">
      <h2>Definition</h2>
      <textarea class="or-input or-fb-json" rows="22" {self._attr("model", "definition_json")}></textarea>
      <h2>Answer handlers</h2>
      <textarea class="or-input or-fb-json" rows="8" {self._attr("model", "settings_json")}></textarea>
      <p class="or-muted">Handlers run after the submission is stored.
      Use <code>store</code>, <code>email</code>, <code>webhook</code>, or a registered <code>callable</code>.</p>
    </section>
    <section class="or-fb-preview">
      <h2>Preview</h2>
      <div class="or-fb-preview-body">{self.preview_html}</div>
    </section>
  </div>
</div>
<style>
.or-fb-layout {{ display:grid; grid-template-columns: 14rem 1fr 1fr; gap:1rem; }}
.or-fb-palette-btns {{ display:flex; flex-wrap:wrap; gap:.35rem; }}
.or-fb-toolbar, .or-fb-meta {{ display:flex; flex-wrap:wrap; gap:.5rem; margin-bottom:.75rem; align-items:center; }}
.or-fb-json {{ font-family: ui-monospace, monospace; font-size:.85rem; width:100%; }}
.or-fb-preview-body {{ border:1px solid var(--or-border, #e5e7eb); border-radius:.5rem; padding:1rem; }}
@media (max-width: 960px) {{ .or-fb-layout {{ grid-template-columns: 1fr; }} }}
</style>
"""

    def _attr(self, kind: str, value: str) -> str:
        from almasix.orbit.support.conduit_attrs import conduit_attr

        if kind == "model":
            return conduit_attr("model", value)
        if kind == "click":
            return conduit_attr("click", value)
        return ""
