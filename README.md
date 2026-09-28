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

panel.plugin(
    FormBuilderPlugin.make()
    .navigation_group("Forms")
)
```

For database storage, create the tables from `almasix_orbit_form_builder.migrations.migration_statements()` and:

```python
from almasix_orbit_form_builder import DatabaseFormStore, set_form_store

set_form_store(DatabaseFormStore())
```

## What you get

| Surface | Purpose |
|---------|---------|
| **Form builder** page | Palette of all Orbit field/layout types, JSON tree editor, live preview, draft/publish |
| **Definitions** resource | List and manage form metadata |
| **Submissions** resource | Inspect answers |
| **Fill** page (`/forms/fill`) | Respondents submit published forms |

## Definitions

Forms are stored as JSON that mirrors Orbit’s `to_dict()` shape:

```json
{
  "components": [
    {
      "type": "Section",
      "heading": "Contact",
      "schema": [
        { "type": "TextInput", "name": "email", "label": "Email", "required": true }
      ]
    }
  ]
}
```

`build_form(definition)` hydrates that document into a live `almasix.orbit.forms.Form`. Callables (relationship loaders, live hooks) are not embedded in JSON — register named handlers in your app and reference them from field config when needed.

## Answer handlers

Every submit is **always** persisted first. Then configured handlers run in order:

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

def push_to_crm(form, submission, config):
    ...

register_handler("my_crm", push_to_crm)
```

## Tenancy

When the panel has tenancy enabled, the plugin binds `set_tenant_resolver` so definitions and submissions are keyed by `tenant_id` (empty string = global). Use `.without_tenant_resolver()` to skip.

## Limits (v1)

- Designer edits a structured JSON tree (not a free-form canvas).
- Relationship / upload-heavy fields work with static serializable props; advanced callables need named handlers.
- Fill page lives at `forms/fill` — set `form_slug` on the host (or open via the UI) for the published slug.

## License

MIT
