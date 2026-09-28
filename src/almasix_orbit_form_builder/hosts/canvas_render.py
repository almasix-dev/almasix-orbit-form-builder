"""Visual canvas HTML for the form designer (layout-aware nodes)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from almasix.orbit.support.html import e

from almasix_orbit_form_builder.registry import CONTAINER_TYPES

AttrFn = Callable[[str, str], str]


def _span_style(node: dict[str, Any]) -> str:
    span = node.get("column_span")
    if isinstance(span, int) and span > 1:
        return f"grid-column: span {span};"
    return ""


def render_field_widget(node: dict[str, Any]) -> str:
    """Lightweight visual stand-in for a field on the canvas."""
    t = str(node.get("type") or "Field")
    label = e(str(node.get("label") or node.get("name") or t))
    req = ' <span class="or-fb-req">*</span>' if node.get("required") else ""
    ph = e(str(node.get("placeholder") or ""))
    helper = e(str(node.get("helper_text") or node.get("hint") or ""))
    name = e(str(node.get("name") or ""))

    control = ""
    if t in {"Textarea", "RichEditor", "MarkdownEditor", "CodeEditor"}:
        control = f'<textarea class="or-input" rows="3" placeholder="{ph}" disabled></textarea>'
    elif t in {"Checkbox", "Toggle"}:
        control = (
            f'<label class="or-fb-inline-check"><input type="checkbox" disabled /> {label}</label>'
        )
        label_html = f'<div class="or-fb-field-label">{e(t)}{req}</div>'
        return f"{label_html}{control}" + (
            f'<p class="or-muted or-fb-help">{helper}</p>' if helper else ""
        )
    elif t in {"Select", "MultiSelect", "Radio", "CheckboxList", "TagsInput", "ToggleButtons"}:
        control = f'<select class="or-input" disabled><option>{ph or "Select…"}</option></select>'
    elif t in {
        "DatePicker",
        "DateTimePicker",
        "TimePicker",
        "WeekPicker",
        "MonthPicker",
        "YearPicker",
    }:
        control = f'<input class="or-input" type="date" placeholder="{ph}" disabled />'
    elif t == "FileUpload":
        control = '<div class="or-fb-upload filepond--root">Drag &amp; drop files, or browse</div>'
    elif t == "Hidden":
        return f'<div class="or-fb-hidden-chip">Hidden · {name or label}</div>'
    elif t in {"Slider"}:
        control = '<input class="or-input" type="range" disabled />'
    else:
        control = f'<input class="or-input" type="text" placeholder="{ph}" disabled />'

    help_html = f'<p class="or-muted or-fb-help">{helper}</p>' if helper else ""
    return f'<div class="or-fb-field-label">{label}{req}</div>{control}{help_html}'


def render_canvas(
    definition: dict[str, Any],
    *,
    selected_path: str,
    attr: AttrFn,
) -> str:
    components = definition.get("components") or []
    if not isinstance(components, list):
        components = []
    try:
        cols = int(definition.get("columns", 2) or 2)
    except (TypeError, ValueError):
        cols = 2
    cols = max(1, min(12, cols))

    body = _render_list(components, "", selected_path, attr, grid_cols=cols)
    return (
        f'<div class="or-fb-canvas-root" data-list-path="" data-or-fb-drop="1" '
        f'style="--or-fb-cols:{cols}">'
        f'<div class="or-fb-canvas-hint or-muted">'
        f"Form grid · {cols} column{'s' if cols != 1 else ''} — drag fields here or into layouts"
        f"</div>"
        f"{body}"
        f"</div>"
    )


def _render_list(
    lst: list[Any],
    list_path: str,
    selected_path: str,
    attr: AttrFn,
    *,
    grid_cols: int | None = None,
) -> str:
    items: list[str] = []
    for i, item in enumerate(lst):
        if not isinstance(item, dict):
            continue
        path = f"{list_path}.{i}" if list_path else str(i)
        items.append(_render_node(item, path, list_path, selected_path, attr))

    style = ""
    cls = "or-fb-dropzone"
    if grid_cols:
        style = (
            f'style="--or-fb-cols:{int(grid_cols)};'
            f'display:grid;grid-template-columns:repeat({int(grid_cols)},minmax(0,1fr))"'
        )
        cls += " or-fb-dropzone-grid"

    empty = ""
    if not items:
        empty = '<div class="or-fb-empty-drop">Drop components here</div>'

    return (
        f'<ul class="{cls}" data-list-path="{e(list_path)}" data-or-fb-sortable="1" {style}>'
        f"{''.join(items)}{empty}</ul>"
    )


def _render_node(
    node: dict[str, Any],
    path: str,
    parent_list: str,
    selected_path: str,
    attr: AttrFn,
) -> str:
    t = str(node.get("type") or "?")
    selected = " is-selected" if path == selected_path else ""
    span = _span_style(node)
    style_attr = f' style="{span}"' if span else ""

    toolbar = (
        f'<div class="or-fb-node-chrome">'
        f'<span class="or-fb-handle" title="Drag">⠿</span>'
        f'<span class="or-fb-type-badge">{e(t)}</span>'
        f'<button type="button" class="or-btn or-btn-sm" {attr("click", f"open_inspector({path!r})")}>'
        f"Edit</button>"
        f'<button type="button" class="or-btn or-btn-sm or-fb-del" '
        f"{attr('click', f'delete_path({path!r})')}>Delete</button>"
        f"</div>"
    )

    inner = ""
    if t in CONTAINER_TYPES - {"Tabs", "Wizard"}:
        cols = node.get("columns") if t in {"Grid", "Group"} else None
        if not isinstance(cols, int):
            cols = 2 if t in {"Grid", "Group"} else None
        heading = e(str(node.get("heading") or node.get("label") or t))
        desc = e(str(node.get("description") or ""))
        header = f'<div class="or-fb-layout-title">{heading}</div>'
        if desc:
            header += f'<p class="or-muted or-fb-help">{desc}</p>'
        children = node.get("schema") if isinstance(node.get("schema"), list) else []
        child_html = _render_list(children, f"{path}.schema", selected_path, attr, grid_cols=cols)
        inner = (
            f'<div class="or-fb-layout-body or-fb-layout-{e(t.lower())}">{header}{child_html}</div>'
        )
    elif t == "Tabs":
        bits: list[str] = []
        for ti, tab in enumerate(node.get("tabs") or []):
            if not isinstance(tab, dict):
                continue
            tpath = f"{path}.tabs.{ti}"
            tsel = " is-selected" if tpath == selected_path else ""
            tlabel = e(str(tab.get("label") or f"Tab {ti + 1}"))
            schema = tab.get("schema") if isinstance(tab.get("schema"), list) else []
            bits.append(
                f'<li class="or-fb-node or-fb-tab{tsel}" data-path="{e(tpath)}" '
                f'data-parent-list="{e(path + ".tabs")}">'
                f'<div class="or-fb-node-chrome">'
                f'<span class="or-fb-handle">⠿</span>'
                f"<strong>{tlabel}</strong>"
                f'<button type="button" class="or-btn or-btn-sm" '
                f"{attr('click', f'open_inspector({tpath!r})')}>Edit</button>"
                f'<button type="button" class="or-btn or-btn-sm" '
                f"{attr('click', f'delete_path({tpath!r})')}>Delete</button>"
                f"</div>"
                f"{_render_list(schema, tpath + '.schema', selected_path, attr)}"
                f"</li>"
            )
        inner = (
            f'<ul class="or-fb-dropzone or-fb-tabs" data-list-path="{e(path + ".tabs")}" '
            f'data-or-fb-sortable="1">{"".join(bits)}</ul>'
        )
    elif t == "Wizard":
        bits = []
        for si, step in enumerate(node.get("steps") or []):
            if not isinstance(step, dict):
                continue
            spath = f"{path}.steps.{si}"
            ssel = " is-selected" if spath == selected_path else ""
            slabel = e(str(step.get("label") or f"Step {si + 1}"))
            schema = step.get("schema") if isinstance(step.get("schema"), list) else []
            bits.append(
                f'<li class="or-fb-node or-fb-step{ssel}" data-path="{e(spath)}" '
                f'data-parent-list="{e(path + ".steps")}">'
                f'<div class="or-fb-node-chrome">'
                f'<span class="or-fb-handle">⠿</span>'
                f"<strong>{slabel}</strong>"
                f'<button type="button" class="or-btn or-btn-sm" '
                f"{attr('click', f'open_inspector({spath!r})')}>Edit</button>"
                f'<button type="button" class="or-btn or-btn-sm" '
                f"{attr('click', f'delete_path({spath!r})')}>Delete</button>"
                f"</div>"
                f"{_render_list(schema, spath + '.schema', selected_path, attr)}"
                f"</li>"
            )
        inner = (
            f'<ul class="or-fb-dropzone or-fb-steps" data-list-path="{e(path + ".steps")}" '
            f'data-or-fb-sortable="1">{"".join(bits)}</ul>'
        )
    else:
        inner = f'<div class="or-fb-widget">{render_field_widget(node)}</div>'

    # Click body opens inspector; chrome buttons are separate.
    open_click = attr("click", f"open_inspector({path!r})")
    return (
        f'<li class="or-fb-node{selected}" data-path="{e(path)}" '
        f'data-parent-list="{e(parent_list)}"{style_attr}>'
        f'<div class="or-fb-card">'
        f"{toolbar}"
        f'<div class="or-fb-card-body" {open_click}>{inner}</div>'
        f"</div></li>"
    )
