"""Serialize Tabs / Wizard (tuple and dict shapes)."""

from __future__ import annotations

from almasix.orbit.forms import Form, TextInput
from almasix.orbit.schemas import Tabs, Wizard

from almasix_orbit_form_builder.serialize import serialize_component, serialize_form


def test_serialize_tabs_tuple_and_dict() -> None:
    tabs = Tabs.make().tabs(
        ("One", [TextInput.make("a").label("A")]),
        {"label": "Two", "schema": [TextInput.make("b")]},
    )
    dumped = serialize_component(tabs)
    assert dumped["type"] == "Tabs"
    assert len(dumped["tabs"]) == 2
    assert dumped["tabs"][0]["label"] == "One"
    assert dumped["tabs"][0]["schema"][0]["type"] == "TextInput"
    assert dumped["tabs"][1]["label"] == "Two"


def test_serialize_wizard_tuple_description_and_dict() -> None:
    wizard = Wizard.make()
    # Mix tuple-with-description and dict shapes that serialize_component accepts.
    wizard._steps = [
        ("Intro", [TextInput.make("title")], "Say hello"),
        {"label": "Done", "schema": [TextInput.make("ok")]},  # type: ignore[list-item]
    ]
    dumped = serialize_component(wizard)
    assert dumped["type"] == "Wizard"
    assert dumped["steps"][0]["label"] == "Intro"
    assert dumped["steps"][0]["description"] == "Say hello"
    assert dumped["steps"][0]["schema"][0]["name"] == "title"
    assert dumped["steps"][1]["label"] == "Done"

    form = Form.make("f").schema([Tabs.make().tabs(("T", [TextInput.make("x")]))])
    assert serialize_form(form)["components"][0]["type"] == "Tabs"
