"""The chat workspace and note-intake proofs (quick task 261116-u9l).

The desk now presents a conversation beside the structured vitals form. These proofs keep the
conversation truthful and presentation-only: the composer never scores, approves or commits;
an offline note becomes the complaint; an online note is read by the ONE grounded extraction
seam and the nurse's typed values still win; the handover is the graph's typed card.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest

from conftest import COMPLETE_CASE
from test_desk import _base, _form_from_case, _post, _running_server, _section, _thread_id
from triagedesk.core.schema import CaseInput, ExtractionResult
from triagedesk.desk import server as desk_server
from triagedesk.desk.copy import (
    _CHAT_NOTE_EMPTY,
    _CHAT_NOTE_FAILED,
    _CHAT_NOTE_OFFLINE,
)
from triagedesk.desk.forms import _VITALS_GROUPS, _VITALS_LAYOUT


def _stub_extraction(**case_fields: Any) -> ExtractionResult:
    """A grounded extraction result for the note tests (no model, no scorer)."""
    return ExtractionResult(case=CaseInput(**case_fields))


def _form_block(body: str) -> str:
    """The inner HTML of the structured vitals form."""
    return body.split('<form id="vitals-form"', 1)[1].split("</form>", 1)[0]


def test_the_page_renders_the_chat_workspace() -> None:
    """The served page carries the app shell, a live log, the composer, and the scored form."""
    body = desk_server.render_state()

    assert 'class="app-shell"' in body
    assert 'role="log"' in body
    assert 'class="chat-message assistant"' in body
    assert "TriageDesk assistant" in body
    assert 'id="note-input"' in body
    assert 'form="vitals-form"' in body
    assert 'value="note"' in body
    assert 'class="intake-panel"' in body
    assert '<form id="vitals-form"' in body
    assert "Structured intake" in body
    assert 'class="waiting-page"' not in body


def test_form_groups_partition_the_clinical_layout() -> None:
    """Every grouped control appears once, in the ONE declared clinical order."""
    grouped = [name for _, names in _VITALS_GROUPS for name in names]
    assert grouped == [name for name, _ in _VITALS_LAYOUT]
    assert len(grouped) == len(set(grouped))


def test_note_offline_becomes_the_complaint_without_scoring(
    tmp_path: Path, injected_store: Any
) -> None:
    """Offline, a note is the complaint; the vitals stay the nurse's job and nothing is scored."""
    with _running_server(tmp_path / "chat.db", injected_store) as server:
        body = _post(
            _base(server) + "/case",
            {"action": "note", "note": "coughing and fast breathing since last night"},
        )

    block = _form_block(body)
    assert "coughing and fast breathing since last night" in block
    assert _CHAT_NOTE_OFFLINE in body
    assert 'class="priority-card"' not in body
    assert 'class="approval-gate"' not in body
    assert injected_store.rows == []


def test_note_online_prefills_from_the_grounded_read(
    tmp_path: Path, injected_store: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Online, the note is read through the extraction seam and the form is prefilled."""

    async def fake_extract(note: str) -> ExtractionResult:
        assert note == "40M, RR 24, HR 118, BP 108/70, temp 38.9, chest pain"
        return _stub_extraction(
            age_years=40,
            respiratory_rate=24,
            heart_rate=118,
            systolic_bp=108,
            diastolic_bp=70,
            temperature_c=38.9,
            complaint="chest pain",
        )

    monkeypatch.setattr(desk_server, "extract_note", fake_extract)
    with _running_server(tmp_path / "note-online.db", injected_store) as server:
        server.online = True
        body = _post(
            _base(server) + "/case",
            {
                "action": "note",
                "note": "40M, RR 24, HR 118, BP 108/70, temp 38.9, chest pain",
            },
        )

    assert "Here is what I read" in body
    assert "chest pain" in body
    assert re.search(r'id="age_years"[^>]*value="40"', body)
    assert re.search(r'id="respiratory_rate"[^>]*value="24"', body)
    assert re.search(r'id="heart_rate"[^>]*value="118"', body)
    assert 'class="priority-card"' not in body
    assert 'class="approval-gate"' not in body
    assert injected_store.rows == []


def test_note_prefill_keeps_the_nurses_typed_values(
    tmp_path: Path, injected_store: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The note fills blanks; a value the nurse typed is never overwritten by the model."""

    async def fake_extract(_: str) -> ExtractionResult:
        return _stub_extraction(
            respiratory_rate=60,
            heart_rate=118,
            complaint="model words",
        )

    monkeypatch.setattr(desk_server, "extract_note", fake_extract)
    with _running_server(tmp_path / "note-wins.db", injected_store) as server:
        server.online = True
        body = _post(
            _base(server) + "/case",
            {
                "action": "note",
                "note": "a note",
                "respiratory_rate": "24",
                "complaint": "nurse words",
            },
        )

    block = _form_block(body)
    assert re.search(r'id="respiratory_rate"[^>]*value="24"', block)
    assert re.search(r'id="heart_rate"[^>]*value="118"', block)
    assert "nurse words" in block
    assert "model words" not in block


def test_note_online_failure_is_reported_and_never_scored(
    tmp_path: Path, injected_store: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed read leaves the form untouched and renders no card or gate."""

    async def fake_extract(_: str) -> ExtractionResult:
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(desk_server, "extract_note", fake_extract)
    with _running_server(tmp_path / "note-failed.db", injected_store) as server:
        server.online = True
        body = _post(
            _base(server) + "/case",
            {"action": "note", "note": "a note the model cannot read"},
        )

    assert _CHAT_NOTE_FAILED in body
    assert 'class="priority-card"' not in body
    assert 'class="approval-gate"' not in body
    assert injected_store.rows == []


def test_note_requires_text(tmp_path: Path, injected_store: Any) -> None:
    """An empty composer message is a refusal, never a case submission."""
    with _running_server(tmp_path / "note-empty.db", injected_store) as server:
        body = _post(_base(server) + "/case", {"action": "note", "note": "   "})

    assert _CHAT_NOTE_EMPTY in body
    assert 'class="priority-card"' not in body
    assert 'class="approval-gate"' not in body
    assert injected_store.rows == []


def test_the_gate_focuses_the_approver_name(tmp_path: Path, injected_store: Any) -> None:
    """A rendered gate focuses the next action — the named decision — not the vitals."""
    with _running_server(tmp_path / "gate-focus.db", injected_store) as server:
        body = _post(_base(server) + "/case", _form_from_case(COMPLETE_CASE))

    gate = _section(body, "approval-gate")
    assert gate.count("autofocus") == 1
    assert re.search(r'id="approver-name"[^>]*\bautofocus\b', gate)
    assert body.count("autofocus") == 1


def test_approve_with_a_selected_colour_is_refused(tmp_path: Path, injected_store: Any) -> None:
    """A colour belongs to Edit colour; Approve must not silently discard the selection."""
    with _running_server(tmp_path / "approve-colour.db", injected_store) as server:
        base = _base(server)
        body = _post(base + "/case", _form_from_case(COMPLETE_CASE))
        thread_id = _thread_id(body)
        decided = _post(
            base + "/decision",
            {
                "thread_id": thread_id,
                "decision": "approve",
                "name": "Nurse Demo",
                "role": "triage nurse",
                "colour": "YELLOW",
            },
        )

    assert "A colour is only used with Edit colour" in decided
    assert injected_store.rows == []


def test_edit_with_a_selected_colour_commits_that_colour(
    tmp_path: Path, injected_store: Any
) -> None:
    """Edit is the one action that records a changed colour."""
    with _running_server(tmp_path / "edit-colour.db", injected_store) as server:
        base = _base(server)
        body = _post(base + "/case", _form_from_case(COMPLETE_CASE))
        thread_id = _thread_id(body)
        decided = _post(
            base + "/decision",
            {
                "thread_id": thread_id,
                "decision": "edit",
                "name": "Nurse Demo",
                "role": "triage nurse",
                "colour": "YELLOW",
            },
        )

    assert "Edited to YELLOW" in decided
    assert len(injected_store.rows) == 1
    assert injected_store.rows[0].colour == "YELLOW"


def test_the_handover_renders_after_a_named_approval(tmp_path: Path, injected_store: Any) -> None:
    """The approved handover shows the committed facts and the MCP station note."""
    with _running_server(tmp_path / "handover.db", injected_store) as server:
        base = _base(server)
        body = _post(base + "/case", _form_from_case(COMPLETE_CASE))
        thread_id = _thread_id(body)
        decided = _post(
            base + "/decision",
            {
                "thread_id": thread_id,
                "decision": "approve",
                "name": "Nurse Demo",
                "role": "triage nurse",
            },
        )

    assert 'class="handover-card"' in decided
    assert "Approved by" in decided
    assert "Queue position" in decided
    assert "Read-only projection" in decided
    assert "the same sourced facts the MCP server returns" in decided
    assert len(injected_store.rows) == 1


def test_chat_module_is_presentation_only() -> None:
    """The chat module imports no queue writer, commit tool, or durable resume seam."""
    path = Path(__file__).resolve().parents[1] / "src" / "triagedesk" / "desk" / "chat.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    assert "triagedesk.store" not in modules
    assert "triagedesk.store.queue" not in modules
    assert "triagedesk.mcp.server" not in modules
    assert "triagedesk.durable" not in modules
    source = path.read_text(encoding="utf-8")
    assert "commit_priority" not in source
    assert "commit_to_queue" not in source
