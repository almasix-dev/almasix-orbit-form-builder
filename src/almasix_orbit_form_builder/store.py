"""In-memory and database repositories for form definitions and submissions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol

from almasix_orbit_form_builder.models import FormDefinition, FormSubmission, new_id
from almasix_orbit_form_builder.tenant import GLOBAL_TENANT_ID, current_tenant_id


def _now() -> datetime:
    return datetime.now(UTC)


def _encode(payload: Any) -> str:
    return json.dumps(payload)


def _decode(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (dict, list, int, float, bool)):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        return raw


def _run(coro: Any) -> Any:
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class FormStore(Protocol):
    def list_definitions(self, *, tenant_id: str | None = None) -> list[FormDefinition]: ...

    def get_definition(
        self, form_id: str, *, tenant_id: str | None = None
    ) -> FormDefinition | None: ...

    def get_definition_by_slug(
        self, slug: str, *, tenant_id: str | None = None
    ) -> FormDefinition | None: ...

    def save_definition(self, form: FormDefinition) -> FormDefinition: ...

    def delete_definition(self, form_id: str, *, tenant_id: str | None = None) -> None: ...

    def list_submissions(
        self, form_id: str | None = None, *, tenant_id: str | None = None
    ) -> list[FormSubmission]: ...

    def save_submission(self, submission: FormSubmission) -> FormSubmission: ...

    def get_submission(
        self, submission_id: str, *, tenant_id: str | None = None
    ) -> FormSubmission | None: ...


def _tenant(tenant_id: str | None) -> str:
    if tenant_id is not None:
        return tenant_id
    return current_tenant_id()


class MemoryFormStore:
    """Process-local store used by tests and local demos."""

    def __init__(self) -> None:
        self.definitions: dict[str, FormDefinition] = {}
        self.submissions: dict[str, FormSubmission] = {}

    def list_definitions(self, *, tenant_id: str | None = None) -> list[FormDefinition]:
        tid = _tenant(tenant_id)
        return [f for f in self.definitions.values() if f.tenant_id == tid]

    def get_definition(
        self, form_id: str, *, tenant_id: str | None = None
    ) -> FormDefinition | None:
        form = self.definitions.get(form_id)
        if form is None:
            return None
        tid = _tenant(tenant_id)
        return form if form.tenant_id == tid else None

    def get_definition_by_slug(
        self, slug: str, *, tenant_id: str | None = None
    ) -> FormDefinition | None:
        tid = _tenant(tenant_id)
        for form in self.definitions.values():
            if form.slug == slug and form.tenant_id == tid:
                return form
        if tid != GLOBAL_TENANT_ID:
            for form in self.definitions.values():
                if form.slug == slug and form.tenant_id == GLOBAL_TENANT_ID:
                    return form
        return None

    def save_definition(self, form: FormDefinition) -> FormDefinition:
        form.updated_at = _now()
        if not form.id:
            form.id = new_id()
        self.definitions[form.id] = form
        return form

    def delete_definition(self, form_id: str, *, tenant_id: str | None = None) -> None:
        form = self.get_definition(form_id, tenant_id=tenant_id)
        if form is not None:
            del self.definitions[form_id]

    def list_submissions(
        self, form_id: str | None = None, *, tenant_id: str | None = None
    ) -> list[FormSubmission]:
        tid = _tenant(tenant_id)
        rows = [s for s in self.submissions.values() if s.tenant_id == tid]
        if form_id is not None:
            rows = [s for s in rows if s.form_id == form_id]
        return sorted(rows, key=lambda s: s.created_at, reverse=True)

    def save_submission(self, submission: FormSubmission) -> FormSubmission:
        if not submission.id:
            submission.id = new_id()
        self.submissions[submission.id] = submission
        return submission

    def get_submission(
        self, submission_id: str, *, tenant_id: str | None = None
    ) -> FormSubmission | None:
        row = self.submissions.get(submission_id)
        if row is None:
            return None
        tid = _tenant(tenant_id)
        return row if row.tenant_id == tid else None


class DatabaseFormStore:
    """Persist forms in Almasix ``DB`` tables ``orbit_form_definitions`` / ``orbit_form_submissions``."""

    def __init__(
        self,
        *,
        definitions_table: str = "orbit_form_definitions",
        submissions_table: str = "orbit_form_submissions",
        connection: str | None = None,
    ) -> None:
        self.definitions_table = definitions_table
        self.submissions_table = submissions_table
        self.connection = connection

    def _qb(self, table: str) -> Any:
        from almasix.orm.facade import DB

        return DB.table(table, connection=self.connection)

    def _row_to_definition(self, row: dict[str, Any]) -> FormDefinition:
        return FormDefinition(
            id=str(row["id"]),
            slug=str(row["slug"]),
            title=str(row["title"]),
            status=str(row.get("status") or "draft"),
            definition=_decode(row.get("definition")) or {},
            settings=_decode(row.get("settings")) or {},
            tenant_id=str(row.get("tenant_id") or GLOBAL_TENANT_ID),
        )

    def _row_to_submission(self, row: dict[str, Any]) -> FormSubmission:
        return FormSubmission(
            id=str(row["id"]),
            form_id=str(row["form_id"]),
            payload=_decode(row.get("payload")) or {},
            meta=_decode(row.get("meta")) or {},
            tenant_id=str(row.get("tenant_id") or GLOBAL_TENANT_ID),
        )

    def list_definitions(self, *, tenant_id: str | None = None) -> list[FormDefinition]:
        tid = _tenant(tenant_id)

        async def _load() -> list[FormDefinition]:
            rows = await self._qb(self.definitions_table).where("tenant_id", tid).get()
            return [self._row_to_definition(r) for r in rows]

        return _run(_load())

    def get_definition(
        self, form_id: str, *, tenant_id: str | None = None
    ) -> FormDefinition | None:
        tid = _tenant(tenant_id)

        async def _load() -> FormDefinition | None:
            row = await (
                self._qb(self.definitions_table)
                .where("id", form_id)
                .where("tenant_id", tid)
                .first()
            )
            return self._row_to_definition(row) if row else None

        return _run(_load())

    def get_definition_by_slug(
        self, slug: str, *, tenant_id: str | None = None
    ) -> FormDefinition | None:
        tid = _tenant(tenant_id)

        async def _load() -> FormDefinition | None:
            row = await (
                self._qb(self.definitions_table).where("slug", slug).where("tenant_id", tid).first()
            )
            if row is None and tid != GLOBAL_TENANT_ID:
                row = await (
                    self._qb(self.definitions_table)
                    .where("slug", slug)
                    .where("tenant_id", GLOBAL_TENANT_ID)
                    .first()
                )
            return self._row_to_definition(row) if row else None

        return _run(_load())

    def save_definition(self, form: FormDefinition) -> FormDefinition:
        form.updated_at = _now()
        if not form.id:
            form.id = new_id()
        payload = {
            "id": form.id,
            "slug": form.slug,
            "title": form.title,
            "status": form.status,
            "definition": _encode(form.definition),
            "settings": _encode(form.settings),
            "tenant_id": form.tenant_id,
            "updated_at": form.updated_at.isoformat(),
        }

        async def _save() -> None:
            existing = await (
                self._qb(self.definitions_table)
                .where("id", form.id)
                .where("tenant_id", form.tenant_id)
                .first()
            )
            if existing:
                await (
                    self._qb(self.definitions_table)
                    .where("id", form.id)
                    .where("tenant_id", form.tenant_id)
                    .update(payload)
                )
            else:
                payload["created_at"] = form.created_at.isoformat()
                await self._qb(self.definitions_table).insert(payload)

        _run(_save())
        return form

    def delete_definition(self, form_id: str, *, tenant_id: str | None = None) -> None:
        tid = _tenant(tenant_id)

        async def _delete() -> None:
            await (
                self._qb(self.definitions_table)
                .where("id", form_id)
                .where("tenant_id", tid)
                .delete()
            )

        _run(_delete())

    def list_submissions(
        self, form_id: str | None = None, *, tenant_id: str | None = None
    ) -> list[FormSubmission]:
        tid = _tenant(tenant_id)

        async def _load() -> list[FormSubmission]:
            q = self._qb(self.submissions_table).where("tenant_id", tid)
            if form_id is not None:
                q = q.where("form_id", form_id)
            rows = await q.get()
            return [self._row_to_submission(r) for r in rows]

        return _run(_load())

    def save_submission(self, submission: FormSubmission) -> FormSubmission:
        if not submission.id:
            submission.id = new_id()
        payload = {
            "id": submission.id,
            "form_id": submission.form_id,
            "payload": _encode(submission.payload),
            "meta": _encode(submission.meta),
            "tenant_id": submission.tenant_id,
            "created_at": submission.created_at.isoformat(),
        }

        async def _save() -> None:
            await self._qb(self.submissions_table).insert(payload)

        _run(_save())
        return submission

    def get_submission(
        self, submission_id: str, *, tenant_id: str | None = None
    ) -> FormSubmission | None:
        tid = _tenant(tenant_id)

        async def _load() -> FormSubmission | None:
            row = await (
                self._qb(self.submissions_table)
                .where("id", submission_id)
                .where("tenant_id", tid)
                .first()
            )
            return self._row_to_submission(row) if row else None

        return _run(_load())


_store: FormStore | None = None


def set_form_store(store: FormStore) -> None:
    global _store
    _store = store


def get_form_store() -> FormStore:
    global _store
    if _store is None:
        _store = MemoryFormStore()
    return _store


def bootstrap_memory_store() -> MemoryFormStore:
    store = MemoryFormStore()
    set_form_store(store)
    return store
