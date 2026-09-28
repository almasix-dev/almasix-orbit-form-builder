"""Serialize Orbit components into a JSON-safe form builder definition."""

from __future__ import annotations

from typing import Any

from almasix.orbit.forms.form import Form
from almasix.orbit.support.component import Component


def _clean(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_clean(v) for v in value if _is_ok(v)]
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items() if _is_ok(v)}
    return None


def _is_ok(value: Any) -> bool:
    if value is None or callable(value):
        return False
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_is_ok(v) or v is None for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and (_is_ok(v) or v is None) for k, v in value.items())
    return False


def _attr(component: Any, *names: str) -> Any:
    for name in names:
        if hasattr(component, name):
            return getattr(component, name)
    return None


def serialize_component(component: Component) -> dict[str, Any]:
    raw = component.to_dict()
    node: dict[str, Any] = {"type": type(component).__name__}
    name = raw.get("name")
    if name:
        node["name"] = name

    for key, value in raw.items():
        if key in {"type", "name", "schema", "components", "relationship", "tabs", "steps"}:
            continue
        cleaned = _clean(value)
        if cleaned is None or cleaned == {} or cleaned == []:
            continue
        node[key] = cleaned

    # Layout props often missing from thin to_dict() dumps.
    columns = _attr(component, "_columns")
    if isinstance(columns, int) and "columns" not in node:
        node["columns"] = columns
    heading = _attr(component, "_heading")
    if isinstance(heading, str) and heading and "heading" not in node:
        node["heading"] = heading
    description = _attr(component, "_description")
    if isinstance(description, str) and description and "description" not in node:
        node["description"] = description
    column_span = _attr(component, "_column_span")
    if isinstance(column_span, int) and "column_span" not in node:
        node["column_span"] = column_span

    schema = getattr(component, "_schema", None)
    if isinstance(schema, list) and schema:
        node["schema"] = [serialize_component(c) for c in schema]

    blocks = getattr(component, "_blocks", None)
    if isinstance(blocks, list) and blocks:
        node["blocks"] = [serialize_component(b) for b in blocks]

    tabs = getattr(component, "_tabs", None)
    if isinstance(tabs, list) and tabs:
        dumped: list[dict[str, Any]] = []
        for tab in tabs:
            if isinstance(tab, tuple) and len(tab) >= 2:
                label, comps = tab[0], tab[1]
                dumped.append(
                    {
                        "label": str(label),
                        "schema": [
                            serialize_component(c) for c in comps if isinstance(c, Component)
                        ],
                    }
                )
            elif isinstance(tab, dict):
                dumped.append(
                    {
                        "label": str(tab.get("label") or "Tab"),
                        "schema": [
                            serialize_component(c)
                            for c in (tab.get("schema") or [])
                            if isinstance(c, Component)
                        ],
                    }
                )
        if dumped:
            node["tabs"] = dumped

    steps = getattr(component, "_steps", None)
    if isinstance(steps, list) and steps:
        dumped_steps: list[dict[str, Any]] = []
        for step in steps:
            if isinstance(step, tuple) and len(step) >= 2:
                label, comps = step[0], step[1]
                entry: dict[str, Any] = {
                    "label": str(label),
                    "schema": [serialize_component(c) for c in comps if isinstance(c, Component)],
                }
                if len(step) > 2 and step[2]:
                    entry["description"] = str(step[2])
                dumped_steps.append(entry)
            elif isinstance(step, dict):
                dumped_steps.append(
                    {
                        "label": str(step.get("label") or "Step"),
                        "schema": [
                            serialize_component(c)
                            for c in (step.get("schema") or [])
                            if isinstance(c, Component)
                        ],
                    }
                )
        if dumped_steps:
            node["steps"] = dumped_steps

    return node


def serialize_form(form: Form) -> dict[str, Any]:
    components = list(getattr(form, "_schema", None) or form.get_components())
    out: dict[str, Any] = {
        "components": [serialize_component(c) for c in components],
    }
    columns = getattr(form, "_columns", None)
    if isinstance(columns, int):
        out["columns"] = columns
    return out
