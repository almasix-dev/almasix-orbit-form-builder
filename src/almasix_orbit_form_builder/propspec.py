"""Property questions shown in the form-builder modal, chosen per component type."""

from __future__ import annotations

from typing import Any

from almasix_orbit_form_builder.registry import COMPONENT_TYPES


def _row(
    key: str,
    kind: str,
    label: str,
    help_text: str = "",
    default: str = "",
    choices: str = "",
) -> dict[str, str]:
    return {
        "key": key,
        "kind": kind,
        "label": label,
        "help": help_text,
        "default": default,
        "choices": choices,
    }


# Identity first. Type catalogs append only the questions that belong to that component.
_IDENTITY = (
    _row("name", "text", "Name", "Key stored with the answer."),
    _row("label", "text", "Label"),
    _row("prefix_icon", "text", "Icon", "Icon shown beside the field."),
    _row("placeholder", "text", "Placeholder"),
    _row("helper_text", "text", "Helper text"),
    _row("default", "text", "Default"),
    _row("required", "bool", "Required"),
    _row("column_span", "number", "Column span", "How many form columns this item spans."),
)

_TEXT_EXTRAS = (
    _row("prefix", "text", "Prefix"),
    _row("suffix", "text", "Suffix"),
    _row("min_length", "number", "Min length"),
    _row("max_length", "number", "Max length"),
    _row("mask", "text", "Mask"),
)

_TEXTAREA_EXTRAS = (
    _row("rows", "number", "Rows"),
    _row("autosize", "bool", "Autosize"),
    _row("min_length", "number", "Min length"),
    _row("max_length", "number", "Max length"),
)

_CHOICE_EXTRAS = (
    _row(
        "options",
        "kv",
        "Options",
        "One choice per line, value: Label. Leave this empty when using a model.",
    ),
    _row(
        "relationship",
        "text",
        "Model or relationship",
        "Relationship or model name. Used instead of the options list.",
    ),
    _row("searchable", "bool", "Searchable"),
    _row("native", "bool", "Native control", default="1"),
)

_DATE_EXTRAS = (
    _row("min_date", "text", "Earliest date", "YYYY-MM-DD."),
    _row("max_date", "text", "Latest date", "YYYY-MM-DD."),
    _row("display_format", "text", "Display format"),
    _row("range", "text", "Range end field", "Name of the field that stores the end date."),
    _row("native", "bool", "Browser date input", "Off uses the calendar picker."),
)

_TIME_EXTRAS = (
    _row("time_format", "choice", "Clock", choices="12|24"),
    _row("seconds", "bool", "Show seconds"),
    _row("minute_step", "number", "Minute step"),
    _row("native", "bool", "Browser time input"),
)

_FILE_EXTRAS = (
    _row("disk", "text", "Disk"),
    _row("directory", "text", "Directory"),
    _row(
        "accepted_file_types", "csv", "Accepted types", "Comma-separated, for example image/*,.pdf."
    ),
    _row("max_size", "number", "Max size (KB)"),
    _row("min_size", "number", "Min size (KB)"),
    _row("multiple", "bool", "Multiple files"),
    _row("max_files", "number", "Max files"),
    _row("image", "bool", "Images only"),
    _row("avatar", "bool", "Avatar"),
    _row("image_preview", "bool", "Image preview"),
    _row("reorderable", "bool", "Reorderable"),
    _row("downloadable", "bool", "Downloadable"),
    _row("openable", "bool", "Openable"),
)

_TYPE_EXTRAS: dict[str, tuple[dict[str, str], ...]] = {
    "TextInput": _TEXT_EXTRAS,
    "Textarea": _TEXTAREA_EXTRAS,
    "RichEditor": (_row("max_length", "number", "Max length"),),
    "MarkdownEditor": (_row("max_length", "number", "Max length"),),
    "CodeEditor": (_row("rows", "number", "Rows"),),
    "Select": _CHOICE_EXTRAS,
    "MultiSelect": _CHOICE_EXTRAS,
    "Radio": _CHOICE_EXTRAS,
    "CheckboxList": _CHOICE_EXTRAS,
    "ToggleButtons": _CHOICE_EXTRAS,
    "Checkbox": (_row("inline", "bool", "Inline"),),
    "Toggle": (_row("inline", "bool", "Inline"),),
    "DatePicker": _DATE_EXTRAS,
    "WeekPicker": _DATE_EXTRAS,
    "MonthPicker": _DATE_EXTRAS,
    "YearPicker": _DATE_EXTRAS,
    "DateTimePicker": _DATE_EXTRAS + _TIME_EXTRAS,
    "TimePicker": _TIME_EXTRAS,
    "FileUpload": _FILE_EXTRAS,
    "ColorPicker": (),
    "MoneyInput": (_row("prefix", "text", "Prefix"), _row("suffix", "text", "Suffix")),
    "Slider": (
        _row("min_value", "number", "Minimum"),
        _row("max_value", "number", "Maximum"),
        _row("step", "number", "Step"),
    ),
    "Grid": (
        _row("columns", "number", "Columns", default="2"),
        _row("dense", "bool", "Dense"),
    ),
    "Group": (
        _row("columns", "number", "Columns", default="2"),
        _row("dense", "bool", "Dense"),
    ),
    "Section": (
        _row("heading", "text", "Heading"),
        _row("icon", "text", "Icon"),
        _row("description", "text", "Description"),
        _row("collapsible", "bool", "Collapsible"),
        _row("collapsed", "bool", "Collapsed"),
        _row("dense", "bool", "Dense"),
    ),
    "Fieldset": (_row("dense", "bool", "Dense"),),
    "Flex": (_row("grow", "bool", "Grow"),),
    "Callout": (
        _row("heading", "text", "Heading"),
        _row("icon", "text", "Icon"),
        _row("description", "text", "Description"),
    ),
    "EmptyState": (
        _row("heading", "text", "Heading"),
        _row("icon", "text", "Icon"),
        _row("description", "text", "Description"),
    ),
    "Text": (
        _row("heading", "text", "Heading"),
        _row("icon", "text", "Icon"),
    ),
    "Placeholder": (_row("content", "text", "Content"),),
}

_LAYOUTS = frozenset(
    {
        "Grid",
        "Group",
        "Section",
        "Fieldset",
        "Flex",
        "Split",
        "Tabs",
        "Wizard",
        "Callout",
        "EmptyState",
        "Text",
        "Icon",
        "Image",
        "UnorderedList",
    }
)
_IDENTITY_SKIP = {
    "Hidden": frozenset(
        {"label", "prefix_icon", "placeholder", "helper_text", "default", "required", "column_span"}
    ),
    "Placeholder": frozenset({"prefix_icon", "placeholder", "helper_text", "default", "required"}),
}


def props_for(type_name: str) -> list[dict[str, str]]:
    """Curated property questions for one component type, important fields first."""
    if type_name == "_Tab":
        return [_row("label", "text", "Label")]
    if type_name == "_Step":
        return [
            _row("label", "text", "Label"),
            _row("description", "text", "Description"),
        ]
    if type_name not in COMPONENT_TYPES and type_name not in _TYPE_EXTRAS:
        return [_row("name", "text", "Name"), _row("label", "text", "Label")]

    skip = set(_IDENTITY_SKIP.get(type_name, ()))
    if type_name in _LAYOUTS:
        skip |= {"placeholder", "helper_text", "default", "required", "prefix_icon"}
        if type_name not in {"Grid", "Group", "Fieldset", "Flex", "Split"}:
            skip.add("name")
    rows = [row for row in _IDENTITY if row["key"] not in skip]
    rows.extend(_TYPE_EXTRAS.get(type_name, ()))
    return rows


def display_value(node: dict[str, Any], key: str, kind: str) -> Any:
    raw = node.get(key)
    if kind == "bool":
        return bool(raw)
    if raw is None:
        return ""
    if kind == "csv" and isinstance(raw, list):
        return ", ".join(str(v) for v in raw)
    if kind == "json" and isinstance(raw, (dict, list)):
        import json

        return json.dumps(raw, indent=2)
    if kind == "kv" and isinstance(raw, dict):
        return "\n".join(f"{key}: {value}" for key, value in raw.items())
    return raw


def coerce_value(kind: str, raw: Any) -> Any:
    if kind == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in {"1", "true", "yes", "on"}
    if raw is None:
        return None
    if kind == "number":
        text = str(raw).strip()
        if text == "":
            return None
        try:
            return int(text) if "." not in text else float(text)
        except ValueError:
            return None
    if kind == "csv":
        if isinstance(raw, list):
            return raw or None
        parts = [part.strip() for part in str(raw).split(",") if part.strip()]
        return parts or None
    if kind == "kv":
        if isinstance(raw, dict):
            return raw or None
        pairs: dict[str, str] = {}
        for line in str(raw).splitlines():
            text = line.strip()
            if not text:
                continue
            if ":" in text:
                key, value = text.split(":", 1)
            elif "=" in text:
                key, value = text.split("=", 1)
            else:
                key, value = text, text
            key = key.strip()
            if key:
                pairs[key] = value.strip()
        return pairs or None
    if kind == "choice":
        text = str(raw).strip()
        return text or None
    if kind == "json":
        if isinstance(raw, (dict, list)):
            return raw or None
        text = str(raw).strip()
        if not text:
            return None
        import json

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text
        return parsed
    text = raw if not isinstance(raw, str) else raw.strip()
    if text == "":
        return None
    return raw
