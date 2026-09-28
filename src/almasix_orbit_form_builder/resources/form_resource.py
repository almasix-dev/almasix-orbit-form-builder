"""Resource listing form definitions from the plugin store."""

from __future__ import annotations

import json
from typing import Any, ClassVar

from almasix.orbit.actions.action import DeleteAction, EditAction, ViewAction
from almasix.orbit.forms import Form, Placeholder, Select, Textarea, TextInput
from almasix.orbit.panels.resource import Resource
from almasix.orbit.tables import Table, TextColumn

from almasix_orbit_form_builder.models import FormDefinition, new_id
from almasix_orbit_form_builder.store import get_form_store
from almasix_orbit_form_builder.tenant import current_tenant_id


class FormDefinitionResource(Resource):
    slug = "form-definitions"
    navigation_label = "Definitions"
    navigation_icon = "heroicon-o-document-text"
    navigation_group: ClassVar[str | None] = "Forms"
    navigation_sort = 5
    record_title_attribute = "title"
    model_label = "Form"
    records_mutable = True
    # Store already scopes by tenant; panel list scoping uses ``==`` on ids and
    # drops rows when types differ (e.g. ``"1"`` vs ``1``).
    is_scoped_to_tenant = False
    refresh_records_on_mount = True
    records: ClassVar[list[dict[str, Any]]] = []

    @classmethod
    def builder_url(cls, record: Any = None) -> str:
        """Visual designer URL, including the panel/tenant prefix."""
        from almasix_orbit_form_builder.pages.designer import FormDesignerPage

        prefix = str(FormDesignerPage.get_url_path_prefix() or cls.get_url_path_prefix() or "")
        root = prefix.rstrip("/")
        base = f"{root}/form-builder" if root else "/form-builder"
        rid = ""
        if isinstance(record, dict):
            rid = str(record.get("id") or "")
        elif record is not None:
            rid = str(getattr(record, "id", "") or "")
        if rid:
            return f"{base}?form={rid}"
        return base

    @classmethod
    def after_create_url(cls, record: Any = None) -> str:
        return cls.builder_url(record)

    @classmethod
    def get_records(cls) -> list[dict[str, Any]]:
        rows = []
        for form in get_form_store().list_definitions():
            row = form.to_dict()
            definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
            cols = definition.get("columns", 2)
            row["columns"] = cols if isinstance(cols, int) else 2
            rows.append(row)
        cls.records = rows
        return list(rows)

    @classmethod
    def form(cls, form: Form) -> Form:
        return form.schema(
            [
                TextInput.make("title").required(),
                TextInput.make("slug").required(),
                Select.make("status")
                .options({"draft": "Draft", "published": "Published"})
                .default("draft"),
                TextInput.make("columns")
                .label("Form columns")
                .numeric()
                .default(2)
                .helper_text("How root-level fields are arranged on the canvas. Default is 2."),
                Placeholder.make("builder_hint").content(
                    "Edit the component tree on the Form builder page. "
                    "Definition JSON below is a readonly snapshot."
                ),
                Textarea.make("definition_json")
                .rows(12)
                .disabled()
                .helper_text("Readonly export of the stored definition."),
                Textarea.make("settings_json")
                .rows(6)
                .label("Settings JSON")
                .disabled()
                .helper_text("Readonly export of handlers / settings."),
            ]
        )

    @classmethod
    def table(cls, table: Table) -> Table:
        return (
            table.columns(
                [
                    TextColumn.make("title").searchable().sortable(),
                    TextColumn.make("slug").searchable(),
                    TextColumn.make("status").badge(),
                    TextColumn.make("columns").label("Columns"),
                ]
            )
            .actions(
                [
                    ViewAction.make().url(lambda record=None, **_: cls.page_url("view", record)),
                    EditAction.make()
                    .label("Edit in builder")
                    .url(lambda record=None, **_: cls.builder_url(record)),
                    DeleteAction.make(),
                ]
            )
            .record_url(lambda record=None, **_: cls.builder_url(record))
        )

    @classmethod
    def mutate_form_data_before_fill(cls, data: dict[str, Any]) -> dict[str, Any]:
        out = dict(data)
        definition = out.get("definition")
        settings = out.get("settings")
        if isinstance(definition, dict):
            out["definition_json"] = json.dumps(definition, indent=2)
            cols = definition.get("columns", 2)
            out["columns"] = cols if isinstance(cols, int) else 2
        elif "definition_json" not in out:
            out["definition_json"] = json.dumps({"components": [], "columns": 2}, indent=2)
            out.setdefault("columns", 2)
        if isinstance(settings, dict):
            out["settings_json"] = json.dumps(settings, indent=2)
        elif "settings_json" not in out:
            out["settings_json"] = "{}"
        return out

    @classmethod
    def mutate_form_data_before_create(cls, data: dict[str, Any]) -> dict[str, Any]:
        return cls._coerce(data, creating=True)

    @classmethod
    def mutate_form_data_before_save(cls, data: dict[str, Any]) -> dict[str, Any]:
        return cls._coerce(data, creating=False)

    @classmethod
    def _coerce(cls, data: dict[str, Any], *, creating: bool) -> dict[str, Any]:
        store = get_form_store()
        form_id = str(data.get("id") or "")
        existing = store.get_definition(form_id) if form_id else None

        definition: dict[str, Any]
        settings: dict[str, Any]
        if existing is not None and not creating:
            # Preserve stored trees — resource form JSON is readonly.
            definition = (
                existing.definition if isinstance(existing.definition, dict) else {"components": []}
            )
            settings = existing.settings if isinstance(existing.settings, dict) else {}
        else:
            definition = {"components": [], "columns": 2}
            settings = {"handlers": [{"type": "store"}]}
            if isinstance(data.get("definition"), dict) and data["definition"]:
                definition = dict(data["definition"])
            if isinstance(data.get("settings"), dict) and data["settings"]:
                settings = data["settings"]

        try:
            cols = int(
                data.get("columns")
                if data.get("columns") not in (None, "")
                else definition.get("columns") or 2
            )
        except (TypeError, ValueError):
            cols = 2
        cols = max(1, min(12, cols))
        if not isinstance(definition, dict):
            definition = {"components": []}
        definition = {**definition, "columns": cols}
        if not isinstance(definition.get("components"), list):
            definition["components"] = []

        form = FormDefinition(
            id=form_id or new_id(),
            slug=str(data.get("slug") or (existing.slug if existing else "untitled")),
            title=str(data.get("title") or (existing.title if existing else "Untitled")),
            status=str(data.get("status") or (existing.status if existing else "draft")),
            definition=definition,
            settings=settings,
            tenant_id=current_tenant_id(),
        )
        # Slug uniqueness
        clash = store.get_definition_by_slug(form.slug)
        if clash is not None and clash.id != form.id:
            form.slug = f"{form.slug}-{form.id[:8]}"
        store.save_definition(form)
        return form.to_dict()

    @classmethod
    def delete_record(cls, record_id: str) -> None:
        get_form_store().delete_definition(str(record_id or ""))
