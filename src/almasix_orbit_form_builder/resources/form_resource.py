"""Resource listing form definitions from the plugin store."""

from __future__ import annotations

from typing import Any, ClassVar

from almasix.orbit.forms import Form, Select, Textarea, TextInput
from almasix.orbit.panels.resource import Resource
from almasix.orbit.tables import Table, TextColumn

from almasix_orbit_form_builder.models import FormDefinition
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
    records: ClassVar[list[dict[str, Any]]] = []

    @classmethod
    def get_records(cls) -> list[dict[str, Any]]:
        rows = [f.to_dict() for f in get_form_store().list_definitions()]
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
                Textarea.make("definition_json")
                .rows(12)
                .helper_text("JSON definition (prefer the Form builder page for editing)."),
                Textarea.make("settings_json").rows(6).label("Settings JSON"),
            ]
        )

    @classmethod
    def table(cls, table: Table) -> Table:
        return table.columns(
            [
                TextColumn.make("title").searchable().sortable(),
                TextColumn.make("slug").searchable(),
                TextColumn.make("status").badge(),
            ]
        )

    @classmethod
    def mutate_form_data_before_create(cls, data: dict[str, Any]) -> dict[str, Any]:
        return cls._coerce(data)

    @classmethod
    def mutate_form_data_before_save(cls, data: dict[str, Any]) -> dict[str, Any]:
        return cls._coerce(data)

    @classmethod
    def _coerce(cls, data: dict[str, Any]) -> dict[str, Any]:
        import json

        definition = data.get("definition") or {}
        settings = data.get("settings") or {}
        if "definition_json" in data:
            try:
                definition = json.loads(data.pop("definition_json") or "{}")
            except json.JSONDecodeError:
                definition = {"components": []}
        if "settings_json" in data:
            try:
                settings = json.loads(data.pop("settings_json") or "{}")
            except json.JSONDecodeError:
                settings = {}
        form = FormDefinition(
            id=str(data.get("id") or ""),
            slug=str(data.get("slug") or "untitled"),
            title=str(data.get("title") or "Untitled"),
            status=str(data.get("status") or "draft"),
            definition=definition if isinstance(definition, dict) else {"components": []},
            settings=settings if isinstance(settings, dict) else {},
            tenant_id=current_tenant_id(),
        )
        if not form.id:
            from almasix_orbit_form_builder.models import new_id

            form.id = new_id()
        get_form_store().save_definition(form)
        return form.to_dict()
