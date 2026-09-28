"""Conduit host for the visual form designer (canvas + modals + drag-drop)."""

from __future__ import annotations

import json
from typing import Any, ClassVar

from almasix.orbit.panels.conduit.hosts import FormDataMutations, OrbitPageHost
from almasix.orbit.support.html import e

from almasix_orbit_form_builder.definition import validate_definition
from almasix_orbit_form_builder.hosts.canvas_render import render_canvas
from almasix_orbit_form_builder.hydrate import build_form
from almasix_orbit_form_builder.models import FormDefinition
from almasix_orbit_form_builder.propspec import coerce_value, display_value, props_for
from almasix_orbit_form_builder.registry import (
    PALETTE,
    all_type_names,
)
from almasix_orbit_form_builder.store import get_form_store
from almasix_orbit_form_builder.tenant import current_tenant_id
from almasix_orbit_form_builder.tree import (
    default_node,
    delete_node,
    empty_definition,
    ensure_definition,
    get_node,
    insert_node,
    move_node,
    resolve_insert_list_path,
    update_node,
    walk_tree,
)


class _DesignerPublic(set[str]):
    """Accept ``data.*`` and ``props.*`` bindings in addition to named fields."""

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str) and (
            item in {"data", "props"} or item.startswith("data.") or item.startswith("props.")
        ):
            return True
        return super().__contains__(item)


class FormDesignerHost(FormDataMutations, OrbitPageHost):
    """Visual canvas designer with property / preview modals and Sortable DnD."""

    form_id: str = ""
    loaded_form_id: str = ""
    title: str = "Untitled form"
    slug: str = "untitled"
    status: str = "draft"
    form_columns: str = "2"
    definition_json: str = '{"components":[],"columns":2}'
    settings_json: str = '{"handlers":[{"type":"store"}]}'
    selected_path: str = ""
    palette_filter: str = ""
    palette_group: str = "all"
    inspector_open: bool = False
    preview_open: bool = False
    json_open: bool = False
    handlers_open: bool = False
    # Inspector fields
    insp_label: str = ""
    insp_name: str = ""
    insp_placeholder: str = ""
    insp_helper_text: str = ""
    insp_hint: str = ""
    insp_default: str = ""
    insp_required: bool = False
    insp_readonly: bool = False
    insp_disabled: bool = False
    insp_hidden: bool = False
    insp_heading: str = ""
    insp_description: str = ""
    insp_columns: str = ""
    insp_column_span: str = ""
    insp_rules: str = ""
    insp_max_length: str = ""
    insp_min_length: str = ""
    insp_collapsible: bool = False
    insp_collapsed: bool = False
    insp_dense: bool = False
    props: dict[str, Any] = {}
    # Handlers
    handler_index: int = -1
    handler_to: str = ""
    handler_subject: str = ""
    handler_url: str = ""
    handler_callable: str = ""
    # Preview
    preview_html: str = ""
    data: dict[str, Any] = {}
    preview_error: str = ""
    preview_success: str = ""
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
        return _DesignerPublic(
            {
                "form_id",
                "loaded_form_id",
                "title",
                "slug",
                "status",
                "form_columns",
                "definition_json",
                "settings_json",
                "selected_path",
                "palette_filter",
                "palette_group",
                "inspector_open",
                "preview_open",
                "json_open",
                "handlers_open",
                "insp_label",
                "insp_name",
                "insp_placeholder",
                "insp_helper_text",
                "insp_hint",
                "insp_default",
                "insp_required",
                "insp_readonly",
                "insp_disabled",
                "insp_hidden",
                "insp_heading",
                "insp_description",
                "insp_columns",
                "insp_column_span",
                "insp_rules",
                "insp_max_length",
                "insp_min_length",
                "insp_collapsible",
                "insp_collapsed",
                "insp_dense",
                "handler_index",
                "handler_to",
                "handler_subject",
                "handler_url",
                "handler_callable",
                "preview_html",
                "data",
                "select_search",
                "morph_search",
                "table_select",
                "preview_error",
                "preview_success",
                "props",
                "error",
                "saved",
                "message",
            }
        )

    def set_property(self, name: str, value: Any) -> None:
        if isinstance(name, str) and name.startswith("props."):
            parts = name.split(".")[1:]
            bag = dict(self.props or {})
            if len(parts) == 1:
                bag[parts[0]] = value
            elif len(parts) >= 2:
                parent = bag.get(parts[0])
                nested = dict(parent) if isinstance(parent, dict) else {}
                nested[".".join(parts[1:])] = value
                bag[parts[0]] = nested
            self.props = bag
            return
        super().set_property(name, value)

    def _option_map(self) -> dict[str, Any]:
        raw = (self.props or {}).get("options")
        return dict(raw) if isinstance(raw, dict) else {}

    def add_option_row(self) -> None:
        options = self._option_map()
        n = 1
        while f"option_{n}" in options:
            n += 1
        options[f"option_{n}"] = ""
        bag = dict(self.props or {})
        bag["options"] = options
        self.props = bag

    def remove_option_row(self, key: str = "") -> None:
        options = self._option_map()
        options.pop(str(key), None)
        bag = dict(self.props or {})
        bag["options"] = options
        self.props = bag

    def set_option_key(self, key: str = "", new_key: str = "") -> None:
        options = self._option_map()
        old = str(key)
        renamed = str(new_key or "").strip()
        if old not in options or not renamed or renamed == old:
            return
        out: dict[str, Any] = {}
        for existing, val in options.items():
            out[renamed if existing == old else existing] = val
        bag = dict(self.props or {})
        bag["options"] = out
        self.props = bag

    def mount(self, **kwargs: Any) -> None:
        self.error = ""
        self.saved = False
        self.message = ""
        if kwargs.get("form_id"):
            self.form_id = str(kwargs["form_id"])
        if not self.definition_json:
            self._set_definition(empty_definition())
        self._sync_form_columns()
        if self.form_id and self.form_id != self.loaded_form_id:
            self.load_form(self.form_id)
            return
        self._refresh_preview()
        self._sync_inspector()

    def updatedFormColumns(self, value: Any = None) -> None:
        if value is not None:
            self.form_columns = str(value)
        self.apply_form_columns()

    def _definition(self) -> dict[str, Any]:
        try:
            data = json.loads(self.definition_json or "{}")
        except json.JSONDecodeError:
            return empty_definition()
        return ensure_definition(data if isinstance(data, dict) else empty_definition())

    def _set_definition(self, definition: dict[str, Any]) -> None:
        data = ensure_definition(definition)
        self.definition_json = json.dumps(data, indent=2)
        self._sync_form_columns()

    def _sync_form_columns(self) -> None:
        cols = self._definition().get("columns", 2)
        self.form_columns = str(cols if isinstance(cols, int) and cols >= 1 else 2)

    def apply_form_columns(self) -> None:
        try:
            cols = max(1, min(12, int(self.form_columns or 2)))
        except ValueError:
            cols = 2
            self.form_columns = "2"
        definition = self._definition()
        definition["columns"] = cols
        self._set_definition(definition)
        self.message = f"Form columns set to {cols}."

    def _settings(self) -> dict[str, Any]:
        try:
            data = json.loads(self.settings_json or "{}")
        except json.JSONDecodeError:
            return {"handlers": [{"type": "store"}]}
        return data if isinstance(data, dict) else {"handlers": [{"type": "store"}]}

    def _set_settings(self, settings: dict[str, Any]) -> None:
        self.settings_json = json.dumps(settings if isinstance(settings, dict) else {}, indent=2)

    def _handlers(self) -> list[dict[str, Any]]:
        handlers = self._settings().get("handlers")
        return [h for h in handlers if isinstance(h, dict)] if isinstance(handlers, list) else []

    def updatedFormId(self, value: Any = None) -> None:
        """Auto-load when the form select changes (Conduit/Livewire camelCase hook)."""
        fid = str(value if value is not None else self.form_id or "")
        self.form_id = fid
        if not fid:
            return
        if fid == self.loaded_form_id:
            return
        self.load_form(fid)

    def updated_form_id(self, value: Any = None) -> None:
        """Snake-case alias for hosts that call updated_* literally."""
        self.updatedFormId(value)

    def updatedForm_id(self, value: Any = None) -> None:
        self.updatedFormId(value)

    def load_form(self, form_id: str = "") -> None:
        self.error = ""
        self.saved = False
        self.message = ""
        fid = str(form_id or self.form_id or "")
        if not fid:
            self.error = "Select a form to load."
            return
        form = get_form_store().get_definition(fid)
        if form is None:
            self.error = "Form not found."
            return
        self.form_id = form.id
        self.loaded_form_id = form.id
        self.title = form.title
        self.slug = form.slug
        self.status = form.status
        self._set_definition(
            form.definition if isinstance(form.definition, dict) else empty_definition()
        )
        self._set_settings(form.settings if isinstance(form.settings, dict) else {})
        self.selected_path = ""
        self.inspector_open = False
        self._refresh_preview()
        self._sync_inspector()
        self.message = f"Loaded “{form.title}”."

    def new_form(self) -> None:
        self.form_id = ""
        self.loaded_form_id = ""
        self.title = "Untitled form"
        self.slug = "untitled"
        self.status = "draft"
        self._set_definition(
            {
                "columns": 2,
                "components": [
                    {
                        "type": "TextInput",
                        "name": "name",
                        "label": "Name",
                        "required": True,
                    }
                ],
            }
        )
        self._set_settings({"handlers": [{"type": "store"}]})
        self.selected_path = "0"
        self.inspector_open = False
        self.error = ""
        self.saved = False
        self.message = "New draft ready."
        self._refresh_preview()
        self._sync_inspector()

    def select(self, path: str = "") -> None:
        self.selected_path = str(path or "")
        self._sync_inspector()

    def open_inspector(self, path: str = "") -> None:
        self.selected_path = str(path or self.selected_path or "")
        self._sync_inspector()
        if not self.selected_path or get_node(self._definition(), self.selected_path) is None:
            self.error = "Select a component first."
            self.inspector_open = False
            return
        self.inspector_open = True
        self.error = ""

    def close_inspector(self) -> None:
        self.inspector_open = False

    def open_preview(self) -> None:
        self.preview_open = True
        self.data = {}
        self.preview_error = ""
        self.preview_success = ""
        self._refresh_preview()

    def close_preview(self) -> None:
        self.preview_open = False

    def toggle_json(self) -> None:
        self.json_open = not bool(self.json_open)

    def toggle_handlers(self) -> None:
        self.handlers_open = not bool(self.handlers_open)

    def get_form(self) -> Any:
        """Used by FormDataMutations helpers during preview."""
        try:
            return build_form(self._definition(), name="preview")
        except Exception:  # noqa: BLE001
            return None

    def _selected_type(self, node: dict[str, Any] | None = None) -> str:
        node = node if node is not None else get_node(self._definition(), self.selected_path)
        if not isinstance(node, dict):
            return ""
        kind = str(node.get("type") or "")
        if kind:
            return kind
        if ".steps." in self.selected_path:
            return "_Step"
        if ".tabs." in self.selected_path:
            return "_Tab"
        return ""

    def _sync_inspector(self) -> None:
        node = get_node(self._definition(), self.selected_path)
        specs = props_for(self._selected_type(node)) if node else []
        bag: dict[str, Any] = {}
        if node:
            for spec in specs:
                key = spec["key"]
                if spec["kind"] == "bool" and key not in node:
                    bag[key] = spec.get("default") == "1"
                elif spec["kind"] == "kv":
                    raw = node.get(key)
                    bag[key] = dict(raw) if isinstance(raw, dict) else {}
                else:
                    bag[key] = display_value(node, key, spec["kind"])
        self.props = bag
        self.insp_label = str(bag.get("label") or "")
        self.insp_name = str(bag.get("name") or "")
        self.insp_placeholder = str(bag.get("placeholder") or "")
        self.insp_required = bool(bag.get("required"))
        self.insp_columns = "" if bag.get("columns") in (None, "") else str(bag.get("columns"))
        self.insp_column_span = (
            "" if bag.get("column_span") in (None, "") else str(bag.get("column_span"))
        )

    def apply_inspector(self) -> None:
        self.error = ""
        if not self.selected_path:
            self.error = "Select a component first."
            return
        specs = {row["key"]: row for row in props_for(self._selected_type())}
        bag = dict(self.props or {})
        current = get_node(self._definition(), self.selected_path) or {}
        updates: dict[str, Any] = {}
        for key, spec in specs.items():
            if key not in bag:
                continue
            kind = spec["kind"]
            value = coerce_value(kind, bag.get(key))
            default_on = spec.get("default") == "1"
            # Leave omitted flags out so component defaults stay intact.
            if kind == "bool" and key not in current and bool(value) == default_on:
                continue
            updates[key] = value
        try:
            definition = update_node(self._definition(), self.selected_path, updates)
        except ValueError as exc:
            self.error = str(exc)
            return
        self._set_definition(definition)
        self._refresh_preview()
        self.message = "Properties saved."
        self.inspector_open = False

    def add_field(
        self,
        type_name: str = "TextInput",
        parent_path: str = "",
        index: int | None = None,
    ) -> None:
        self.error = ""
        if type_name not in all_type_names():
            self.error = f"Unknown type: {type_name}"
            return
        parent = parent_path if parent_path is not None else ""
        if parent == "" and self.selected_path:
            # Click-add uses selection; DnD passes explicit list path
            parent = self.selected_path
        definition = self._definition()
        hint = len(walk_tree(definition))
        node = default_node(type_name, index_hint=hint)
        try:
            definition, new_path = insert_node(
                definition,
                parent,
                node,
                index=None if index is None else int(index),
            )
        except ValueError as exc:
            self.error = str(exc)
            return
        self._set_definition(definition)
        self.selected_path = new_path
        self._refresh_preview()
        self._sync_inspector()
        self.message = f"Added {type_name}."

    def delete_selected(self) -> None:
        self.delete_path(self.selected_path)

    def delete_path(self, path: str = "") -> None:
        self.error = ""
        target = str(path or self.selected_path or "")
        if not target:
            self.error = "Select a component to delete."
            return
        try:
            definition = delete_node(self._definition(), target)
        except ValueError as exc:
            self.error = str(exc)
            return
        self._set_definition(definition)
        self.selected_path = ""
        self.inspector_open = False
        self._refresh_preview()
        self._sync_inspector()
        self.message = "Component removed."

    def move(self, from_path: str = "", to_parent: str = "", index: int = 0) -> None:
        self.error = ""
        if not from_path:
            self.error = "Missing move source."
            return
        # Palette clones arrive as type names prefixed with "type:"
        if from_path.startswith("type:"):
            type_name = from_path[5:]
            self.add_field(type_name, parent_path=to_parent or "", index=int(index))
            return
        try:
            definition = move_node(self._definition(), from_path, to_parent or "", int(index))
        except ValueError as exc:
            self.error = str(exc)
            return
        self._set_definition(definition)
        list_path = resolve_insert_list_path(definition, to_parent or "")
        self.selected_path = f"{list_path}.{index}".strip(".") if list_path else str(index)
        self._refresh_preview()
        self._sync_inspector()

    def add_handler(self, handler_type: str = "store") -> None:
        settings = self._settings()
        handlers = list(self._handlers())
        entry: dict[str, Any] = {"type": str(handler_type or "store")}
        if entry["type"] == "email":
            entry["to"] = ""
            entry["subject"] = "New submission"
        elif entry["type"] == "webhook":
            entry["url"] = ""
        elif entry["type"] == "callable":
            entry["name"] = ""
        handlers.append(entry)
        settings["handlers"] = handlers
        self._set_settings(settings)
        self.handler_index = len(handlers) - 1
        self._load_handler_fields()
        self.message = "Handler added."

    def remove_handler(self, index: int = 0) -> None:
        settings = self._settings()
        handlers = list(self._handlers())
        idx = int(index)
        if 0 <= idx < len(handlers):
            handlers.pop(idx)
            settings["handlers"] = handlers
            self._set_settings(settings)
            self.handler_index = -1
            self._load_handler_fields()
            self.message = "Handler removed."

    def select_handler(self, index: int = 0) -> None:
        self.handler_index = int(index)
        self._load_handler_fields()

    def _load_handler_fields(self) -> None:
        handlers = self._handlers()
        idx = int(self.handler_index)
        if not (0 <= idx < len(handlers)):
            self.handler_to = ""
            self.handler_subject = ""
            self.handler_url = ""
            self.handler_callable = ""
            return
        h = handlers[idx]
        self.handler_to = str(h.get("to") or "")
        self.handler_subject = str(h.get("subject") or "")
        self.handler_url = str(h.get("url") or "")
        self.handler_callable = str(h.get("name") or "")

    def apply_handler(self) -> None:
        settings = self._settings()
        handlers = list(self._handlers())
        idx = int(self.handler_index)
        if not (0 <= idx < len(handlers)):
            self.error = "Select a handler first."
            return
        h = dict(handlers[idx])
        if h.get("type") == "email":
            h["to"] = self.handler_to
            h["subject"] = self.handler_subject
        elif h.get("type") == "webhook":
            h["url"] = self.handler_url
        elif h.get("type") == "callable":
            h["name"] = self.handler_callable
        handlers[idx] = h
        settings["handlers"] = handlers
        self._set_settings(settings)
        self.message = "Handler updated."
        self.error = ""

    def preview(self) -> None:
        self.open_preview()

    def _refresh_preview(self) -> None:
        try:
            definition = self._definition()
            problems = validate_definition(definition)
            if problems:
                self.preview_html = '<p class="or-danger">' + e("; ".join(problems)) + "</p>"
                return
            form = build_form(definition, name="preview")
            self.preview_html = form.render(
                self.data if isinstance(self.data, dict) else {},
                form_errors=getattr(self, "_preview_form_errors", {}),
                upload_url=self._upload_url(),
            )
            self.error = ""
        except Exception as exc:  # noqa: BLE001
            self.preview_html = f'<p class="or-danger">{e(str(exc))}</p>'

    def _upload_url(self) -> str:
        panel = type(self)._panel
        if panel is not None:
            getter = getattr(panel, "upload_url", None)
            if callable(getter):
                try:
                    return str(getter())
                except Exception:  # noqa: BLE001
                    pass
        return "/orbit-upload"

    def submit_preview(self) -> None:
        self.preview_error = ""
        self.preview_success = ""
        try:
            form = build_form(self._definition(), name="preview")
            errors = form.validate(dict(self.data or {}))
            if errors:
                self._preview_form_errors = errors  # type: ignore[attr-defined]
                self.preview_error = "Please fix the highlighted fields."
                self._refresh_preview()
                return
            self._preview_form_errors = {}  # type: ignore[attr-defined]
            self.preview_success = "Preview submission looks valid (not stored)."
            self._refresh_preview()
        except Exception as exc:  # noqa: BLE001
            self.preview_error = str(exc)

    def _slug_taken(self, slug: str, *, exclude_id: str = "") -> bool:
        other = get_form_store().get_definition_by_slug(slug)
        if other is None:
            return False
        return other.id != exclude_id

    def save(self, publish: bool = False) -> None:
        self.error = ""
        self.saved = False
        self.message = ""
        definition = self._definition()
        problems = validate_definition(definition)
        if problems:
            self.error = "; ".join(problems)
            return
        settings = self._settings()
        store = get_form_store()
        slug = (self.slug or "untitled").strip()
        title = (self.title or "Untitled form").strip()

        if self.form_id and self.form_id != self.loaded_form_id:
            self.error = "Load the selected form before saving, or click New."
            return
        target_id = self.loaded_form_id or ""

        existing = store.get_definition(target_id) if target_id else None
        if target_id and existing is None:
            self.error = "Form not found — it may have been deleted. Click New or Load."
            return

        if self._slug_taken(slug, exclude_id=existing.id if existing else ""):
            self.error = f"Slug “{slug}” is already in use."
            return

        form = existing or FormDefinition(
            slug=slug,
            title=title,
            definition=definition,
            settings=settings,
            tenant_id=current_tenant_id(),
        )
        form.title = title
        form.slug = slug
        form.definition = definition
        form.settings = settings
        form.status = "published" if publish else "draft"
        form.tenant_id = form.tenant_id or current_tenant_id()
        store.save_definition(form)
        self.form_id = form.id
        self.loaded_form_id = form.id
        self.status = form.status
        self.saved = True
        self.message = "Published." if publish else "Draft saved."
        self._refresh_preview()

    def publish(self) -> None:
        self.save(publish=True)

    def _attr(self, kind: str, value: str) -> str:
        from almasix.orbit.support.conduit_attrs import conduit_attr

        return conduit_attr(kind, value)

    def _render_palette(self) -> str:
        q = (self.palette_filter or "").strip().lower()
        group_filter = (self.palette_group or "all").lower()
        bits: list[str] = [
            f'<div class="or-fb-palette-tools">'
            f'<input class="or-input" placeholder="Filter components…" '
            f"{self._attr('model', 'palette_filter')} />"
            f'<select class="or-input" {self._attr("model", "palette_group")}>'
            f'<option value="all"{" selected" if group_filter == "all" else ""}>All</option>'
            f'<option value="fields"{" selected" if group_filter == "fields" else ""}>Fields</option>'
            f'<option value="layouts"{" selected" if group_filter == "layouts" else ""}>Layouts</option>'
            f'<option value="primes"{" selected" if group_filter == "primes" else ""}>Primes</option>'
            f"</select></div>"
            f'<p class="or-muted or-fb-hint">Drag onto the canvas, or click to add into the selection.</p>'
            f'<ul class="or-fb-palette-list" data-or-fb-palette="1">'
        ]
        for group in PALETTE:
            gkey = str(group["label"]).lower()
            if group_filter != "all" and group_filter not in gkey:
                continue
            for t in group["types"]:
                if q and q not in t.lower():
                    continue
                click = self._attr("click", f'add_field("{t}")')
                bits.append(
                    f'<li class="or-fb-palette-item" data-type="{e(t)}" data-path="type:{e(t)}">'
                    f'<button type="button" class="or-fb-palette-btn" {click}>'
                    f'<span class="or-fb-handle">⠿</span> {e(t)}'
                    f'<span class="or-muted or-fb-palette-kind">{e(group["label"])}</span>'
                    f"</button></li>"
                )
        bits.append("</ul>")
        return "".join(bits)

    def _render_options_editor(self, label: str, hint: str) -> str:
        rows: list[str] = []
        for key, value in self._option_map().items():
            key_change = self._attr("change", f"set_option_key({key!r}, $event.target.value)")
            value_model = self._attr("model", f"props.options.{key}")
            remove = self._attr("click", f"remove_option_row({key!r})")
            rows.append(
                '<div class="or-key-value-row">'
                f'<input class="or-input or-key-value-key" value="{e(str(key))}" '
                f'placeholder="value" aria-label="Value" {key_change} />'
                f'<input class="or-input or-key-value-value" value="{e(str(value))}" '
                f'placeholder="Label" aria-label="Label" {value_model} />'
                f'<button type="button" class="or-key-value-remove or-btn or-btn-gray or-btn-sm" '
                f'{remove} aria-label="Remove row">&times;</button>'
                "</div>"
            )
        if not rows:
            rows.append(
                '<p class="or-muted or-fb-help">No options yet. Add a row for each choice.</p>'
            )
        add = self._attr("click", "add_option_row()")
        return (
            '<div class="or-field or-field-KeyValue">'
            f'<span class="or-label">{e(label)}</span>{hint}'
            '<div class="or-key-value-editor">'
            '<div class="or-key-value-head"><span>Value</span><span>Label</span>'
            '<span class="or-key-value-head-spacer" aria-hidden="true"></span></div>'
            f"{''.join(rows)}</div>"
            f'<button type="button" class="or-btn or-btn-gray or-btn-sm" {add}>Add option</button>'
            "</div>"
        )

    def _render_inspector_modal(self) -> str:
        if not self.inspector_open:
            return ""
        node = get_node(self._definition(), self.selected_path)
        if node is None:
            return ""
        t = self._selected_type(node)
        specs = props_for(t)
        fields: list[str] = []
        for spec in specs:
            key = spec["key"]
            kind = spec["kind"]
            label = spec["label"]
            help_text = spec.get("help") or ""
            model = f"props.{key}"
            hint = f'<span class="or-muted or-fb-help">{e(help_text)}</span>' if help_text else ""
            if kind == "bool":
                fields.append(
                    f'<label class="or-fb-check"><input type="checkbox" '
                    f"{self._attr('model', model)} /> {e(label)}</label>{hint}"
                )
            elif kind == "number":
                fields.append(
                    f'<label>{e(label)} {hint}<input class="or-input" type="number" '
                    f"{self._attr('model', model)} /></label>"
                )
            elif kind == "choice":
                options = "".join(
                    f'<option value="{e(item)}">{e(item)}</option>'
                    for item in str(spec.get("choices") or "").split("|")
                    if item
                )
                fields.append(
                    f'<label>{e(label)} {hint}<select class="or-input" '
                    f'{self._attr("model", model)}><option value="">—</option>{options}</select></label>'
                )
            elif kind == "kv":
                fields.append(self._render_options_editor(label, hint))
            elif kind in {"json", "csv"}:
                fields.append(
                    f'<label>{e(label)} {hint}<textarea class="or-input" rows="4" '
                    f'placeholder="draft: Draft&#10;published: Published" '
                    f"{self._attr('model', model)}></textarea></label>"
                )
            else:
                fields.append(
                    f'<label>{e(label)} {hint}<input class="or-input" type="text" '
                    f"{self._attr('model', model)} /></label>"
                )

        return f"""
<div class="or-fb-modal" role="dialog" aria-modal="true">
  <div class="or-fb-modal-backdrop" {self._attr("click", "close_inspector()")}></div>
  <div class="or-fb-modal-panel or-fb-modal-wide">
    <header class="or-fb-modal-head">
      <h2>Properties · {e(t or "Component")} <code>{e(self.selected_path)}</code></h2>
      <button type="button" class="or-btn" {self._attr("click", "close_inspector()")}>Close</button>
    </header>
    <div class="or-fb-modal-body or-fb-inspector-fields">{"".join(fields) or "<p class='or-muted'>No editable props.</p>"}</div>
    <footer class="or-fb-modal-foot">
      <button type="button" class="or-btn or-btn-primary" {self._attr("click", "apply_inspector()")}>Save properties</button>
    </footer>
  </div>
</div>
"""

    def _render_preview_modal(self) -> str:
        if not self.preview_open:
            return ""
        notice = ""
        if self.preview_success:
            notice = f'<p class="or-success">{e(self.preview_success)}</p>'
        elif self.preview_error:
            notice = f'<p class="or-danger">{e(self.preview_error)}</p>'
        return f"""
<div class="or-fb-modal" role="dialog" aria-modal="true">
  <div class="or-fb-modal-backdrop" {self._attr("click", "close_preview()")}></div>
  <div class="or-fb-modal-panel or-fb-modal-wide">
    <header class="or-fb-modal-head">
      <h2>Preview · {e(self.title)}</h2>
      <button type="button" class="or-btn" {self._attr("click", "close_preview()")}>Close</button>
    </header>
    <div class="or-fb-modal-body">
      {notice}
      <form {self._attr("submit", "submit_preview")}>
        {self.preview_html}
        <div class="or-form-actions">
          <button type="submit" class="or-btn or-btn-primary">Submit preview</button>
        </div>
      </form>
    </div>
  </div>
</div>
"""

    def _render_handlers_panel(self) -> str:
        if not self.handlers_open:
            return ""
        rows: list[str] = []
        for i, handler in enumerate(self._handlers()):
            htype = e(str(handler.get("type") or "store"))
            active = " is-selected" if i == int(self.handler_index) else ""
            sel = f"select_handler({i})"
            rem = f"remove_handler({i})"
            rows.append(
                f'<button type="button" class="or-btn or-btn-sm{active}" '
                f"{self._attr('click', sel)}>{htype} #{i}</button>"
                f'<button type="button" class="or-btn or-btn-sm" '
                f"{self._attr('click', rem)}>Remove</button>"
            )
        edit = ""
        idx = int(self.handler_index)
        handlers = self._handlers()
        if 0 <= idx < len(handlers):
            h = handlers[idx]
            fields = []
            if h.get("type") == "email":
                fields.append(
                    f'<label>To <input class="or-input" {self._attr("model", "handler_to")} /></label>'
                    f'<label>Subject <input class="or-input" {self._attr("model", "handler_subject")} /></label>'
                )
            elif h.get("type") == "webhook":
                fields.append(
                    f'<label>URL <input class="or-input" {self._attr("model", "handler_url")} /></label>'
                )
            elif h.get("type") == "callable":
                fields.append(
                    f'<label>Name <input class="or-input" {self._attr("model", "handler_callable")} /></label>'
                )
            else:
                fields.append('<p class="or-muted">Store handler has no extra options.</p>')
            edit = (
                f'<div class="or-fb-handler-edit">{"".join(fields)}'
                f'<button type="button" class="or-btn or-btn-primary" '
                f"{self._attr('click', 'apply_handler()')}>Apply handler</button></div>"
            )
        add_btns = "".join(
            (
                f'<button type="button" class="or-btn or-btn-sm" '
                f"{self._attr('click', f'add_handler({t!r})')}>+ {t}</button>"
            )
            for t in ("store", "email", "webhook", "callable")
        )
        return (
            f'<div class="or-fb-handlers-drawer">'
            f"<h3>Answer handlers</h3>"
            f'<div class="or-fb-handler-row">{"".join(rows)}</div>{edit}'
            f'<div class="or-fb-handler-add">{add_btns}</div></div>'
        )

    def render(self) -> str:
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
        canvas = render_canvas(
            self._definition(),
            selected_path=self.selected_path,
            attr=self._attr,
        )
        json_block = ""
        if self.json_open:
            json_block = f'<pre class="or-fb-json" tabindex="0">{e(self.definition_json)}</pre>'

        return f"""
<div class="or-page or-page-form-builder" data-or-fb-root="1">
  <h1 class="or-page-title">Form builder</h1>
  {notice}
  <div class="or-fb-toolbar">
    <select class="or-input" {self._attr("model.live", "form_id")}>
      <option value="">— select form —</option>
      {form_options}
    </select>
    <button type="button" class="or-btn" {self._attr("click", "new_form()")}>New</button>
    <button type="button" class="or-btn or-btn-primary" {self._attr("click", "save()")}>Save draft</button>
    <button type="button" class="or-btn or-btn-primary" {self._attr("click", "publish()")}>Publish</button>
    <button type="button" class="or-btn" {self._attr("click", "toggle_handlers()")}>Handlers</button>
    <button type="button" class="or-btn" {self._attr("click", "toggle_json()")}>JSON</button>
    <button type="button" class="or-btn or-btn-primary or-fb-preview-btn" {self._attr("click", "open_preview()")}>Preview</button>
  </div>
  <div class="or-fb-meta">
    <label>Title <input class="or-input" {self._attr("model", "title")} /></label>
    <label>Slug <input class="or-input" {self._attr("model", "slug")} /></label>
    <label>Form columns
      <input class="or-input" type="number" min="1" max="12" style="width:4.5rem"
        {self._attr("model.live", "form_columns")} />
    </label>
    <button type="button" class="or-btn or-btn-sm" {self._attr("click", "apply_form_columns()")}>Apply columns</button>
    <span class="or-muted">Status: {e(self.status)}</span>
  </div>
  {self._render_handlers_panel()}
  {json_block}
  <div class="or-fb-workspace">
    <aside class="or-fb-palette">
      <h2>Components</h2>
      {self._render_palette()}
    </aside>
    <section class="or-fb-canvas-wrap">
      <h2>Canvas</h2>
      <p class="or-muted or-fb-hint">Click a field or layout to edit properties. Drop zones highlight while dragging.</p>
      {canvas}
    </section>
  </div>
  {self._render_inspector_modal()}
  {self._render_preview_modal()}
</div>
{_DESIGNER_CSS}
{_DESIGNER_JS}
"""


_DESIGNER_CSS = """
<style>
.or-fb-workspace { display:grid; grid-template-columns: 16rem minmax(0,1fr); gap:1rem; align-items:start; min-height:70vh; }
.or-fb-palette { position:sticky; top:1rem; max-height:calc(100vh - 2rem); overflow:auto; border:1px solid var(--or-border,#e5e7eb); border-radius:.75rem; padding:.75rem; background:var(--or-bg,#fff); }
.or-fb-palette-tools { display:flex; flex-direction:column; gap:.4rem; margin-bottom:.6rem; }
.or-fb-palette-list { list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:.3rem; }
.or-fb-palette-item { margin:0; }
.or-fb-palette-btn { width:100%; text-align:left; display:flex; align-items:center; gap:.35rem; flex-wrap:wrap; padding:.45rem .55rem; border:1px solid var(--or-border,#e5e7eb); border-radius:.45rem; background:var(--or-bg-muted,#f9fafb); cursor:grab; font:inherit; color:inherit; }
.or-fb-palette-kind { margin-left:auto; font-size:.7rem; }
.or-fb-canvas-wrap { min-width:0; }
.or-fb-canvas-root { border:1px dashed var(--or-border,#d1d5db); border-radius:.75rem; padding:1rem; min-height:28rem; background: color-mix(in srgb, var(--or-bg-muted,#f3f4f6) 55%, transparent); }
.or-fb-dropzone { list-style:none; margin:.5rem 0 0; padding:.5rem; min-height:3.5rem; border-radius:.5rem; border:2px dashed transparent; transition: border-color .15s, background .15s; }
.or-fb-dropzone-grid {
  display:grid !important;
  grid-template-columns: repeat(var(--or-fb-cols, 2), minmax(0, 1fr)) !important;
  gap:.75rem; align-items:start;
}
.or-fb-toolbar { display:flex; flex-wrap:wrap; gap:.5rem; margin-bottom:.75rem; align-items:center; }
.or-fb-preview-btn { margin-left:auto; }
.or-fb-dropzone.is-drop-target { border-color: var(--or-primary,#f1511b); background: color-mix(in srgb, var(--or-primary,#f1511b) 10%, transparent); }
.or-fb-empty-drop { grid-column: 1 / -1; text-align:center; padding:1.25rem; color: var(--or-muted,#6b7280); font-size:.9rem; pointer-events:none; }
.or-fb-node { list-style:none; margin:0; min-width:0; }
.or-fb-card { border:1px solid var(--or-border,#e5e7eb); border-radius:.65rem; background:var(--or-bg,#fff); padding:.55rem .65rem .75rem; box-shadow:0 1px 2px rgb(0 0 0 / 4%); cursor:pointer; }
.or-fb-node.is-selected > .or-fb-card { outline:2px solid var(--or-primary,#f1511b); outline-offset:1px; }
.or-fb-node-chrome { display:flex; flex-wrap:wrap; align-items:center; gap:.35rem; margin-bottom:.45rem; }
.or-fb-type-badge { font-size:.7rem; font-weight:600; text-transform:uppercase; letter-spacing:.03em; opacity:.7; }
.or-fb-handle { cursor:grab; opacity:.55; user-select:none; padding:0 .2rem; }
.or-fb-field-label { font-weight:600; margin-bottom:.25rem; font-size:.9rem; }
.or-fb-req { color: var(--or-danger,#dc2626); }
.or-fb-help { font-size:.8rem; margin:.25rem 0 0; }
.or-fb-upload { border:1px dashed var(--or-border,#d1d5db); border-radius:.4rem; padding:.75rem; text-align:center; color:var(--or-muted,#6b7280); font-size:.85rem; }
.or-fb-hidden-chip { font-size:.8rem; opacity:.65; font-family:ui-monospace,monospace; }
.or-fb-layout-title { font-weight:700; margin-bottom:.35rem; }
.or-fb-layout-section, .or-fb-layout-fieldset { border-left:3px solid var(--or-primary,#f1511b); padding-left:.6rem; }
.or-fb-meta, .or-fb-handler-add, .or-fb-handler-row { display:flex; flex-wrap:wrap; gap:.5rem; margin-bottom:.75rem; align-items:center; }
.or-fb-handlers-drawer { border:1px solid var(--or-border,#e5e7eb); border-radius:.65rem; padding:.75rem; margin-bottom:.75rem; }
.or-fb-json { font-family: ui-monospace, monospace; font-size:.8rem; width:100%; max-height:16rem; overflow:auto; padding:.75rem; border:1px solid var(--or-border,#e5e7eb); border-radius:.5rem; background: var(--or-bg-muted, #f9fafb); white-space:pre-wrap; margin-bottom:.75rem; }
.or-fb-inspector-fields, .or-fb-handler-edit { display:flex; flex-direction:column; gap:.5rem; }
.or-fb-hint { font-size:.85rem; }
.or-fb-check { display:flex; align-items:center; gap:.35rem; }
.or-btn.is-selected { outline:2px solid var(--or-primary,#f1511b); }
.or-fb-modal { position:fixed; inset:0; z-index:80; display:flex; align-items:flex-start; justify-content:center; padding:4vh 1rem; }
.or-fb-modal-backdrop { position:absolute; inset:0; background:rgb(15 23 42 / 45%); }
.or-fb-modal-panel { position:relative; z-index:1; width:min(36rem,100%); max-height:90vh; overflow:auto; background:var(--or-bg,#fff); border-radius:.85rem; box-shadow:0 20px 50px rgb(0 0 0 / 25%); }
.or-fb-modal-wide { width:min(96vw, 1536px); max-height:92vh; }
.or-fb-modal-head, .or-fb-modal-foot { display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.85rem 1rem; border-bottom:1px solid var(--or-border,#e5e7eb); }
.or-fb-modal-foot { border-bottom:0; border-top:1px solid var(--or-border,#e5e7eb); }
.or-fb-modal-body { padding:1rem; }
.sortable-ghost { opacity:.35; }
.sortable-drag { opacity:.95; box-shadow:0 12px 28px rgb(0 0 0 / 18%); transform: scale(1.02); }
.or-fb-palette-item.sortable-ghost .or-fb-palette-btn { outline:2px dashed var(--or-primary,#f1511b); }
@media (max-width: 960px) { .or-fb-workspace { grid-template-columns: 1fr; } .or-fb-palette { position:static; max-height:none; } }
</style>
"""

_DESIGNER_JS = """
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>
<script>
(function () {
  function findConduit() {
    var root = document.querySelector("[data-or-fb-root]");
    var host = root && root.closest("[wire\\\\:id], [conduit\\\\:id], [data-conduit-id]");
    if (!host) host = document.querySelector("[conduit\\\\:id], [data-conduit-id], [wire\\\\:id]");
    return host && (host.__conduit || host.__livewire) || null;
  }
  function callHost(name) {
    var args = Array.prototype.slice.call(arguments, 1);
    var c = findConduit();
    if (!c) return;
    if (typeof c.call === "function") { c.call.apply(c, [name].concat(args)); return; }
    if (typeof c[name] === "function") { c[name].apply(c, args); }
  }
  function markTargets(active) {
    document.querySelectorAll("[data-or-fb-sortable]").forEach(function (el) {
      el.classList.toggle("is-drop-target", !!active);
    });
  }
  function wire(root) {
    if (!root || typeof Sortable === "undefined") return;
    var palette = root.querySelector("[data-or-fb-palette]");
    if (palette && !palette.dataset.orFbSortWired) {
      palette.dataset.orFbSortWired = "1";
      Sortable.create(palette, {
        group: { name: "or-fb", pull: "clone", put: false },
        sort: false,
        animation: 150,
        handle: ".or-fb-handle, .or-fb-palette-btn",
        draggable: ".or-fb-palette-item",
        ghostClass: "sortable-ghost",
        dragClass: "sortable-drag",
        onStart: function () { markTargets(true); },
        onEnd: function () { markTargets(false); }
      });
    }
    root.querySelectorAll("[data-or-fb-sortable]").forEach(function (tree) {
      if (tree.dataset.orFbSortWired) return;
      tree.dataset.orFbSortWired = "1";
      Sortable.create(tree, {
        group: { name: "or-fb", pull: true, put: true },
        handle: ".or-fb-handle",
        animation: 150,
        draggable: ".or-fb-node",
        ghostClass: "sortable-ghost",
        dragClass: "sortable-drag",
        filter: ".or-fb-empty-drop",
        emptyInsertThreshold: 24,
        onStart: function () { markTargets(true); },
        onAdd: function (evt) {
          markTargets(false);
          var item = evt.item;
          var toList = evt.to;
          if (!item || !toList) return;
          var type = item.getAttribute("data-type");
          var toParent = toList.getAttribute("data-list-path") || "";
          var index = typeof evt.newIndex === "number" ? evt.newIndex : 0;
          if (type) {
            item.parentNode && item.parentNode.removeChild(item);
            callHost("move", "type:" + type, toParent, index);
            return;
          }
          var fromPath = item.getAttribute("data-path") || "";
          callHost("move", fromPath, toParent, index);
        },
        onUpdate: function (evt) {
          markTargets(false);
          var item = evt.item;
          var toList = evt.to;
          if (!item || !toList) return;
          if (item.getAttribute("data-type")) return;
          var fromPath = item.getAttribute("data-path") || "";
          var toParent = toList.getAttribute("data-list-path") || "";
          var index = typeof evt.newIndex === "number" ? evt.newIndex : 0;
          callHost("move", fromPath, toParent, index);
        },
        onEnd: function () { markTargets(false); }
      });
    });
  }
  function boot() {
    document.querySelectorAll("[data-or-fb-root]").forEach(wire);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  document.addEventListener("conduit:navigated", boot);
  document.addEventListener("livewire:navigated", boot);
  document.addEventListener("morph.updated", function () {
    document.querySelectorAll("[data-or-fb-root]").forEach(function (root) {
      root.querySelectorAll("[data-or-fb-sortable], [data-or-fb-palette]").forEach(function (t) {
        delete t.dataset.orFbSortWired;
      });
    });
    boot();
  });
})();
</script>
"""
