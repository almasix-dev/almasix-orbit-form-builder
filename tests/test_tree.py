"""Unit tests for definition tree path helpers."""

from __future__ import annotations

from almasix_orbit_form_builder.tree import (
    default_node,
    delete_node,
    empty_definition,
    get_node,
    insert_node,
    move_node,
    update_node,
    walk_tree,
)


def test_insert_nest_delete_and_move() -> None:
    d = empty_definition()
    d, section = insert_node(d, "", default_node("Section", index_hint=0))
    assert section == "0"
    d, grid = insert_node(d, section, default_node("Grid", index_hint=0))
    assert grid == "0.schema.0"
    assert get_node(d, grid)["columns"] == 2
    d, a = insert_node(d, grid, default_node("TextInput", index_hint=0))
    d, b = insert_node(d, grid, default_node("TextInput", index_hint=1))
    assert a == "0.schema.0.schema.0"
    assert b == "0.schema.0.schema.1"
    types = [n.get("type") for _, n, _ in walk_tree(d)]
    assert types == ["Section", "Grid", "TextInput", "TextInput"]
    d = delete_node(d, b)
    assert get_node(d, b) is None
    d, ta = insert_node(d, grid, default_node("Textarea", index_hint=2))
    d = move_node(d, ta, "", 0)
    assert walk_tree(d)[0][1]["type"] == "Textarea"
    # Moving a child to root shifts the Section (and Grid) index from 0 → 1.
    grid_after = "1.schema.0"
    assert get_node(d, grid) is None
    d = update_node(d, grid_after, {"columns": 3, "heading": ""})
    assert get_node(d, grid_after)["columns"] == 3


def test_tabs_default_and_nested_insert() -> None:
    d = empty_definition()
    d, tabs = insert_node(d, "", default_node("Tabs", index_hint=0))
    node = get_node(d, tabs)
    assert node is not None
    assert node["tabs"][0]["schema"] == []
    d, field = insert_node(d, tabs, default_node("Checkbox", index_hint=0))
    assert field.startswith("0.tabs.0.schema.")
    assert get_node(d, field)["type"] == "Checkbox"
