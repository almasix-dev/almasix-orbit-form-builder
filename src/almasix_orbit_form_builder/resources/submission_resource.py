"""Resource listing form submissions."""

from __future__ import annotations

from typing import Any, ClassVar

from almasix.orbit.forms import Form, Textarea, TextInput
from almasix.orbit.panels.resource import Resource
from almasix.orbit.tables import Table, TextColumn

from almasix_orbit_form_builder.store import get_form_store


class FormSubmissionResource(Resource):
    slug = "form-submissions"
    navigation_label = "Submissions"
    navigation_icon = "heroicon-o-inbox"
    navigation_group: ClassVar[str | None] = "Forms"
    navigation_sort = 20
    record_title_attribute = "id"
    model_label = "Submission"
    records_mutable = False
    records: ClassVar[list[dict[str, Any]]] = []

    @classmethod
    def get_records(cls) -> list[dict[str, Any]]:
        rows = [s.to_dict() for s in get_form_store().list_submissions()]
        # Flatten payload for table glance
        for row in rows:
            payload = row.get("payload") or {}
            if isinstance(payload, dict):
                row["summary"] = ", ".join(f"{k}={v}" for k, v in list(payload.items())[:4])
            else:
                row["summary"] = str(payload)
        cls.records = rows
        return list(rows)

    @classmethod
    def form(cls, form: Form) -> Form:
        return form.schema(
            [
                TextInput.make("form_id").disabled(),
                Textarea.make("payload_json").rows(12).disabled(),
            ]
        )

    @classmethod
    def table(cls, table: Table) -> Table:
        return table.columns(
            [
                TextColumn.make("id").label("ID"),
                TextColumn.make("form_id").label("Form"),
                TextColumn.make("summary").label("Answers"),
                TextColumn.make("created_at").label("Received"),
            ]
        )
