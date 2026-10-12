"""The desk surface end-to-end and structural proof suite (Plans 10-01/10-02, UX-01…UX-04).

Proves the phase's surface hermetically (D10-15): the bridge is driven over loopback
ONLY, through the shared conftest seams (the injected in-memory store and a ``tmp_path``
checkpoint file), so no model, no borrowed subprocess and no repo-root artefact is touched.

Three parts:

* the end-to-end proof — a GET renders the empty state, a vitals POST renders the graph's
  suggested priority framed as a suggestion with its adjacent citations and evidence, and a
  named-human approve lands EXACTLY one queue row through the gated tool (Plan 10-01);
* the uncertainty and fail-safe proofs (Plan 10-02) — the loud banner fires only from the
  typed signal, a deferred case is a read-only card with no gate, the evidence list is read
  from the paused state snapshot, and every gate branch (dismiss, timeout, edit set, schema
  rejection, repeat submission) is provably incapable of committing without a named human;
* the structural and copy proofs — the ``desk/`` package has no commit path, binds loopback
  only, hardens offline before its handler is reached, makes no external request, escapes the
  untrusted complaint, launches no borrowed subprocess, and renders no prohibited token or
  numeric-risk figure.
"""

from __future__ import annotations

import asyncio
import contextlib
import html
import inspect
import re
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from conftest import (
    COMPLETE_CASE,
    package_parts_for,
    resolved_imports,
)
from triagedesk.cli import main
from triagedesk.core import matcher, retrieval, scorer
from triagedesk.core.rules import get_tews
from triagedesk.core.schema import (
    ApprovalToken,
    CaseInput,
    ConfidenceResult,
    Escalation,
    EvidenceResult,
    PriorityResult,
    RecoveryRequest,
)
from triagedesk.desk import server as desk_server
from triagedesk.desk.server import (
    decide,
    form_to_case,
    make_server,
    serve,
    submit_case,
)
from triagedesk.durable import PausedRun
from triagedesk.evals.case import CaseSpec, load_cases
from triagedesk.evals.invariants import prohibited_tokens

DESK_DIR = Path(desk_server.__file__).parent
SRC_ROOT = DESK_DIR.resolve().parents[1]  # .../src (the parent of the triagedesk package)
ASSET_DIR = DESK_DIR / "static"
CASES_DIR = Path(__file__).resolve().parents[1] / "evals" / "cases"

# The banner headline, verbatim from UX-01 (asserted as a literal so a paraphrase fails).
BANNER_HEADLINE = "No discriminator matched / low confidence — nurse to confirm"
NO_MATCH_BODY = (
    "No discriminator matched this complaint, so this suggestion may be incomplete. "
    "Confirm before you act."
)
LOW_CONFIDENCE_BODY = (
    "Confidence is low for this suggestion, so it may be incomplete. Confirm before you act."
)

# The modules a desk module must NEVER import: the queue writer and the module that hosts the
# gated commit tool. The only route to a queue row is the resumed interrupt through that tool
# (D10-11/D10-12), so a direct import here would be a second, un-audited write path.
_COMMIT_PATH_MODULES = frozenset({"triagedesk.store.queue", "triagedesk.mcp.server"})
# The commit symbols themselves: importing one from anywhere is a second write path, however
# it is reached (an absolute import, a relative import, or a re-export).
_COMMIT_SYMBOLS = frozenset({"commit_to_queue", "commit_priority"})


@contextlib.contextmanager
def _running_server(db_path: Path) -> Iterator[Any]:
    """Start the bridge on an OS-picked loopback port; shut it down in a ``finally``."""
    server = make_server("127.0.0.1", 0, db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _get(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def _csrf_token(base: str) -> str:
    """The per-server CSRF token the surface renders into every form (WR-01)."""
    match = re.search(r'name="csrf_token" value="([^"]+)"', _get(base + "/"))
    assert match, "the rendered form carries no csrf_token field"
    return match.group(1)


def _post(url: str, data: dict[str, str]) -> str:
    """POST *data* with the surface's own CSRF token, as a same-origin browser would.

    The token is fetched from ``GET /`` (the surface's own page), never hard-coded, so the
    tests exercise exactly the token a real form carries (WR-01).
    """
    origin = url.rsplit("/", 1)[0]
    payload = {**data, "csrf_token": _csrf_token(origin)}
    encoded = urllib.parse.urlencode(payload).encode("utf-8")
    with urllib.request.urlopen(url, data=encoded) as response:
        return response.read().decode("utf-8")


def _post_status(
    url: str, data: dict[str, str], headers: dict[str, str] | None = None
) -> tuple[int, str]:
    """POST *data* with NO CSRF token injection; return ``(status, body)``.

    Used by the CSRF proofs: a request that omits the token, or carries a foreign ``Origin``,
    must be refused (a 403 or the documented failure panel) and write nothing (WR-01).
    """
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=encoded, headers=headers or {})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _raw_post(server: Any, request_bytes: bytes) -> bytes:
    """Send raw request bytes over a fresh socket and read the raw response.

    Used for the malformed-request proofs: ``urllib`` would refuse to build an invalid
    ``Content-Length`` or a non-UTF-8 body, so the request is hand-written (WR-01).
    """
    with socket.create_connection(
        ("127.0.0.1", server.server_address[1]), timeout=5
    ) as sock:
        sock.sendall(request_bytes)
        sock.settimeout(5)
        chunks: list[bytes] = []
        try:
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        except TimeoutError:
            pass
        return b"".join(chunks)


def _form_from_case(case: CaseInput) -> dict[str, str]:
    """Render a case as the vitals form a nurse would post (no literal colour — D10-08)."""
    form: dict[str, str] = {}
    for key, value in case.model_dump().items():
        if value is None:
            continue
        if isinstance(value, bool):
            form[key] = "true" if value else "false"
        else:
            form[key] = str(value)
    return form


def _base(server: Any) -> str:
    return f"http://127.0.0.1:{server.server_address[1]}"


def _thread_id(body: str) -> str:
    """The paused thread id the gate form carries as its hidden field (D10-11)."""
    match = re.search(r'name="thread_id" value="([^"]+)"', body)
    assert match, "the gate form carries no hidden thread_id field"
    return match.group(1)


def _section(body: str, cls: str) -> str:
    """The rendered ``<section class="cls">`` region (a card / gate region)."""
    match = re.search(rf'<section class="{cls}"[^>]*>.*?</section>', body, re.DOTALL)
    assert match, f"the rendered page has no {cls!r} region"
    return match.group(0)


def _banner_region(body: str) -> str:
    """The inner HTML of the ``uncertainty-banner`` region (empty when it did not fire)."""
    match = re.search(
        r'<div class="uncertainty-banner"[^>]*>(.*?)</div>', body, re.DOTALL
    )
    assert match, "the rendered page has no uncertainty-banner region"
    return match.group(1)


def _css_block(css: str, selector: str) -> str:
    """The declaration block of ONE served-CSS rule (for the wrap/clip proxies)."""
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, f"the served CSS declares no rule for {selector!r}"
    return match.group(1)


def _e09() -> CaseSpec:
    """The genuine ``no_match`` fixture the deferred-path proofs run (never a fabricated state)."""
    return next(case for case in load_cases(CASES_DIR) if case.id == "E-09")


def _run_from_state(**channels: Any) -> PausedRun:
    """A terminal ``PausedRun`` built from a state mapping (for the trigger/terminal proofs)."""
    return PausedRun(
        thread_id="state-thread",
        config={},
        result=channels,
        payload=None,
        paused=False,
        existed=False,
    )


# ------------------------------------------------------------------ end-to-end (Plan 10-01)


def test_form_to_card_to_gate_to_commit(tmp_path: Path, injected_store: Any) -> None:
    """A vitals form renders the suggestion; a named approve lands EXACTLY one queue row."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        base = _base(server)

        empty = _get(base + "/")
        assert "No case yet" in empty
        assert (
            "Enter the patient's vitals and complaint, then choose Get suggested priority."
            in empty
        )
        assert "Suggested priority" not in empty
        assert "Your decision" not in empty

        # Learn the graph's own colour from a direct run — never a literal colour (D10-08).
        probe = asyncio.run(submit_case(COMPLETE_CASE, tmp_path / "probe.db"))
        assert probe.paused and probe.payload is not None
        colour = str(probe.payload["colour"])
        assert colour

        body = _post(base + "/case", _form_from_case(COMPLETE_CASE))
        for expected in (
            "Suggested priority",
            "This is a suggestion, not a decision. You confirm the priority.",
            "Suggested colour:",
            "Target time:",
            "Why these vitals:",
            "Evidence from the SATS knowledge base:",
            "Your decision",
            "Approve suggestion",
            "Edit colour",
            "Dismiss (commit nothing)",
        ):
            assert expected in body, f"missing card/gate copy: {expected}"
        assert colour in body, "the suggested colour name was not rendered as text"

        match = re.search(r'name="thread_id" value="([^"]+)"', body)
        assert match, "the gate form carries no hidden thread_id field"
        thread_id = match.group(1)
        assert thread_id

        decision = _post(
            base + "/decision",
            {
                "thread_id": thread_id,
                "decision": "approve",
                "name": "Nurse Demo",
                "role": "triage nurse",
            },
        )
        assert "Approved by Nurse Demo (triage nurse) — committed to the queue." in decision
        assert len(injected_store.rows) == 1, "an approve did not land exactly one queue row"


def test_trauma_checkbox_is_paired_with_a_hidden_false() -> None:
    """The Trauma checkbox carries a hidden ``false`` companion, placed after it (CR-01).

    An unchecked HTML checkbox is not a successful control, so a bare checkbox makes the
    browser omit the scored ``trauma`` vital and the case routes to the recovery terminal. The
    companion MUST follow the checkbox: the handler keeps ``parse_qs(...)[key][0]``, so a checked
    box (``["true", "false"]``) still reads True while an unchecked box (``["false"]``) reads
    False.
    """
    body = desk_server.render_state()
    checkbox = '<input id="trauma" name="trauma" type="checkbox" value="true">'
    hidden = '<input type="hidden" name="trauma" value="false">'
    assert checkbox in body, "the Trauma checkbox is not rendered"
    assert hidden in body, "the Trauma checkbox has no hidden false companion"
    assert body.index(checkbox) < body.index(hidden), (
        "the hidden companion must follow the checkbox so a checked box still reads true"
    )
    # The two browser submissions the pairing produces, through the ONE schema mapping.
    assert form_to_case({"trauma": "false"}).trauma is False
    assert form_to_case({"trauma": "true"}).trauma is True


def test_unchecked_trauma_reaches_the_card_and_gate(
    tmp_path: Path, injected_store: Any
) -> None:
    """The DEFAULT (Trauma unchecked) browser submission is committable, not a recovery (CR-01).

    Simulates the browser's own serialisation of the RENDERED form: the unchecked Trauma
    checkbox contributes nothing of its own, but the paired hidden ``false`` — which the browser
    DOES submit — supplies the scored vital. Before the fix (a bare checkbox) the browser omitted
    ``trauma`` entirely, the schema mapped the absence to ``None``, and the submission routed to
    the recovery terminal with no card and no gate.
    """
    with _running_server(tmp_path / "checkpoints.db") as server:
        rendered = _get(_base(server) + "/")
        companion = re.search(
            r'<input type="hidden" name="trauma" value="([^"]*)">', rendered
        )
        assert companion, "the Trauma checkbox has no hidden companion (CR-01)"

        form = _form_from_case(COMPLETE_CASE)
        form.pop("trauma", None)  # an unchecked checkbox is not a successful control...
        form["trauma"] = companion.group(1)  # ...its paired hidden field IS submitted
        body = _post(_base(server) + "/case", form)

    assert 'class="priority-card"' in body, "the unchecked default did not render a card"
    assert 'class="approval-gate"' in body, "the unchecked default did not render the gate"
    assert "A scored vital is missing" not in body
    assert injected_store.rows == []


def test_out_of_range_vital_renders_the_schema_message(
    tmp_path: Path, injected_store: Any
) -> None:
    """An invalid field surfaces the ONE schema's own rejection; nothing is scored (D10-13)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        form = _form_from_case(COMPLETE_CASE)
        form["respiratory_rate"] = "500"
        body = _post(_base(server) + "/case", form)

        assert "Check the highlighted field and try again." in body
        assert "Suggested priority" not in body
        assert injected_store.rows == []


def test_form_to_case_routes_a_bad_numeric_through_the_schema() -> None:
    """``form_to_case`` never pre-casts: a bad numeric is a ``ValidationError`` (CR-01).

    A bare ``int()``/``float()`` pre-cast would raise a plain ``ValueError`` the handler
    does not catch; routing the raw string through the ONE schema keeps every rejection a
    ``ValidationError`` the surface renders.
    """
    for bad in ("1e2", "abc", "40.5"):
        with pytest.raises(ValidationError):
            form_to_case({"age_years": bad})


def test_scientific_notation_vital_renders_the_schema_message(
    tmp_path: Path, injected_store: Any
) -> None:
    """A browser-reachable ``1e2`` in a ``type=number`` field surfaces the schema message.

    With no ``step`` the browser accepts scientific notation and submits the raw string, so
    the request must render the ONE schema's rejection rather than crash the handler and
    drop the connection (CR-01).
    """
    with _running_server(tmp_path / "checkpoints.db") as server:
        form = _form_from_case(COMPLETE_CASE)
        form["heart_rate"] = "1e2"
        body = _post(_base(server) + "/case", form)

    assert "heart_rate" in body
    assert "Check the highlighted field and try again." in body
    assert 'class="priority-card"' not in body
    assert injected_store.rows == []


def test_non_numeric_vital_renders_the_schema_message(
    tmp_path: Path, injected_store: Any
) -> None:
    """A non-numeric raw value surfaces the schema message; the handler never drops (CR-01)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        form = _form_from_case(COMPLETE_CASE)
        form["age_years"] = "abc"
        body = _post(_base(server) + "/case", form)

    assert "age_years" in body
    assert "Check the highlighted field and try again." in body
    assert 'class="priority-card"' not in body
    assert injected_store.rows == []


def test_malformed_request_renders_the_failure_panel(
    tmp_path: Path, injected_store: Any
) -> None:
    """A bad ``Content-Length`` or a non-UTF-8 body fails cleanly, never by dropping (WR-01)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        bad_length = (
            b"POST /case HTTP/1.1\r\nHost: x\r\nContent-Length: abc\r\n"
            b"Connection: close\r\n\r\n"
        )
        response = _raw_post(server, bad_length)
        assert b"HTTP/1." in response, "the handler dropped the connection on a bad length"
        assert b"The case could not be scored." in response

        bad_body = (
            b"POST /case HTTP/1.1\r\nHost: x\r\nContent-Length: 4\r\n"
            b"Connection: close\r\n\r\n\xff\xfe\xfd\xfc"
        )
        response = _raw_post(server, bad_body)
        assert b"HTTP/1." in response, "the handler dropped the connection on a bad body"
        assert b"The case could not be scored." in response

    assert injected_store.rows == []


def test_oversized_content_length_is_refused_without_reading(
    tmp_path: Path, injected_store: Any
) -> None:
    """A ``Content-Length`` above the cap renders the failure panel without reading (IN-01).

    An unbounded length would leave the handler blocked reading a body that never arrives,
    pinning the request thread. The cap refuses it up front with the documented panel.
    """
    with _running_server(tmp_path / "checkpoints.db") as server:
        oversized = (
            b"POST /case HTTP/1.1\r\nHost: x\r\nContent-Length: 999999999\r\n"
            b"Connection: close\r\n\r\n"
        )
        response = _raw_post(server, oversized)
        assert b"HTTP/1." in response, "the handler dropped the connection on an oversized body"
        assert b"The case could not be scored." in response
    assert injected_store.rows == []


def test_forms_carry_the_per_server_csrf_token(
    tmp_path: Path, injected_store: Any
) -> None:
    """Both the vitals form and the gate form carry the per-server CSRF token (WR-01)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        base = _base(server)
        token = _csrf_token(base)
        field = f'name="csrf_token" value="{token}"'
        assert field in _get(base + "/"), "the vitals form carries no CSRF token"
        gate = _section(_post(base + "/case", _form_from_case(COMPLETE_CASE)), "approval-gate")
        assert field in gate, "the gate form carries no CSRF token"


def test_post_without_the_csrf_token_is_refused(
    tmp_path: Path, injected_store: Any
) -> None:
    """A POST with no CSRF token renders the failure panel and writes nothing (WR-01)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        status, body = _post_status(
            _base(server) + "/case", _form_from_case(COMPLETE_CASE)
        )
    assert status == 200
    assert "The case could not be scored." in body
    assert 'class="priority-card"' not in body
    assert injected_store.rows == []


def test_post_with_a_wrong_csrf_token_is_refused(
    tmp_path: Path, injected_store: Any
) -> None:
    """A POST with an incorrect CSRF token renders the failure panel and writes nothing (WR-01)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        form = {**_form_from_case(COMPLETE_CASE), "csrf_token": "not-the-token"}
        status, body = _post_status(_base(server) + "/case", form)
    assert status == 200
    assert "The case could not be scored." in body
    assert 'class="priority-card"' not in body
    assert injected_store.rows == []


def test_cross_origin_post_is_refused(tmp_path: Path, injected_store: Any) -> None:
    """A POST carrying a foreign ``Origin`` is refused (403) and writes nothing (WR-01).

    A drive-by page can issue a cross-origin form POST (a CORS "simple request", no preflight),
    so the token alone is not enough: the origin check refuses it before dispatch.
    """
    with _running_server(tmp_path / "checkpoints.db") as server:
        base = _base(server)
        form = {**_form_from_case(COMPLETE_CASE), "csrf_token": _csrf_token(base)}
        status, _body = _post_status(
            base + "/case", form, headers={"Origin": "http://evil.example"}
        )
    assert status == 403
    assert injected_store.rows == []


def test_decision_without_the_csrf_token_cannot_commit(
    tmp_path: Path, injected_store: Any
) -> None:
    """A fabricated approve with no CSRF token commits nothing — the drive-by page is refused.

    This is the authorization gap the phase exists to close: the queue write is irreversible,
    so a cross-origin page that fabricates the approver must not reach the commit path (WR-01).
    """
    db = tmp_path / "checkpoints.db"
    paused = asyncio.run(submit_case(COMPLETE_CASE, db))
    with _running_server(db) as server:
        status, body = _post_status(
            _base(server) + "/decision",
            {
                "thread_id": paused.thread_id,
                "decision": "approve",
                "name": "Fabricated",
                "role": "attacker",
            },
        )
    assert status == 200
    assert "The case could not be scored." in body
    assert "committed to the queue" not in body
    assert injected_store.rows == []


def test_rejected_submission_repopulates_the_vitals_form(
    tmp_path: Path, injected_store: Any
) -> None:
    """A validation error preserves every entered vital, not only the complaint (WR-03)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        form = _form_from_case(COMPLETE_CASE)
        form["heart_rate"] = "999"
        body = _post(_base(server) + "/case", form)

    assert "Check the highlighted field and try again." in body
    assert 'value="40"' in body, "the age was not repopulated"
    assert 'value="999"' in body, "the rejected heart rate was not repopulated"
    assert f">{COMPLETE_CASE.complaint}</textarea>" in body, "the complaint was not repopulated"
    assert 'value="walking" selected' in body, "the mobility choice was not repopulated"
    assert 'value="alert" selected' in body, "the AVPU choice was not repopulated"
    assert injected_store.rows == []


def _schema_bound(name: str, key: str) -> Any:
    """The ``ge``/``le`` bound of a ``CaseInput`` field (the ONE schema's own bound)."""
    for meta in CaseInput.model_fields[name].metadata:
        if hasattr(meta, key):
            return getattr(meta, key)
    return None


def _bound_text(value: Any) -> str:
    """Render a numeric bound the way the form does (no trailing ``.0``)."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def test_vitals_bounds_are_derived_from_the_schema() -> None:
    """Every numeric input's min/max equals the ONE schema's own bound, never a copy (IN-04)."""
    body = desk_server.render_state()
    for name in (
        "age_years",
        "age_months",
        "height_cm",
        "respiratory_rate",
        "heart_rate",
        "systolic_bp",
        "diastolic_bp",
        "temperature_c",
        "spo2",
    ):
        low = _bound_text(_schema_bound(name, "ge"))
        high = _bound_text(_schema_bound(name, "le"))
        assert f'min="{low}" max="{high}"' in body, f"{name} bounds are not schema-derived"


# --------------------------------------------------------------- structural (Plan 10-01)


def test_no_self_commit_path_in_the_desk_package() -> None:
    """No ``desk/`` module imports the queue writer or the gated-commit host (D10-12).

    The scan recurses the WHOLE package and resolves relative imports, so neither a
    ``from ..store.queue import commit_to_queue`` nor a commit path added in a ``desk/``
    subpackage can evade the guard (WR-04).
    """
    modules = sorted(DESK_DIR.rglob("*.py"))
    assert modules, "the desk package scan visited no module"
    for path in modules:
        source = path.read_text(encoding="utf-8")
        resolved = set(resolved_imports(source, package_parts_for(path, SRC_ROOT)))
        module_offenders = resolved & _COMMIT_PATH_MODULES
        assert not module_offenders, (
            f"{path.name} imports a commit path: {sorted(module_offenders)}"
        )
        symbol_offenders = {
            name for name in resolved if name.rsplit(".", 1)[-1] in _COMMIT_SYMBOLS
        }
        assert not symbol_offenders, (
            f"{path.name} imports a commit symbol: {sorted(symbol_offenders)}"
        )


def test_commit_path_guard_resolves_relative_and_symbol_imports() -> None:
    """The guard is not vacuous: relative and symbol imports of a commit path are caught (WR-04)."""
    parts = ["triagedesk", "desk"]  # the __package__ of a desk/ module
    relative = set(resolved_imports("from ..store.queue import commit_to_queue\n", parts))
    assert "triagedesk.store.queue" in relative
    assert "triagedesk.store.queue.commit_to_queue" in relative

    symbol = set(resolved_imports("from triagedesk.mcp.server import commit_priority\n", parts))
    assert "triagedesk.mcp.server" in symbol
    assert "triagedesk.mcp.server.commit_priority" in symbol


def test_commit_path_guard_catches_literal_dynamic_imports() -> None:
    """A literal ``import_module``/``__import__`` of a commit path is caught (WR-01).

    The static scan alone would miss a dynamic import; the resolver now also reads a
    literal-argument ``importlib.import_module``/``__import__`` call. A *string-built* name is
    honestly reported as unresolvable — the guard's claim is scoped to the literal import graph
    it scans, never asserted beyond it.
    """
    parts = ["triagedesk", "desk"]
    dynamic_module = set(
        resolved_imports("importlib.import_module('triagedesk.store.queue')\n", parts)
    )
    assert "triagedesk.store.queue" in dynamic_module

    dynamic_dunder = set(
        resolved_imports("__import__('triagedesk.mcp.server')\n", parts)
    )
    assert "triagedesk.mcp.server" in dynamic_dunder

    built = set(
        resolved_imports(
            "importlib.import_module('triagedesk.store.' + 'queue')\n", parts
        )
    )
    assert "triagedesk.store.queue" not in built


def test_make_server_binds_localhost_only(tmp_path: Path) -> None:
    """The server binds ``127.0.0.1`` explicitly, never a wildcard (D10-03)."""
    server = make_server("127.0.0.1", 0, tmp_path / "checkpoints.db")
    try:
        host = server.server_address[0]
        assert host == "127.0.0.1"
        assert host not in ("", "0.0.0.0", "::")
    finally:
        server.server_close()


def test_serve_declares_a_localhost_default() -> None:
    """``serve``'s declared default host is loopback (D10-03)."""
    assert inspect.signature(serve).parameters["host"].default == "127.0.0.1"


def test_non_loopback_bind_is_refused(tmp_path: Path) -> None:
    """A wildcard/routable bind fails closed, never exposing the surface (WR-02, D10-03)."""
    for host in ("0.0.0.0", "::", "192.0.2.1", "localhost"):
        with pytest.raises(ValueError):
            make_server(host, 0, tmp_path / "checkpoints.db")


def test_non_loopback_bind_requires_explicit_opt_in(tmp_path: Path) -> None:
    """The only route to a non-loopback bind is the explicit opt-in flag (WR-02)."""
    server = make_server(
        "0.0.0.0", 0, tmp_path / "checkpoints.db", allow_non_loopback=True
    )
    try:
        assert server.server_address[0] == "0.0.0.0"
    finally:
        server.server_close()


def test_serve_refuses_a_non_loopback_host() -> None:
    """``serve`` fails closed on a non-loopback host before binding (WR-02)."""
    with pytest.raises(ValueError):
        serve(host="0.0.0.0", port=0)


def test_desk_command_refuses_a_non_loopback_host(tmp_path: Path) -> None:
    """``main(['desk', '--host', '0.0.0.0', …])`` reports the refusal and exits non-zero (WR-02)."""
    code = main(
        ["desk", "--host", "0.0.0.0", "--port", "0", "--db", str(tmp_path / "c.db")]
    )
    assert code == 1


def test_desk_entry_point_hardens_offline_before_serve(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """``main(['desk', …])`` runs ``harden_offline()`` BEFORE the handler is reached (WR-06)."""
    events: list[str] = []

    def fake_harden() -> None:
        events.append("harden")

    def fake_serve(**kwargs: Any) -> None:
        events.append("serve")

    # ``cli`` binds ``harden_offline`` into its own namespace at import time, so the effective
    # patch target is ``triagedesk.cli.harden_offline``; the handler is imported lazily inside
    # ``main``, so its patch target is the ``triagedesk.desk.server`` attribute (WR-06).
    monkeypatch.setattr("triagedesk.cli.harden_offline", fake_harden)
    monkeypatch.setattr("triagedesk.desk.server.serve", fake_serve)

    code = main(["desk", "--port", "0", "--db", str(tmp_path / "checkpoints.db")])

    assert code == 0
    assert events == ["harden", "serve"]


def test_served_assets_make_no_external_request() -> None:
    """Neither asset carries a URL, an off-host script, a font import or a fetch (D10-03)."""
    sources = {
        "index.html": (ASSET_DIR / "index.html").read_text(encoding="utf-8"),
        "styles.css": (ASSET_DIR / "styles.css").read_text(encoding="utf-8"),
    }
    for name, source in sources.items():
        assert "http://" not in source, name
        assert "https://" not in source, name
        assert "@import" not in source, name
        assert "url(" not in source, name
    assert "<script src=" not in sources["index.html"]
    assert "-apple-system" in sources["styles.css"]
    assert "BlinkMacSystemFont" in sources["styles.css"]


def test_untrusted_complaint_escapes_markup(tmp_path: Path, injected_store: Any) -> None:
    """The untrusted complaint cannot inject markup: escaped form present, raw tag absent."""
    markup = '<img src=x onerror="alert(1)">'
    with _running_server(tmp_path / "checkpoints.db") as server:
        form = _form_from_case(COMPLETE_CASE)
        form["complaint"] = markup
        body = _post(_base(server) + "/case", form)

        assert html.escape(markup) in body
        assert markup not in body


def test_index_html_loading_swap_on_submit() -> None:
    """``index.html`` carries the loading copy and a submit handler that disables the CTA."""
    source = (ASSET_DIR / "index.html").read_text(encoding="utf-8")
    assert "Getting the suggested priority…" in source
    assert "addEventListener('submit'" in source
    assert "disabled = true" in source

    script = source.split("<script>", 1)[1].split("</script>", 1)[0]
    assert "$" not in script, "the inline script must carry no placeholder character"


# ------------------------------------- Task 1: the banner, the deferred terminal, evidence


def test_banner_trigger_reads_only_the_typed_signal() -> None:
    """The ONE banner rule is the typed signal — never a heuristic (D10-09)."""
    assert desk_server.banner_trigger({"no_match": True}) == "no_match"
    assert (
        desk_server.banner_trigger(
            {"no_match": False, "confidence": ConfidenceResult(deferral=True)}
        )
        == "deferral"
    )
    assert (
        desk_server.banner_trigger(
            {"no_match": False, "confidence": ConfidenceResult(deferral=False)}
        )
        is None
    )
    # Never evidence.no_match ("no excerpt matched" — a different fact).
    assert desk_server.banner_trigger({"evidence": EvidenceResult(no_match=True)}) is None
    # Never missing_vitals alone (that is the recovery signal's job).
    assert (
        desk_server.banner_trigger(
            {"priority": PriorityResult(missing_vitals=["heart_rate"])}
        )
        is None
    )


def test_terminal_kind_prefers_the_deferral_channel() -> None:
    """A deferral wins over a co-present escalation — a deferral routes to escalate (D10-17)."""
    state: Mapping[str, Any] = {
        "confidence": ConfidenceResult(deferral=True),
        "escalation": Escalation(reason="case could not be safely scored"),
    }
    assert desk_server.terminal_kind(state) == "deferred"
    assert desk_server.terminal_kind({"escalation": Escalation(reason="x")}) == "escalated"
    assert desk_server.terminal_kind({"recovery": RecoveryRequest(reason="y")}) == "recovery"
    assert desk_server.terminal_kind({}) is None


def test_deferred_case_renders_the_banner_read_only_card_and_no_gate(
    tmp_path: Path, injected_store: Any
) -> None:
    """The E-09 class is a loud banner on a READ-ONLY card with NO gate (UX-01, D10-17)."""
    case = _e09()
    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(_base(server) + "/case", _form_from_case(case.case))

    assert BANNER_HEADLINE in body, "the verbatim banner headline did not render"
    assert NO_MATCH_BODY in body
    assert LOW_CONFIDENCE_BODY not in body
    assert 'class="priority-card"' in body, "the deferred path rendered no read-only card"
    assert "Not confirmed and not queued" in body
    assert "This case was deferred for human review — no priority was committed." in body
    assert 'class="approval-gate"' not in body, "the deferred path wrongly offered a gate"
    for control in (
        "Your decision",
        "Approve suggestion",
        "Edit colour",
        "Dismiss (commit nothing)",
    ):
        assert control not in body, f"the deferred path rendered a gate control: {control}"
    assert injected_store.rows == []


def test_banner_body_is_trigger_conditional() -> None:
    """A deferral-only state renders the low-confidence body, never the no-match body (D10-09)."""
    body = desk_server.render_state(
        _run_from_state(
            no_match=False,
            confidence=ConfidenceResult(deferral=True),
            priority=PriorityResult(),
        )
    )
    assert BANNER_HEADLINE in body
    assert LOW_CONFIDENCE_BODY in body
    assert NO_MATCH_BODY not in body


def test_no_banner_for_evidence_no_match_or_missing_vitals() -> None:
    """The banner never fires on ``evidence.no_match`` or ``missing_vitals`` alone (D10-09)."""
    evidence_only = desk_server.render_state(
        _run_from_state(
            no_match=False,
            confidence=ConfidenceResult(deferral=False),
            evidence=EvidenceResult(no_match=True),
            priority=PriorityResult(),
        )
    )
    assert BANNER_HEADLINE not in evidence_only

    missing_only = desk_server.render_state(
        _run_from_state(
            no_match=False,
            priority=PriorityResult(missing_vitals=["heart_rate"]),
        )
    )
    assert BANNER_HEADLINE not in missing_only


def test_evidence_list_renders_each_passage_in_rank_order(
    tmp_path: Path, injected_store: Any
) -> None:
    """A scored case renders one ranked evidence row per passage (UX-02, D10-07)."""
    complaint = "central chest pain and shortness of breath"
    case = COMPLETE_CASE.model_copy(update={"complaint": complaint})
    expected = retrieval.retrieve(complaint).passages
    assert len(expected) >= 2, "the fixture complaint did not retrieve multiple passages"

    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(_base(server) + "/case", _form_from_case(case))

    card = _section(body, "priority-card")
    assert "Evidence from the SATS knowledge base:" in card
    indices = [card.index(passage.label) for passage in expected]
    assert indices == sorted(indices), "the evidence rows are not in rank order"
    for passage in expected:
        assert passage.label in card, f"missing evidence label: {passage.label}"
        assert passage.citation in card, f"missing evidence citation: {passage.citation}"


def test_evidence_list_renders_the_no_evidence_line(
    tmp_path: Path, injected_store: Any
) -> None:
    """Zero passages render the verbatim no-evidence line, never an empty box (UX-02)."""
    case = _e09()
    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(_base(server) + "/case", _form_from_case(case.case))
    card = _section(body, "priority-card")
    assert "No evidence excerpt matched this complaint." in card


# ------------------------------------------- Task 2: the fail-safe gate (UX-03, D10-10/D10-13)


def test_gate_carries_the_paused_thread_id(tmp_path: Path, injected_store: Any) -> None:
    """The gate's hidden ``thread_id`` is the submit's ``PausedRun.thread_id`` (D10-11)."""
    db = tmp_path / "checkpoints.db"
    paused = asyncio.run(submit_case(COMPLETE_CASE, db))
    assert paused.paused and paused.payload is not None
    assert _thread_id(desk_server.render_state(paused)) == paused.thread_id


def test_dismiss_commits_nothing(tmp_path: Path, injected_store: Any) -> None:
    """A dismiss returns ``refused=True``/``committed=False`` and writes no row (D10-10)."""
    db = tmp_path / "checkpoints.db"
    paused = asyncio.run(submit_case(COMPLETE_CASE, db))
    thread_id = _thread_id(desk_server.render_state(paused))
    assert thread_id == paused.thread_id

    result = asyncio.run(decide(thread_id, {"decision": "dismiss"}, db))
    commit = result["commit_result"]
    assert commit.refused is True
    assert commit.committed is False
    assert injected_store.rows == []

    rendered = desk_server.render_state(result=result, form_values={"decision": "dismiss"})
    assert "Dismissed — nothing has been committed." in rendered


def test_a_failure_is_never_an_approve(
    tmp_path: Path, injected_store: Any, monkeypatch: Any
) -> None:
    """A server/graph failure renders the error copy and leaves the queue untouched (fail-safe)."""

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("graph exploded")

    monkeypatch.setattr("triagedesk.desk.server.decide", boom)
    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(
            _base(server) + "/decision",
            {"thread_id": "whatever", "decision": "approve", "name": "N", "role": "R"},
        )

    assert 'class="state-panel state-error"' in body
    assert (
        "The case could not be scored. Nothing has been committed. Try again, or check the "
        "desk log." in body
    )
    assert injected_store.rows == []


def test_absent_thread_renders_an_error_panel(tmp_path: Path, injected_store: Any) -> None:
    """A decision whose thread has no pending gate renders the gate's own refusal (D10-11)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(
            _base(server) + "/decision",
            {"thread_id": "absent-thread", "decision": "approve", "name": "N", "role": "R"},
        )
    assert 'class="state-panel state-error"' in body
    assert "no pending approval gate" in body
    assert injected_store.rows == []


def test_decision_without_a_thread_id_renders_the_error_panel(
    tmp_path: Path, injected_store: Any
) -> None:
    """A decision POST with no thread id renders the error panel and writes nothing (D10-11)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(
            _base(server) + "/decision",
            {"decision": "approve", "name": "N", "role": "R"},
        )
    assert 'class="state-panel state-error"' in body
    assert "There is no paused case to decide. Submit the vitals first." in body
    assert injected_store.rows == []


def test_state_panel_escapes_its_copy() -> None:
    """A state panel escapes its own copy, so a caller cannot leak markup (IN-05)."""
    markup = '<img src=x onerror="alert(1)">'
    body = desk_server.render_state(error=markup)
    assert html.escape(markup) in body
    assert markup not in body


def test_timeout_is_no_approve(tmp_path: Path, injected_store: Any) -> None:
    """No decision POST leaves the queue empty; the gate preselects no decision/colour (D10-10)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(_base(server) + "/case", _form_from_case(COMPLETE_CASE))
        # deliberately no /decision POST — a timeout is "no decision ever arrives"

    assert injected_store.rows == [], "a timeout committed a queue row"
    gate = _section(body, "approval-gate")
    assert "checked" not in gate, "the gate preselected a colour"
    assert "selected" not in gate, "the gate preselected a decision"
    assert 'id="gate-timeout"' in body
    assert "No decision was made — nothing has been committed." in body


def test_edit_set_equals_the_gate_set(tmp_path: Path, injected_store: Any) -> None:
    """The edit control offers exactly the colours the gate validates against (D10-18)."""
    colours = desk_server.editable_colours()
    derived = sorted({band.colour for band in get_tews().tews_to_colour})
    assert colours == derived
    assert "BLUE" not in colours, "the gate would refuse a BLUE edit"

    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(_base(server) + "/case", _form_from_case(COMPLETE_CASE))
    gate = _section(body, "approval-gate")
    rendered = sorted(re.findall(r'name="colour" value="([^"]+)"', gate))
    assert rendered == colours

    # The SAME set the token validator accepts: every offered colour is a valid edit.
    for colour in colours:
        ApprovalToken(
            decision="edit",
            approved_at=datetime.now(UTC),
            approved_by="Nurse Demo",
            role="triage nurse",
            final_colour=colour,
        )


def test_schema_rejection_renders_the_message_and_writes_nothing(
    tmp_path: Path, injected_store: Any
) -> None:
    """An invalid field surfaces the ONE schema's own message; nothing is scored (D10-13)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        form = _form_from_case(COMPLETE_CASE)
        form["heart_rate"] = "999"
        body = _post(_base(server) + "/case", form)

    assert "heart_rate" in body
    assert "Check the highlighted field and try again." in body
    assert 'class="priority-card"' not in body
    assert injected_store.rows == []


def test_existed_repeat_submission_reuses_the_thread(
    tmp_path: Path, injected_store: Any
) -> None:
    """A repeat submission re-renders the card and gate with the SAME thread id (D10-19)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        base = _base(server)
        first = _post(base + "/case", _form_from_case(COMPLETE_CASE))
        second = _post(base + "/case", _form_from_case(COMPLETE_CASE))

    assert _thread_id(first) == _thread_id(second)
    assert 'class="priority-card"' in second
    assert 'class="approval-gate"' in second
    assert injected_store.rows == [], "a repeat submission wrote a queue row"


def test_repeat_submission_after_commit_adds_no_row(
    tmp_path: Path, injected_store: Any
) -> None:
    """A repeat after a commit shows the gate's own outcome and adds no second row (D10-19)."""
    with _running_server(tmp_path / "checkpoints.db") as server:
        base = _base(server)
        first = _post(base + "/case", _form_from_case(COMPLETE_CASE))
        _post(
            base + "/decision",
            {
                "thread_id": _thread_id(first),
                "decision": "approve",
                "name": "Nurse Demo",
                "role": "triage nurse",
            },
        )
        assert len(injected_store.rows) == 1
        again = _post(base + "/case", _form_from_case(COMPLETE_CASE))

    assert 'class="approval-gate"' not in again
    assert "committed case" in again
    assert len(injected_store.rows) == 1, "a repeat submission added a second queue row"


def test_blank_identity_surfaces_the_builder_error(
    tmp_path: Path, injected_store: Any
) -> None:
    """A blank name surfaces the ONE decision builder's error and writes nothing (WR-06)."""
    db = tmp_path / "checkpoints.db"
    paused = asyncio.run(submit_case(COMPLETE_CASE, db))
    with _running_server(db) as server:
        body = _post(
            _base(server) + "/decision",
            {
                "thread_id": paused.thread_id,
                "decision": "approve",
                "name": "   ",
                "role": "triage nurse",
            },
        )
    assert 'class="state-panel state-error"' in body
    assert "approver" in body
    assert injected_store.rows == []


def test_missing_edit_colour_surfaces_the_builder_error(
    tmp_path: Path, injected_store: Any
) -> None:
    """A missing edit colour surfaces the builder's error and writes nothing (D10-18)."""
    db = tmp_path / "checkpoints.db"
    paused = asyncio.run(submit_case(COMPLETE_CASE, db))
    with _running_server(db) as server:
        body = _post(
            _base(server) + "/decision",
            {
                "thread_id": paused.thread_id,
                "decision": "edit",
                "name": "Nurse Demo",
                "role": "triage nurse",
            },
        )
    assert 'class="state-panel state-error"' in body
    assert "colour" in body
    assert injected_store.rows == []


def test_baseline_why_vitals_row_is_never_an_empty_list(
    tmp_path: Path, injected_store: Any
) -> None:
    """An all-normal-vitals case renders the scorer's ``tews_baseline`` row (UI-SPEC)."""
    case = _e09()
    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(_base(server) + "/case", _form_from_case(case.case))

    card = _section(body, "priority-card")
    match = matcher.match_discriminators(case.case.complaint)
    priority = scorer.score_priority(case.case, match.matched_ids)
    baseline = next(
        rule for rule in priority.triggered_rules if rule.rule_id == "tews_baseline"
    )
    assert baseline.detail in card, "the baseline why-vitals detail did not render"
    assert baseline.citation in card, "the baseline why-vitals citation did not render"


# ------------------------------------- Task 3: copy and hermeticity proofs (D10-05, D10-15)


def _rendered_card_and_banner(tmp_path: Path) -> tuple[str, str, str]:
    """The card/banner regions for a scored case and the deferred case (the scan subject)."""
    with _running_server(tmp_path / "scored.db") as server:
        scored = _post(_base(server) + "/case", _form_from_case(COMPLETE_CASE))
    case = _e09()
    with _running_server(tmp_path / "deferred.db") as server:
        deferred = _post(_base(server) + "/case", _form_from_case(case.case))
    return scored, deferred, _banner_region(deferred)


def test_rendered_copy_carries_no_forbidden_token(
    tmp_path: Path, injected_store: Any
) -> None:
    """No rendered card/banner string or served asset carries a prohibited token (D10-05).

    The ONE declared exception is the verbatim complaint echo — the nurse's own words shown
    as typed, covered instead by the escaping proof — so the scan subject is the card region,
    the banner region and the surface's own copy, never the complaint field.
    """
    scored, deferred, banner = _rendered_card_and_banner(tmp_path)
    subject = "\n".join(
        [
            _section(scored, "priority-card"),
            _section(deferred, "priority-card"),
            banner,
            (ASSET_DIR / "index.html").read_text(encoding="utf-8"),
            (ASSET_DIR / "styles.css").read_text(encoding="utf-8"),
        ]
    )
    assert subject.strip(), "the token scan subject is empty (a vacuous guard)"

    forbidden = prohibited_tokens()
    assert forbidden, "the ONE prohibited-token vocabulary is empty"
    for token in forbidden:
        assert not re.search(rf"\b{re.escape(token)}\b", subject.lower()), (
            f"a rendered string carries the prohibited token {token!r}"
        )


def test_no_rendered_string_shows_a_percentage(
    tmp_path: Path, injected_store: Any
) -> None:
    """No card, banner or state-panel string carries a percent sign or probability word."""
    scored, deferred, _ = _rendered_card_and_banner(tmp_path)
    rendered = scored + deferred
    assert "%" not in rendered
    for word in ("percent", "probability", "probable"):
        assert not re.search(rf"\b{word}\b", rendered.lower()), word


def test_colour_label_accompanies_every_rendered_colour(
    tmp_path: Path, injected_store: Any
) -> None:
    """Every rendered colour carries its name as text and the generic class (D10-08)."""
    db = tmp_path / "checkpoints.db"
    paused = asyncio.run(submit_case(COMPLETE_CASE, db))
    assert paused.payload is not None
    colour = str(paused.payload["colour"])
    card = _section(desk_server.render_state(paused), "priority-card")
    assert f'class="colour-block colour-{colour.lower()}"' in card
    assert f'<span class="colour-name">{colour}</span>' in card
    assert f'<span class="value">{colour}</span>' in card

    # The colour swatch class is escaped like every other rendered value (IN-01).
    hostile = PausedRun(
        thread_id="t",
        config={},
        result={},
        payload={"colour": 'red" onmouseover="alert(1)'},
        paused=True,
        existed=False,
    )
    hostile_card = _section(desk_server.render_state(hostile), "priority-card")
    assert 'onmouseover="alert(1)' not in hostile_card
    assert "colour-block colour-red&quot; onmouseover=&quot;alert(1)" in hostile_card

    # The deferred read-only card renders its colour with its name and class too.
    case = _e09()
    with _running_server(tmp_path / "deferred.db") as server:
        deferred = _post(_base(server) + "/case", _form_from_case(case.case))
    deferred_card = _section(deferred, "priority-card")
    assert "colour-block colour-" in deferred_card
    assert '<span class="colour-name">' in deferred_card


def test_submit_path_launches_no_borrowed_store(
    tmp_path: Path, injected_store: Any, monkeypatch: Any
) -> None:
    """The bridge's full submit+decision path launches no borrowed store (D10-15)."""
    launched: list[object] = []

    def spy(*args: object, **kwargs: object) -> object:
        launched.append((args, kwargs))
        raise AssertionError("the desk surface launched the borrowed store")

    monkeypatch.setattr("triagedesk.store.borrowed.open_borrowed_store", spy)
    with _running_server(tmp_path / "checkpoints.db") as server:
        base = _base(server)
        body = _post(base + "/case", _form_from_case(COMPLETE_CASE))
        _post(
            base + "/decision",
            {
                "thread_id": _thread_id(body),
                "decision": "approve",
                "name": "Nurse Demo",
                "role": "triage nurse",
            },
        )

    assert launched == []
    assert len(injected_store.rows) == 1


def test_deferred_end_to_end_is_read_only(tmp_path: Path, injected_store: Any) -> None:
    """The deferred path renders the banner + read-only card, no gate, no row, no commit."""
    case = _e09()
    with _running_server(tmp_path / "checkpoints.db") as server:
        body = _post(_base(server) + "/case", _form_from_case(case.case))

    assert BANNER_HEADLINE in body
    assert 'class="priority-card"' in body
    assert 'class="approval-gate"' not in body
    assert injected_store.rows == []
    assert injected_store.calls == [], "a deferred case reached the queue store"


def test_served_css_declares_wrapping_rules() -> None:
    """The served CSS wraps long strings and never clips the gate controls (UI-SPEC backstops)."""
    css = (ASSET_DIR / "styles.css").read_text(encoding="utf-8")
    assert "nowrap" not in css, "the CSS clips a label with white-space: nowrap"

    for selector in (".evidence-list li", ".banner-headline", ".complaint-block .value"):
        block = _css_block(css, selector)
        assert "overflow-wrap" in block or "word-break" in block, selector

    banner = _css_block(css, ".banner-headline")
    assert not re.search(r"(?<!-)\bheight\s*:", banner), "the banner headline has a fixed height"

    for selector in ("button", ".gate-actions"):
        block = _css_block(css, selector)
        assert not re.search(r"(?<!-)\bwidth\s*:", block), f"{selector} has a fixed width"


def test_css_declares_exactly_the_editable_colour_swatches() -> None:
    """The stylesheet declares a swatch for exactly the editable colours — no dead rule (IN-02)."""
    css = (ASSET_DIR / "styles.css").read_text(encoding="utf-8")
    swatches = set(re.findall(r"\.colour-([a-z]+)\s*\{[^}]*background:", css))
    expected = {colour.lower() for colour in desk_server.editable_colours()}
    assert swatches == expected, (
        f"CSS swatches {sorted(swatches)} do not equal the editable colours {sorted(expected)}"
    )
