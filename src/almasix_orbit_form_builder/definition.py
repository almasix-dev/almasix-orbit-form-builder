"""Validate a form builder definition document."""

from __future__ import annotations

from typing import Any

from almasix_orbit_form_builder.registry import COMPONENT_TYPES


def validate_definition(definition: dict[str, Any]) -> list[str]:
    """Return a list of human-readable problems (empty means ok)."""
    errors: list[str] = []
    if not isinstance(definition, dict):
        return ["Definition must be an object"]
    components = definition.get("components") or definition.get("schema")
    if not isinstance(components, list):
        errors.append("Definition must include a components array")
        return errors
    if not components:
        errors.append("Add at least one field or layout")
    for index, node in enumerate(components):
        errors.extend(_validate_node(node, path=f"components[{index}]"))
    return errors


def _validate_node(node: Any, *, path: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(node, dict):
        return [f"{path} must be an object"]
    type_name = node.get("type")
    if not isinstance(type_name, str) or type_name not in COMPONENT_TYPES:
        errors.append(f"{path}.type is unknown: {type_name!r}")
        return errors
    for key in ("schema", "components", "blocks"):
        children = node.get(key)
        if children is None:
            continue
        if not isinstance(children, list):
            errors.append(f"{path}.{key} must be an array")
            continue
        for i, child in enumerate(children):
            errors.extend(_validate_node(child, path=f"{path}.{key}[{i}]"))
    for key in ("tabs", "steps"):
        items = node.get(key)
        if items is None:
            continue
        if not isinstance(items, list):
            errors.append(f"{path}.{key} must be an array")
            continue
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{path}.{key}[{i}] must be an object")
                continue
            schema = item.get("schema") or []
            if not isinstance(schema, list):
                errors.append(f"{path}.{key}[{i}].schema must be an array")
                continue
            for j, child in enumerate(schema):
                errors.extend(_validate_node(child, path=f"{path}.{key}[{i}].schema[{j}]"))
    return errors
