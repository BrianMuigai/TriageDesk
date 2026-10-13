"""The desk surface's HTTP layer and public facade (UX-02, UX-03, UX-04; D10-01…D10-19).

This module holds the request handler (``DeskServer``/``DeskHandler``), the loopback/Host/
Origin/CSRF/Content-Length defences, the bind guards and the ``serve`` entry point — and it is
the facade the CLI and the suite reach: it imports and re-exports the names the split
presentation modules now own (``copy``/``markup``/``assets``/``pipeline``/``forms``/``card``/
``gate``/``views``), so ``triagedesk.desk.server`` stays the ONE seam ``desk/__init__.py``,
``cli.py`` and the tests use. The moved modules carry the UX behaviour (the copy, the vitals
form, the card, the gate and the view assembly); the networking and the guards stay here.

The surface can never commit on its own (D10-12): the only route to a queue row is the resumed
``approval_gate`` interrupt through the gated ``commit_priority`` tool; this package's import
graph — its static ``import`` statements AND its literal-argument
``importlib.import_module`` / ``__import__`` calls — reaches neither the queue writer nor the
module that hosts that tool. A *string-built* dynamic attribute access (e.g.
``getattr(mod, "commit_" + "priority")``) is not statically provable, so the guard's claim is
deliberately scoped to the literal import graph it scans, never asserted beyond it (WR-01). It
binds loopback only (D10-03), serves a fixed two-name asset allowlist, escapes every rendered
string, and adds no dependency (D10-16).
"""

from __future__ import annotations

import asyncio
import ipaddress
import secrets
import threading
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from pydantic import ValidationError

from triagedesk.desk.assets import _ASSETS, STATIC_DIR
from triagedesk.desk.copy import _FAILURE_COPY, _NO_THREAD_COPY, _SCHEMA_HINT
from triagedesk.desk.forms import _CSRF_FIELD, form_to_case
from triagedesk.desk.gate import editable_colours
from triagedesk.desk.pipeline import decide, submit_case
from triagedesk.desk.views import banner_trigger, render_state, terminal_kind
from triagedesk.durable import DurableError
from triagedesk.graph.build import CHECKPOINTS_DB_PATH

# The host names the surface answers to beyond a loopback IP (WR-02). ``127.0.0.0/8`` and
# ``::1`` are recognised by ``ipaddress.is_loopback``; this set only adds the one name that is
# not an IP literal. A request whose ``Host`` is not loopback is refused before dispatch, so a
# DNS-rebinding page — same-origin with the surface and able to read the token — cannot satisfy
# the ``Origin`` check with a matching foreign ``Host``.
_LOOPBACK_HOSTNAMES = frozenset({"localhost"})

# The largest POST body the surface will read. A form is a few hundred bytes; an unbounded
# ``Content-Length`` would otherwise pin the request thread (IN-01). A body above this cap is
# refused with the documented failure panel, never read.
_MAX_BODY_BYTES = 64 * 1024


class DeskServer(ThreadingHTTPServer):
    """The desk bridge's threaded HTTP server, carrying the checkpoint file path.

    Safe by construction: the loopback guard runs in ``__init__`` (IN-04), so a direct
    ``DeskServer((host, port), DeskHandler)`` cannot bind a wildcard the way ``make_server``
    would refuse. The per-server CSRF token (WR-01) and the submission lock (IN-03) are minted
    here too, so every construction path — factory or direct — is protected identically.
    """

    db_path: Path
    csrf_token: str
    db_lock: threading.Lock

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler: type[BaseHTTPRequestHandler],
        *,
        allow_non_loopback: bool = False,
        bind_and_activate: bool = True,
    ) -> None:
        if not allow_non_loopback:
            _refuse_non_loopback(server_address[0])
        super().__init__(
            server_address, request_handler, bind_and_activate=bind_and_activate
        )
        # One token per server lifetime: minted before any request, so ``GET /`` always
        # renders the token the surface will require on the next POST (WR-01).
        self.csrf_token = secrets.token_urlsafe(32)
        # Serialise the checkpoint-touching submissions: each POST runs its own event loop
        # against the one SQLite file, so concurrent writes could contend for the lock (IN-03).
        self.db_lock = threading.Lock()


def _loopback_host(host_header: str) -> bool:
    """True when a ``Host`` header names loopback (WR-02).

    The port is deliberately ignored: a DNS-rebinding page reaches the real server port, so the
    port matches in the attack and cannot be the discriminator — the *hostname* is. The hostname
    is parsed by hand (the bracketed IPv6 form, else the part before the last colon) rather than
    by ``urlsplit``, which would silently accept a ``user@host`` userinfo trick; ``ipaddress``
    then accepts any ``127.0.0.0/8`` address and ``::1``. Anything else — a foreign name, a
    malformed header, an absent ``Host`` — is not loopback, so the request is refused before it
    can reach a commit path.
    """
    host = host_header.strip()
    if host.startswith("["):
        end = host.find("]")
        if end == -1:
            return False
        hostname = host[1:end]
    else:
        hostname = host.rsplit(":", 1)[0]
    if hostname.lower() in _LOOPBACK_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


class DeskHandler(BaseHTTPRequestHandler):
    """The desk bridge's request handler — loopback only, allowlisted assets, escaped output."""

    server: DeskServer

    def _send_html(self, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _page(self, **kwargs: Any) -> str:
        """Render a state with the per-server CSRF token threaded into the forms (WR-01)."""
        return render_state(csrf_token=self.server.csrf_token, **kwargs)

    def _host_ok(self) -> bool:
        """True only for a loopback ``Host`` header (WR-02).

        The ``Host`` header is client-controlled, so it can never be the trust anchor for
        "same origin": a DNS-rebinding page is same-origin with the surface and can read the
        token, then POST with a matching foreign ``Host``/``Origin``. Pinning the accepted host
        to loopback refuses that request before dispatch, which is what makes the ``Origin``
        comparison below meaningful.
        """
        return _loopback_host(self.headers.get("Host") or "")

    def _cross_origin(self) -> bool:
        """True when a present ``Origin`` header is not this surface's own origin (WR-01).

        A cross-origin page's POST carries the page's own ``Origin``, which cannot match the
        loopback ``Host`` — so the request is refused before it can reach a commit path. An
        absent ``Origin`` (a non-browser client) is not a cross-origin signal; the CSRF token
        is the defence there, and it is required on every POST regardless.
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return False
        return origin != f"http://{self.headers.get('Host')}"

    def _csrf_ok(self, form: Mapping[str, str]) -> bool:
        """True when *form* carries the per-server CSRF token (WR-01), compared in constant time.

        Both sides are compared as UTF-8 **bytes**: ``compare_digest`` raises ``TypeError`` on a
        ``str`` carrying non-ASCII characters, and ``supplied`` is attacker-controlled
        (``parse_qs`` percent-decodes UTF-8), so a ``str`` comparison would let a single
        non-ASCII token crash the handler instead of rendering the failure panel. The token
        itself is ASCII (``token_urlsafe``), so encoding both sides is total and cannot raise.
        """
        supplied = str(form.get(_CSRF_FIELD, ""))
        return bool(supplied) and secrets.compare_digest(
            supplied.encode("utf-8"), self.server.csrf_token.encode("utf-8")
        )

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        """Render the page for ``/``; serve the CSS by allowlist; anything else is a 404.

        A non-loopback ``Host`` is refused with 403 (WR-02), so the token page is never served
        under a foreign host a DNS-rebinding page could read. ``/`` (and ``/index.html``) render
        the empty state through the ONE template rather than serving the raw file, so no
        unsubstituted placeholder is ever exposed. Only the CSS is served as raw bytes, and only
        when its name is in the fixed allowlist — no path is built from ``self.path``.
        """
        if not self._host_ok():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        path = self.path.split("?", 1)[0]
        name = "index.html" if path in ("/", "") else path.lstrip("/")
        if name not in _ASSETS:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if name == "index.html":
            self._send_html(self._page())
            return
        body = (STATIC_DIR / name).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", _ASSETS[name])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
        """Dispatch ``/case`` and ``/decision`` over the ONE pause/resume plumbing.

        Three defences run before dispatch: a non-loopback ``Host`` renders the documented
        failure panel (WR-02), so a DNS-rebinding page cannot satisfy the origin check with a
        matching foreign ``Host``; a cross-origin ``Origin`` is refused with 403 (WR-01); and a
        POST missing the per-server CSRF token renders the same failure panel (WR-01). The
        header/body parse is guarded too: a malformed ``Content-Length`` (non-numeric, negative
        or above ``_MAX_BODY_BYTES``) or a body that is not valid UTF-8 renders that panel rather
        than crashing the handler, dropping the connection, or pinning the thread on a body that
        never arrives (IN-01).
        """
        if not self._host_ok():
            self._send_html(self._page(error=_FAILURE_COPY))
            return
        if self._cross_origin():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0 or length > _MAX_BODY_BYTES:
                raise ValueError("invalid Content-Length")
            raw = self.rfile.read(length).decode("utf-8")
        except (TypeError, ValueError, UnicodeDecodeError):
            self._send_html(self._page(error=_FAILURE_COPY))
            return
        form = {
            key: values[0]
            for key, values in parse_qs(raw, keep_blank_values=True).items()
        }
        if not self._csrf_ok(form):
            self._send_html(self._page(error=_FAILURE_COPY))
            return
        path = self.path.split("?", 1)[0]
        if path == "/case":
            self._send_html(self._handle_case(form))
        elif path == "/decision":
            self._send_html(self._handle_decision(form))
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_case(self, form: Mapping[str, str]) -> str:
        try:
            case = form_to_case(form)
        except ValidationError as exc:
            # A schema rejection renders BESIDE the offending field (the UI-SPEC ``## UI
            # Considerations`` ``error | vitals-form`` row), so the mandated "Check the
            # highlighted field" copy is literally true. A model-level error with no field
            # falls back to the error panel rather than mis-highlighting a field.
            field = _validation_field(exc)
            if field is None:
                return self._page(error=_validation_message(exc), form_values=form)
            return self._page(
                field_error=(field, _validation_message(exc)), form_values=form
            )
        except (TypeError, ValueError):
            # Defence in depth: any coercion failure that somehow bypassed the schema's own
            # validator is still reported, never an approve (the surface's stated contract).
            return self._page(error=_FAILURE_COPY, form_values=form)
        try:
            # The lock serialises submissions over the one checkpoint file (IN-03).
            with self.server.db_lock:
                paused = asyncio.run(submit_case(case, self.server.db_path))
        except Exception:  # noqa: BLE001 - any failure is reported, never an approve
            return self._page(error=_FAILURE_COPY, form_values=form)
        return self._page(paused=paused, form_values=form)

    def _handle_decision(self, form: Mapping[str, str]) -> str:
        thread_id = str(form.get("thread_id", "")).strip()
        if not thread_id:
            return self._page(error=_NO_THREAD_COPY, form_values=form)
        try:
            with self.server.db_lock:
                result = asyncio.run(decide(thread_id, form, self.server.db_path))
        except DurableError as exc:
            # The gate's OWN refusal (blank identity, missing colour, no pending gate): the
            # surface shows that reason and restates no gate logic.
            return self._page(error=str(exc), form_values=form)
        except Exception:  # noqa: BLE001 - a server/graph failure leaves the decision unresolved
            return self._page(error=_FAILURE_COPY, form_values=form)
        return self._page(result=result, form_values=form)


def _validation_field(exc: ValidationError) -> str | None:
    """The field the schema's first error names (the ``loc`` head), or ``None``.

    Used to render a schema rejection beside the offending field. ``CaseInput`` carries only
    field-level constraints, so a real rejection always names a field; ``None`` is the honest
    fallback for a hypothetical model-level error, which then renders in the error panel.
    """
    location = exc.errors()[0].get("loc", ())
    return str(location[0]) if location else None


def _validation_message(exc: ValidationError) -> str:
    """Build the UI-SPEC schema-rejection copy from the schema's OWN field message (D10-13)."""
    error = exc.errors()[0]
    location = ".".join(str(part) for part in error.get("loc", ()))
    message = str(error.get("msg", "invalid input"))
    detail = f"{location}: {message}" if location else message
    return f"{detail}. {_SCHEMA_HINT}"


def _refuse_non_loopback(host: str) -> None:
    """Fail closed on a non-loopback bind (D10-03).

    The surface has no authentication and gates the approve-to-queue path, so a wildcard
    or routable bind would expose patient vitals/complaints and the commit path to the
    whole network. A host that is not a literal loopback address (including a name that
    cannot be proven loopback) is refused; the caller must opt in explicitly to override.
    """
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError(
            f"the desk surface binds loopback only (D10-03); refusing {host!r}"
        ) from exc
    if not address.is_loopback:
        raise ValueError(
            f"the desk surface binds loopback only (D10-03); refusing {host!r}"
        )


def make_server(
    host: str,
    port: int,
    db_path: str | Path,
    *,
    allow_non_loopback: bool = False,
) -> DeskServer:
    """Construct the desk bridge bound to *host* (loopback only — D10-03) over *db_path*.

    A non-loopback *host* is refused unless the caller passes ``allow_non_loopback=True``
    explicitly — the surface is an unauthenticated local prototype, so binding a wildcard
    is never the default (WR-02). The refusal lives in :class:`DeskServer` itself (IN-04), so
    this factory and a direct construction are protected identically.
    """
    server = DeskServer(
        (host, port), DeskHandler, allow_non_loopback=allow_non_loopback
    )
    server.db_path = Path(db_path)
    return server


def serve(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: str | Path = CHECKPOINTS_DB_PATH,
    allow_non_loopback: bool = False,
) -> None:
    """Serve the desk surface until interrupted (loopback only — D10-03).

    A non-loopback *host* is refused unless ``allow_non_loopback=True`` is passed (WR-02).
    """
    make_server(
        host, port, db_path, allow_non_loopback=allow_non_loopback
    ).serve_forever()


__all__ = [
    "DeskHandler",
    "DeskServer",
    "STATIC_DIR",
    "banner_trigger",
    "decide",
    "editable_colours",
    "form_to_case",
    "make_server",
    "render_state",
    "serve",
    "submit_case",
    "terminal_kind",
]
