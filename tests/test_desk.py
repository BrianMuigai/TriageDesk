"""The desk surface end-to-end and structural proof suite (Plan 10-01, UX-02…UX-04).

Proves the phase's tracer slice hermetically (D10-15): the bridge is driven over loopback
ONLY, through the shared conftest seams (the injected in-memory store and a ``tmp_path``
checkpoint file), so no model, no borrowed subprocess and no repo-root artefact is touched.

Two halves:

* the end-to-end proof — a GET renders the empty state, a vitals POST renders the graph's
  suggested priority framed as a suggestion with its adjacent citations, and a named-human
  approve lands EXACTLY one queue row through the gated tool;
* the structural proofs — the ``desk/`` package has no commit path, binds loopback only,
  hardens offline before its handler is reached, makes no external request, escapes the
  untrusted complaint, and swaps the CTA label while a submit is in flight.
"""

from __future__ import annotations

import asyncio
import contextlib
import html
import inspect
import re
import threading
import urllib.parse
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from conftest import COMPLETE_CASE, imported_modules
from triagedesk.cli import main
from triagedesk.core.schema import CaseInput
from triagedesk.desk import server as desk_server
from triagedesk.desk.server import make_server, serve, submit_case

DESK_DIR = Path(desk_server.__file__).parent
ASSET_DIR = DESK_DIR / "static"

# The modules a desk module must NEVER import: the queue writer and the module that hosts the
# gated commit tool. The only route to a queue row is the resumed interrupt through that tool
# (D10-11/D10-12), so a direct import here would be a second, un-audited write path.
_COMMIT_PATH_MODULES = frozenset({"triagedesk.store.queue", "triagedesk.mcp.server"})


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


def _post(url: str, data: dict[str, str]) -> str:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    with urllib.request.urlopen(url, data=encoded) as response:
        return response.read().decode("utf-8")


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


# ------------------------------------------------------------------ end-to-end (Task 1)


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


# --------------------------------------------------------------- structural (Task 2)


def test_no_self_commit_path_in_the_desk_package() -> None:
    """No ``desk/`` module imports the queue writer or the gated-commit host (D10-12)."""
    modules = sorted(DESK_DIR.glob("*.py"))
    assert modules, "the desk package scan visited no module"
    for path in modules:
        imported = set(imported_modules(path.read_text(encoding="utf-8")))
        offenders = imported & _COMMIT_PATH_MODULES
        assert not offenders, f"{path.name} imports a commit path: {sorted(offenders)}"


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
