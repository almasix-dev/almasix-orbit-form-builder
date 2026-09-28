"""Pluggable answer handlers run after a submission is persisted."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from almasix_orbit_form_builder.models import FormDefinition, FormSubmission

HandlerFn = Callable[[FormDefinition, FormSubmission, Mapping[str, Any]], None]


class AnswerHandler(Protocol):
    name: str

    def handle(
        self,
        form: FormDefinition,
        submission: FormSubmission,
        config: Mapping[str, Any],
    ) -> None: ...


_HANDLERS: dict[str, HandlerFn] = {}


def register_handler(name: str, fn: HandlerFn) -> None:
    """Register a named callable handler (also usable as ``{"type": "callable", "name": ...}``)."""
    _HANDLERS[str(name)] = fn


def get_handler(name: str) -> HandlerFn | None:
    return _HANDLERS.get(str(name))


def clear_handlers() -> None:
    _HANDLERS.clear()


def _handle_store(
    form: FormDefinition, submission: FormSubmission, config: Mapping[str, Any]
) -> None:
    # Persistence already happened; this handler is a no-op marker.
    return None


def _handle_email(
    form: FormDefinition, submission: FormSubmission, config: Mapping[str, Any]
) -> None:
    to = config.get("to")
    if not to:
        return
    # Best-effort: use Almasix mail if available; otherwise no-op in tests.
    try:
        from almasix.mail.facade import Mail  # type: ignore[import-not-found]
    except Exception:
        return
    subject = str(config.get("subject") or f"New submission: {form.title}")
    body = "\n".join(f"{k}: {v}" for k, v in submission.payload.items())
    try:
        Mail.to(to).subject(subject).text(body).send()
    except Exception:
        return


def _handle_webhook(
    form: FormDefinition, submission: FormSubmission, config: Mapping[str, Any]
) -> None:
    url = config.get("url")
    if not url:
        return
    import json
    import urllib.request

    payload = json.dumps(
        {
            "form": form.slug,
            "form_id": form.id,
            "submission_id": submission.id,
            "payload": submission.payload,
            "meta": submission.meta,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        str(url),
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "orbit-form-builder"},
        method="POST",
    )
    timeout = float(config.get("timeout", 5))
    try:
        urllib.request.urlopen(req, timeout=timeout).read()  # noqa: S310
    except Exception:
        return


def _handle_callable(
    form: FormDefinition, submission: FormSubmission, config: Mapping[str, Any]
) -> None:
    name = config.get("name") or config.get("handler")
    if not name:
        return
    fn = get_handler(str(name))
    if fn is None:
        return
    fn(form, submission, config)


_BUILTIN: dict[str, HandlerFn] = {
    "store": _handle_store,
    "email": _handle_email,
    "webhook": _handle_webhook,
    "callable": _handle_callable,
}


def dispatch_handlers(
    form: FormDefinition,
    submission: FormSubmission,
    handlers: list[Mapping[str, Any]] | None = None,
) -> list[str]:
    """Run configured handlers. Always includes an implicit store step already done by the host."""
    ran: list[str] = []
    items = list(handlers or form.settings.get("handlers") or [])
    for item in items:
        if not isinstance(item, Mapping):
            continue
        kind = str(item.get("type") or "")
        fn = _BUILTIN.get(kind) or get_handler(kind)
        if fn is None:
            continue
        fn(form, submission, item)
        ran.append(kind)
    return ran


# Ensure builtins are also reachable by name via register_handler for apps.
for _name, _fn in _BUILTIN.items():
    register_handler(_name, _fn)
