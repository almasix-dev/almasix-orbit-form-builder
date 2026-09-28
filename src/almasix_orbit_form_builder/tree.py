"""Path helpers for nested form-builder definition trees.

Paths use dotted segments, e.g. ``0``, ``0.schema.1``, ``2.tabs.0.schema.0``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

SCHEMA_CONTAINERS = frozenset({"Section", "Grid", "Fieldset", "Group", "Flex", "Split"})
TABS_CONTAINER = "Tabs"
WIZARD_CONTAINER = "Wizard"
ALL_CONTAINERS = SCHEMA_CONTAINERS | {TABS_CONTAINER, WIZARD_CONTAINER}
LIST_KEYS = frozenset({"schema", "tabs", "steps", "components"})


def empty_definition() -> dict[str, Any]:
    return {"components": [], "columns": 2}


def ensure_definition(definition: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(definition) if isinstance(definition, dict) else empty_definition()
    if not isinstance(data.get("components"), list):
        data["components"] = []
    if not isinstance(data.get("columns"), int) or int(data["columns"]) < 1:
        raw = data.get("columns", 2)
        try:
            data["columns"] = max(1, min(12, int(raw)))
        except (TypeError, ValueError):
            data["columns"] = 2
    return data


def parse_path(path: str | None) -> list[str]:
    raw = str(path or "").strip()
    if not raw:
        return []
    return [p for p in raw.split(".") if p != ""]


def join_path(parts: list[Any]) -> str:
    return ".".join(str(p) for p in parts if str(p) != "")


def default_node(type_name: str, *, index_hint: int = 0) -> dict[str, Any]:
    """Create a new definition node with sensible layout defaults."""
    base = type_name[0].lower() + type_name[1:] if type_name else "field"
    name = f"{base}_{max(index_hint, 0) + 1}"
    node: dict[str, Any] = {"type": type_name, "name": name, "label": type_name}
    if type_name in SCHEMA_CONTAINERS:
        node["schema"] = []
        if type_name == "Section":
            node["heading"] = "Section"
        if type_name in {"Grid", "Group"}:
            node["columns"] = 2
    elif type_name == TABS_CONTAINER:
        node.pop("name", None)
        node["tabs"] = [{"label": "Tab 1", "schema": []}]
    elif type_name == WIZARD_CONTAINER:
        node.pop("name", None)
        node["steps"] = [{"label": "Step 1", "schema": []}]
    elif type_name in {"Callout", "EmptyState", "Text"}:
        node["heading"] = type_name
    return node


def root_components(definition: dict[str, Any]) -> list[Any]:
    return list(ensure_definition(definition)["components"])


def is_container(node: dict[str, Any] | None) -> bool:
    if not isinstance(node, dict):
        return False
    return str(node.get("type") or "") in ALL_CONTAINERS


def get_node(definition: dict[str, Any], path: str | None) -> dict[str, Any] | None:
    parts = parse_path(path)
    if not parts:
        return None
    cursor: Any = ensure_definition(definition)["components"]
    node: dict[str, Any] | None = None
    for part in parts:
        if part in LIST_KEYS:
            if not isinstance(node, dict):
                return None
            cursor = node.get(part)
            if not isinstance(cursor, list):
                return None
            continue
        try:
            idx = int(part)
        except ValueError:
            return None
        if not isinstance(cursor, list) or idx < 0 or idx >= len(cursor):
            return None
        item = cursor[idx]
        if not isinstance(item, dict):
            return None
        node = item
    return node


def list_at(definition: dict[str, Any], list_path: str | None) -> list[Any] | None:
    """Return a mutable child list.

    ``list_path`` empty → root components.
    Ends with ``schema`` / ``tabs`` / ``steps`` → that list on the parent node.
    """
    data = ensure_definition(definition)
    parts = parse_path(list_path)
    if not parts:
        comps = data.setdefault("components", [])
        return comps if isinstance(comps, list) else None
    if parts[-1] not in {"schema", "tabs", "steps"}:
        return None
    parent = get_node(data, join_path(parts[:-1]))
    if parent is None:
        return None
    key = parts[-1]
    lst = parent.setdefault(key, [])
    if not isinstance(lst, list):
        return None
    return lst


def resolve_insert_list_path(definition: dict[str, Any], selected_or_parent: str | None) -> str:
    """Normalize a selection/parent into a list path suitable for ``list_at``."""
    path = selected_or_parent or ""
    parts = parse_path(path)
    if not parts:
        return ""
    if parts[-1] in {"schema", "tabs", "steps"}:
        if parts[-1] in {"tabs", "steps"}:
            # Prefer first tab/step schema for field inserts
            return join_path([*parts, 0, "schema"])
        return path
    node = get_node(definition, path)
    if node is None:
        return ""
    t = str(node.get("type") or "")
    if t in SCHEMA_CONTAINERS:
        return join_path([*parts, "schema"])
    if t == TABS_CONTAINER:
        tabs = node.get("tabs")
        if not isinstance(tabs, list) or not tabs:
            return join_path([*parts, "tabs", 0, "schema"])
        return join_path([*parts, "tabs", 0, "schema"])
    if t == WIZARD_CONTAINER:
        steps = node.get("steps")
        if not isinstance(steps, list) or not steps:
            return join_path([*parts, "steps", 0, "schema"])
        return join_path([*parts, "steps", 0, "schema"])
    if t in {"_Tab", "_Step"} or ("schema" in node and "type" not in node):
        return join_path([*parts, "schema"])
    # Leaf → sibling list (parent list path)
    if len(parts) == 1:
        return ""
    return join_path(parts[:-1])


def insert_node(
    definition: dict[str, Any],
    parent_path: str | None,
    node: dict[str, Any],
    *,
    index: int | None = None,
) -> tuple[dict[str, Any], str]:
    data = deepcopy(ensure_definition(definition))
    list_path = resolve_insert_list_path(data, parent_path)
    # Ensure intermediate tab/step exists when targeting schema under empty tabs
    _ensure_list_path(data, list_path)
    lst = list_at(data, list_path)
    if lst is None:
        raise ValueError(f"Cannot insert under {parent_path!r}")
    at = len(lst) if index is None else max(0, min(int(index), len(lst)))
    lst.insert(at, deepcopy(node))
    new_path = join_path([*parse_path(list_path), at]) if list_path else str(at)
    return data, new_path


def _ensure_list_path(definition: dict[str, Any], list_path: str) -> None:
    parts = parse_path(list_path)
    if len(parts) < 2:
        return
    # Walk creating tabs/steps containers as needed
    if "tabs" in parts or "steps" in parts:
        # Find container node path before tabs/steps
        for key in ("tabs", "steps"):
            if key not in parts:
                continue
            ki = parts.index(key)
            container_path = join_path(parts[:ki])
            container = get_node(definition, container_path)
            if container is None:
                return
            lst = container.setdefault(key, [])
            if not isinstance(lst, list):
                return
            if not lst:
                label = "Tab 1" if key == "tabs" else "Step 1"
                lst.append({"label": label, "schema": []})
            # Ensure indexed tab/step
            if ki + 1 < len(parts):
                try:
                    ti = int(parts[ki + 1])
                except ValueError:
                    return
                while len(lst) <= ti:
                    label = f"{'Tab' if key == 'tabs' else 'Step'} {len(lst) + 1}"
                    lst.append({"label": label, "schema": []})
                item = lst[ti]
                if isinstance(item, dict):
                    item.setdefault("schema", [])


def delete_node(definition: dict[str, Any], path: str | None) -> dict[str, Any]:
    data = deepcopy(ensure_definition(definition))
    parts = parse_path(path)
    if not parts:
        raise ValueError("Cannot delete empty path")
    try:
        idx = int(parts[-1])
    except ValueError as exc:
        raise ValueError(f"Cannot delete path {path!r}") from exc
    list_path = join_path(parts[:-1])
    if not list_path:
        lst: list[Any] | None = data.setdefault("components", [])
    else:
        lst = list_at(data, list_path)
    if lst is None or idx < 0 or idx >= len(lst):
        raise ValueError(f"Cannot delete path {path!r}")
    lst.pop(idx)
    return data


def move_node(
    definition: dict[str, Any],
    from_path: str,
    to_list_path: str | None,
    index: int,
) -> dict[str, Any]:
    data = deepcopy(ensure_definition(definition))
    node = get_node(data, from_path)
    if node is None:
        raise ValueError(f"Cannot move path {from_path!r}")
    fp = parse_path(from_path)
    dest_list_path = resolve_insert_list_path(data, to_list_path)
    tp = parse_path(dest_list_path)
    if tp[: len(fp)] == fp and len(tp) >= len(fp):
        # moving into self or descendant list
        if dest_list_path == join_path(fp[:-1]) or join_path(fp) == join_path(tp[: len(fp)]):
            if dest_list_path.startswith(from_path + ".") or dest_list_path == from_path:
                raise ValueError("Cannot move a node into itself")
        if dest_list_path.startswith(from_path + "."):
            raise ValueError("Cannot move a node into its own descendant")

    payload = deepcopy(node)
    data = delete_node(data, from_path)

    # Same-list index adjust
    src_list_path = join_path(fp[:-1])
    src_idx = int(fp[-1])
    if src_list_path == dest_list_path and src_idx < index:
        index -= 1

    _ensure_list_path(data, dest_list_path)
    dest = list_at(data, dest_list_path)
    if dest is None:
        raise ValueError(f"Cannot move into {to_list_path!r}")
    at = max(0, min(int(index), len(dest)))
    dest.insert(at, payload)
    return data


def update_node(
    definition: dict[str, Any], path: str | None, updates: dict[str, Any]
) -> dict[str, Any]:
    data = deepcopy(ensure_definition(definition))
    node = get_node(data, path)
    if node is None:
        raise ValueError(f"Cannot update path {path!r}")
    for key, value in updates.items():
        if key == "type":
            continue
        if value is None or value == "":
            node.pop(key, None)
        elif key in {"columns", "column_span"}:
            try:
                node[key] = int(value)
            except (TypeError, ValueError):
                node[key] = value
        elif key == "required":
            node[key] = (
                bool(value)
                if not isinstance(value, str)
                else value.lower()
                in {
                    "1",
                    "true",
                    "yes",
                    "on",
                }
            )
        else:
            node[key] = value
    return data


def walk_tree(definition: dict[str, Any]) -> list[tuple[str, dict[str, Any], int]]:
    """Flatten nodes as ``(path, node, depth)`` for rendering."""
    out: list[tuple[str, dict[str, Any], int]] = []

    def walk(lst: list[Any], base: str, depth: int) -> None:
        for i, item in enumerate(lst):
            if not isinstance(item, dict):
                continue
            path = join_path([base, i]) if base else str(i)
            t = str(item.get("type") or "")
            out.append((path, item if t else {**item, "type": "_Group"}, depth))
            if t in SCHEMA_CONTAINERS:
                children = item.get("schema")
                if isinstance(children, list):
                    walk(children, join_path([path, "schema"]), depth + 1)
            elif t == TABS_CONTAINER:
                for ti, tab in enumerate(item.get("tabs") or []):
                    if not isinstance(tab, dict):
                        continue
                    tpath = join_path([path, "tabs", ti])
                    out.append((tpath, {**tab, "type": "_Tab"}, depth + 1))
                    schema = tab.get("schema")
                    if isinstance(schema, list):
                        walk(schema, join_path([tpath, "schema"]), depth + 2)
            elif t == WIZARD_CONTAINER:
                for si, step in enumerate(item.get("steps") or []):
                    if not isinstance(step, dict):
                        continue
                    spath = join_path([path, "steps", si])
                    out.append((spath, {**step, "type": "_Step"}, depth + 1))
                    schema = step.get("schema")
                    if isinstance(schema, list):
                        walk(schema, join_path([spath, "schema"]), depth + 2)

    walk(ensure_definition(definition)["components"], "", 0)
    return out
