"""Hydrate a stored JSON definition into a live Orbit Form / component tree."""

from __future__ import annotations

from typing import Any

from almasix.orbit.forms.form import Form

from almasix_orbit_form_builder.registry import resolve_type

# Props applied via zero-arg fluent methods when the stored value is True.
_FLAG_METHODS = frozenset(
    {
        "required",
        "readonly",
        "disabled",
        "hidden",
        "live",
        "dehydrated",
        "searchable",
        "multiple",
        "native",
        "autosize",
        "revealable",
        "copyable",
        "reorderable",
        "addable",
        "deletable",
        "cloneable",
        "collapsible",
        "collapsed",
        "compact",
        "aside",
        "secondary",
        "contained",
        "skippable",
        "linear",
        "non_linear",
        "vertical",
        "inline",
        "boolean",
        "preload",
        "wrap",
        "downloadable",
        "openable",
        "previewable",
        "image",
        "avatar",
        "bulk_toggleable",
        "editable_keys",
        "markdown",
        "html",
        "badge",
        "dense",
        "grow",
        "hidden_label",
        "inline_label",
        "autofocus",
        "seconds",
        "hours12",
        "hours24",
    }
)

# Keys that are structural, not fluent setters.
_STRUCTURAL = frozenset(
    {
        "type",
        "name",
        "schema",
        "components",
        "tabs",
        "steps",
        "blocks",
        "rules",
        "handler",
        "handlers",
    }
)

# Skip non-serializable / internal dump keys from Component.to_dict().
_SKIP = frozenset({"relationship"}) | _STRUCTURAL


def _is_plain(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_is_plain(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_plain(v) for k, v in value.items())
    return False


def _apply_prop(component: Any, key: str, value: Any) -> None:
    if key in _SKIP or value is None:
        return
    method = getattr(component, key, None)
    if not callable(method):
        return
    if key in _FLAG_METHODS:
        if value is True:
            method()
        elif value is False and hasattr(component, f"not_{key}"):
            getattr(component, f"not_{key}")()
        return
    if not _is_plain(value):
        return
    try:
        method(value)
    except TypeError:
        # Some methods take kwargs; ignore incompatible shapes.
        return


def hydrate_component(node: dict[str, Any]) -> Any:
    """Build one Orbit component from a definition node."""
    if not isinstance(node, dict) or "type" not in node:
        raise ValueError("Component node must be a dict with a type")
    cls = resolve_type(str(node["type"]))
    name = node.get("name")
    component = cls.make(name) if name not in (None, "") else cls.make()

    for key, value in node.items():
        if key in _STRUCTURAL:
            continue
        _apply_prop(component, key, value)

    rules = node.get("rules")
    if isinstance(rules, list) and hasattr(component, "rules"):
        string_rules = [r for r in rules if isinstance(r, str)]
        if string_rules:
            component.rules(*string_rules)

    children = node.get("schema") or node.get("components")
    if isinstance(children, list) and hasattr(component, "schema"):
        component.schema([hydrate_component(c) for c in children if isinstance(c, dict)])

    blocks = node.get("blocks")
    if isinstance(blocks, list) and hasattr(component, "blocks"):
        component.blocks([hydrate_component(b) for b in blocks if isinstance(b, dict)])

    tabs = node.get("tabs")
    if isinstance(tabs, list) and hasattr(component, "tabs"):
        tab_args: list[Any] = []
        for tab in tabs:
            if not isinstance(tab, dict):
                continue
            label = tab.get("label") or tab.get("name") or "Tab"
            schema = [hydrate_component(c) for c in tab.get("schema", []) if isinstance(c, dict)]
            tab_args.append((label, schema))
        if tab_args:
            component.tabs(*tab_args)

    steps = node.get("steps")
    if isinstance(steps, list) and hasattr(component, "steps"):
        step_args: list[Any] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            label = step.get("label") or step.get("name") or "Step"
            schema = [hydrate_component(c) for c in step.get("schema", []) if isinstance(c, dict)]
            step_args.append((label, schema))
        if step_args:
            component.steps(*step_args)

    return component


def build_form(definition: dict[str, Any], *, name: str = "dynamic") -> Form:
    """Compile a stored form definition into an Orbit ``Form``."""
    form = Form.make(name)
    components = definition.get("components") or definition.get("schema") or []
    if not isinstance(components, list):
        raise ValueError("Form definition must include a components list")
    form.schema([hydrate_component(c) for c in components if isinstance(c, dict)])
    columns = definition.get("columns")
    if isinstance(columns, int) and hasattr(form, "columns"):
        form.columns(columns)
    return form
