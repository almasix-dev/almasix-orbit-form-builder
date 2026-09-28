# Orbit Form Builder

Visually build Orbit forms from **every** Orbit field and layout, publish them, and collect answers with pluggable handlers.

## Install

```bash
pip install almasix-orbit-form-builder
```

Register the plugin on a panel:

```python
from almasix_orbit_form_builder import FormBuilderPlugin, bootstrap_memory_store

bootstrap_memory_store()  # or DatabaseFormStore() after migrating

panel.plugin(FormBuilderPlugin.make().navigation_group("Forms"))
```

For database storage, create the tables from `almasix_orbit_form_builder.migrations.migration_statements()` and:

```python
from almasix_orbit_form_builder import DatabaseFormStore, set_form_store

set_form_store(DatabaseFormStore())
```

Requires **almasix-orbit ≥ 0.5.3** (custom pages mount Conduit hosts via `get_conduit_host()`).

## What you get

| Surface | Purpose |
|---------|---------|
| **Form builder** page | Generous visual canvas (grids/fields look like themselves), filterable component bank, drag-drop with drop-zone highlights, property modal, preview modal with live validation, draft/publish |
| **Definitions** resource | List metadata (JSON is readonly — edit structure on the builder page) |
| **Submissions** resource | Inspect answers |
| **Fill** page (`/forms/fill`) | Respondents submit published forms |

## Designer

1. Filter or browse the **Components** bank; drag onto the canvas or into a layout drop zone (or click to add into the selection).
2. Root fields follow **Form columns** (default **2**). Nested **Grid** / **Group** show their own column count.
3. Click a field or layout (or **Edit**) to open the **properties** modal — label, placeholder, validation rules, columns, etc.
4. **Preview** opens a modal with a fillable form (validates; does not store).
5. **JSON** / **Handlers** are optional drawers — definition JSON stays a readonly export.

## Definitions

Forms are stored as JSON that mirrors Orbit’s `to_dict()` shape:

```json
{
  "components": [
    {
      "type": "Section",
      "heading": "Contact",
      "schema": [
        {
          "type": "Grid",
          "columns": 2,
          "schema": [
            { "type": "TextInput", "name": "email", "label": "Email", "required": true },
            { "type": "TextInput", "name": "phone", "label": "Phone" }
          ]
        }
      ]
    }
  ]
}
```

`build_form(definition)` hydrates that document into a live `almasix.orbit.forms.Form`. Callables (relationship loaders, live hooks) are not embedded in JSON — register named handlers in your app and reference them from field config when needed.

## Answer handlers

Every submit is **always** persisted first. Then configured handlers run in order. Configure them in the designer (store / email / webhook / callable), for example:

```json
{
  "handlers": [
    { "type": "store" },
    { "type": "email", "to": "ops@example.com", "subject": "New lead" },
    { "type": "webhook", "url": "https://example.com/hooks/forms" },
    { "type": "callable", "name": "my_crm" }
  ],
  "success_message": "Thanks — we got it."
}
```

```python
from almasix_orbit_form_builder import register_handler


def push_to_crm(form, submission, config): ...


register_handler("my_crm", push_to_crm)
```

## Tenancy

When the panel has tenancy enabled, the plugin binds `set_tenant_resolver` so definitions and submissions are keyed by `tenant_id` (empty string = global). Use `.without_tenant_resolver()` to skip.

## Limits

- Designer is a **nested tree** with drag-drop (not a free-form pixel canvas).
- Relationship / upload-heavy fields work with static serializable props; advanced callables need named handlers.
- Fill page lives at `forms/fill` — set `form_slug` on the host (or open via the UI) for the published slug.

## License

MIT
