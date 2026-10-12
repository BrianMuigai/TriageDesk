"""The desk surface end-to-end proof suite (Plan 10-01, UX-02…UX-04).

Proves the phase's tracer slice hermetically (D10-15): the bridge is driven over loopback
ONLY, through the shared conftest seams (the injected in-memory store and a ``tmp_path``
checkpoint file), so no model, no borrowed subprocess and no repo-root artefact is touched.

The end-to-end proof: a GET renders the empty state, a vitals POST renders the graph's
suggested priority framed as a suggestion with its adjacent citations, and a named-human
approve lands EXACTLY one queue row through the gated tool.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import threading
import urllib.parse
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from conftest import COMPLETE_CASE
from triagedesk.core.schema import CaseInput
from triagedesk.desk import server as desk_server
from triagedesk.desk.server import make_server, submit_case

DESK_DIR = Path(desk_server.__file__).parent


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
