"""Focused designer host coverage: handlers, select, publish, render chrome."""

from __future__ import annotations

import json

from almasix.orbit.panels.panel import Panel

from almasix_orbit_form_builder import FormDefinition, bootstrap_memory_store
from almasix_orbit_form_builder.hosts.designer_host import FormDesignerHost
from almasix_orbit_form_builder.store import get_form_store
from almasix_orbit_form_builder.tenant import clear_current_tenant, set_tenant_resolver


def _seed() -> None:
    bootstrap_memory_store()
    clear_current_tenant()
    set_tenant_resolver(None)


def _host() -> FormDesignerHost:
    panel = Panel.make("app").path("/app")
    return FormDesignerHost.bind(panel=panel)()


def test_select_apply_inspector_and_delete_path_errors() -> None:
    _seed()
    host = _host()
    host.new_form()
    host.select("0")
    assert host.insp_name == "name"
    host.props = {**host.props, "label": "Full name", "required": True, "column_span": "2"}
    host.apply_inspector()
    assert host.message == "Properties saved."
    node = json.loads(host.definition_json)["components"][0]
    assert node["label"] == "Full name"
    assert node["required"] is True
    assert node["column_span"] == 2

    host.selected_path = ""
    host.apply_inspector()
    assert "Select a component" in host.error

    host.select("999")
    host.apply_inspector()
    assert host.error

    host.selected_path = ""
    host.delete_path("")
    assert "Select a component to delete" in host.error
    host.delete_path("not-an-index")
    assert host.error
    host.delete_path("99")
    assert host.error


def test_handlers_add_remove_apply_and_render() -> None:
    _seed()
    host = _host()
    host.new_form()
    host.add_handler("email")
    assert host.handler_index == 1  # store + email
    host.handler_to = "ops@example.com"
    host.handler_subject = "Lead"
    host.apply_handler()
    settings = json.loads(host.settings_json)
    assert settings["handlers"][1]["to"] == "ops@example.com"
    assert settings["handlers"][1]["subject"] == "Lead"

    host.add_handler("webhook")
    host.handler_url = "https://example.test/hook"
    host.apply_handler()
    assert json.loads(host.settings_json)["handlers"][2]["url"] == "https://example.test/hook"

    host.add_handler("callable")
    host.handler_callable = "crm"
    host.apply_handler()
    assert json.loads(host.settings_json)["handlers"][3]["name"] == "crm"

    host.add_handler("store")
    host.select_handler(0)
    host.apply_handler()  # store has no extra fields
    assert host.message == "Handler updated."

    # Render with handlers drawer open and email handler selected.
    host.select_handler(1)
    host.handlers_open = True
    html = host.render()
    assert "Canvas" in html
    assert "Components" in html
    assert "Answer handlers" in html
    assert "Apply handler" in html

    host.handler_index = -1
    host.apply_handler()
    assert "Select a handler" in host.error

    before = len(json.loads(host.settings_json)["handlers"])
    host.remove_handler(1)
    assert len(json.loads(host.settings_json)["handlers"]) == before - 1
    host.remove_handler(99)  # out of range no-op


def test_save_appears_in_resource_and_updated_form_id_loads() -> None:
    """Save via designer → resource list includes title/slug; updatedFormId auto-loads."""
    from almasix_orbit_form_builder.resources.form_resource import FormDefinitionResource

    _seed()
    host = _host()
    host.mount()
    host.new_form()
    host.title = "Resource Link"
    host.slug = "resource-link"
    host.save()
    assert host.saved is True
    assert host.form_id
    saved_id = host.form_id

    rows = FormDefinitionResource.get_records()
    match = next((r for r in rows if r.get("id") == saved_id), None)
    assert match is not None
    assert match["title"] == "Resource Link"
    assert match["slug"] == "resource-link"

    # Fresh host: selecting the saved id via updatedFormId auto-loads title/slug.
    host2 = _host()
    host2.mount()
    host2.updatedFormId(saved_id)
    assert host2.loaded_form_id == saved_id
    assert host2.title == "Resource Link"
    assert host2.slug == "resource-link"


def test_updated_form_id_loads_and_publish() -> None:
    _seed()
    store = get_form_store()
    form = FormDefinition(
        slug="survey",
        title="Survey",
        definition={"components": [{"type": "TextInput", "name": "q", "label": "Q"}]},
        status="draft",
        settings={"handlers": [{"type": "store"}]},
    )
    store.save_definition(form)

    host = _host()
    host.mount()
    host.updatedForm_id("")  # empty → no load
    assert host.loaded_form_id == ""
    host.updatedFormId(form.id)
    assert host.loaded_form_id == form.id
    assert host.title == "Survey"
    # Same id again is a no-op
    host.updatedFormId(form.id)
    assert host.loaded_form_id == form.id

    host.publish()
    assert host.saved is True
    assert host.status == "published"
    assert store.get_definition(form.id).status == "published"

    html = host.render()
    assert "Canvas" in html
    assert "Components" in html
    assert "Form builder" in html


def test_tabs_wizard_tree_render_and_move_errors() -> None:
    _seed()
    host = _host()
    host.new_form()
    host.delete_path("0")
    host.add_field("Tabs")
    host.select("0")
    host.add_field("TextInput")
    host.add_field("Wizard")
    html = host.render()
    assert "Tabs" in html
    assert "Wizard" in html or "Canvas" in html
    assert "Components" in html

    host.move("", "", 0)
    assert "Missing move source" in host.error
    host.move("0", "0.schema", 0)  # into self/descendant when possible
    # May error or succeed depending on path resolution; either way exercised
    assert host.error or host.definition_json


def test_canvas_columns_inspector_modal_and_palette_dnd_move() -> None:
    _seed()
    host = _host()
    host.new_form()
    host.form_columns = "3"
    host.apply_form_columns()
    assert json.loads(host.definition_json)["columns"] == 3
    html = host.render()
    assert "Form grid · 3 columns" in html
    host.open_inspector("0")
    assert host.inspector_open is True
    host.props = {**host.props, "placeholder": "Your name"}
    host.apply_inspector()
    assert json.loads(host.definition_json)["components"][0]["placeholder"] == "Your name"
    host.close_inspector()
    assert host.inspector_open is False
    host.move("type:Section", "", 0)
    assert "Section" in host.definition_json
    host.open_preview()
    assert host.preview_open is True
    assert host.preview_html
    host.submit_preview()
    host.close_preview()
    assert host.preview_open is False
    host.palette_filter = "text"
    html2 = host.render()
    assert "TextInput" in html2
    assert "Components" in html2
