"""Extra tree path error and container coverage."""

from __future__ import annotations

import pytest

from almasix_orbit_form_builder.tree import (
    default_node,
    delete_node,
    empty_definition,
    ensure_definition,
    get_node,
    insert_node,
    is_container,
    list_at,
    move_node,
    resolve_insert_list_path,
    update_node,
    walk_tree,
)


def test_delete_empty_and_invalid_paths() -> None:
    d = empty_definition()
    d, _ = insert_node(d, "", default_node("TextInput", index_hint=0))
    with pytest.raises(ValueError, match="empty path"):
        delete_node(d, "")
    with pytest.raises(ValueError, match="Cannot delete"):
        delete_node(d, "schema")
    with pytest.raises(ValueError, match="Cannot delete"):
        delete_node(d, "99")


def test_move_into_descendant_raises() -> None:
    d = empty_definition()
    d, section = insert_node(d, "", default_node("Section", index_hint=0))
    d, grid = insert_node(d, section, default_node("Grid", index_hint=0))
    # Moving a container into its own nested list is rejected.
    with pytest.raises(ValueError, match="itself|descendant"):
        move_node(d, section, f"{section}.schema", 0)
    with pytest.raises(ValueError, match="itself|descendant"):
        move_node(d, section, grid, 0)


def test_wizard_defaults_walk_and_update() -> None:
    d = empty_definition()
    d, wiz = insert_node(d, "", default_node("Wizard", index_hint=0))
    node = get_node(d, wiz)
    assert node is not None
    assert node["steps"][0]["schema"] == []
    d, field = insert_node(d, wiz, default_node("TextInput", index_hint=0))
    assert field.startswith("0.steps.0.schema.")
    walked = walk_tree(d)
    types = [n.get("type") for _, n, _ in walked]
    assert "Wizard" in types
    assert "_Step" in types
    assert "TextInput" in types

    d = update_node(d, field, {"required": "yes", "columns": "x", "type": "Nope"})
    updated = get_node(d, field)
    assert updated is not None
    assert updated["required"] is True
    assert updated["columns"] == "x"
    assert updated["type"] == "TextInput"  # type updates ignored
    d = update_node(d, field, {"label": "", "heading": None})
    assert "label" not in get_node(d, field)


def test_ensure_list_path_and_resolve_edges() -> None:
    assert ensure_definition(None)["components"] == []
    assert ensure_definition({"components": "bad"})["components"] == []
    assert is_container(None) is False
    assert is_container({"type": "Section"}) is True
    assert get_node({"components": [1]}, "0") is None
    assert get_node({"components": [{"type": "X"}]}, "0.bad") is None
    assert list_at({"components": []}, "0.nope") is None

    d = empty_definition()
    d, tabs = insert_node(d, "", default_node("Tabs", index_hint=0))
    assert resolve_insert_list_path(d, f"{tabs}.tabs") == f"{tabs}.tabs.0.schema"
    assert resolve_insert_list_path(d, "missing") == ""
    d2 = empty_definition()
    d2, wiz = insert_node(d2, "", default_node("Wizard", index_hint=0))
    assert resolve_insert_list_path(d2, f"{wiz}.steps") == f"{wiz}.steps.0.schema"

    with pytest.raises(ValueError, match="Cannot move"):
        move_node(d, "99", "", 0)
    with pytest.raises(ValueError, match="Cannot update"):
        update_node(d, "99", {"label": "x"})
