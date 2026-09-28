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


def serialize_component(component: Component) -> dict[str, Any]:
    raw = component.to_dict()
    node: dict[str, Any] = {"type": type(component).__name__}
    name = raw.get("name")
    if name:
        node["name"] = name

    for key, value in raw.items():
        if key in {"type", "name", "schema", "components", "relationship"}:
            continue
        cleaned = _clean(value)
        if cleaned is None or cleaned == {} or cleaned == []:
            continue
        node[key] = cleaned

    schema = getattr(component, "_schema", None)
    if isinstance(schema, list) and schema:
        node["schema"] = [serialize_component(c) for c in schema]

    blocks = getattr(component, "_blocks", None)
    if isinstance(blocks, list) and blocks:
        node["blocks"] = [serialize_component(b) for b in blocks]

    tabs = getattr(component, "_tabs", None)
    if isinstance(tabs, list) and tabs:
        # Tabs store tuples; best-effort dump if present on to_dict already.
        pass

    return node


def serialize_form(form: Form) -> dict[str, Any]:
    components = list(getattr(form, "_schema", None) or form.get_components())
    return {
        "components": [serialize_component(c) for c in components],
        "columns": getattr(form, "_columns", None),
    }
