"""The MCP-runbook-vs-shipped-server grounding proof (DOCS-05, D-04).

Keeps ``docs/MCP.md`` honest against the server and the installer it documents, so
the install-and-use page cannot drift into fiction:

* the tool sections the runbook walks through are **exactly** the tools the owned
  server registers — both directions, so adding a tool forces a doc update and a
  removed tool cannot linger;
* the installer the page points at exists, imports, and knows every harness the
  page lists (and the page lists every harness it knows);
* the OpenCode and ``mcpServers`` blocks parse as JSON, are local stdio entries,
  and launch the one module;
* the documented approval tokens pass ``ApprovalToken`` — the page's example is
  validated by the real validator, not by prose;
* the audit example names every ``AuditRecord`` field, driven from the model, so a
  new field fails the doc;
* the runtime artefacts the page promises are named and gitignored;
* the page does not resurrect the stale ``log/audit.jsonl`` claim.

Nothing here launches the borrowed SQLite subprocess or calls a tool over stdio:
the tool list is read through the SDK's in-memory client, as ``test_mcp_server.py``
does.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from mcp import Client

from triagedesk.core.schema import ApprovalToken
from triagedesk.mcp import server as server_module
from triagedesk.store.audit import AuditRecord

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = REPO_ROOT / "docs" / "MCP.md"
INSTALLER = REPO_ROOT / "scripts" / "install_mcp.py"
SERVER_FILE = REPO_ROOT / "src" / "triagedesk" / "mcp" / "server.py"
GITIGNORE = REPO_ROOT / ".gitignore"

# A tool section is the heading the runbook uses for each worked call.
_TOOL_SECTION_RE = re.compile(r"^### `([a-z_]+)`$", re.MULTILINE)
_JSON_FENCE_RE = re.compile(r"```json\n(.*?)```", re.DOTALL)


def _text() -> str:
    """Read the runbook as text."""
    return RUNBOOK.read_text(encoding="utf-8")


def _installer() -> ModuleType:
    """Load the shipped installer by path (``scripts/`` is not a package)."""
    spec = importlib.util.spec_from_file_location("_install_mcp_runbook", INSTALLER)
    assert spec is not None and spec.loader is not None, f"could not load {INSTALLER}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _json_documents() -> list[Any]:
    """Every JSON fence that parses (abridged ``{…}`` examples are skipped)."""
    documents: list[Any] = []
    for block in _JSON_FENCE_RE.findall(_text()):
        try:
            documents.append(json.loads(block))
        except json.JSONDecodeError:
            continue
    return documents


def _documented_tools() -> set[str]:
    """The tool names the runbook has a worked section for."""
    return set(_TOOL_SECTION_RE.findall(_text()))


async def test_runbook_documents_exactly_the_registered_tools() -> None:
    """The worked sections are the server's tool set — no gap, no ghost tool."""
    async with Client(server_module.server) as client:
        listed = await client.list_tools()
    registered = {tool.name for tool in listed.tools}
    documented = _documented_tools()
    assert registered, "the owned server exposed no tools"
    assert documented == registered, (
        f"docs/MCP.md documents {sorted(documented)} but the server registers {sorted(registered)}"
    )


def test_runbook_points_at_the_shipped_launch_paths() -> None:
    """The documented ways to start the server exist in the shipped tree."""
    text = _text()
    assert "uv run python -m triagedesk.mcp.server" in text
    assert "uv run mcp run src/triagedesk/mcp/server.py" in text
    assert "uv run mcp dev -e . src/triagedesk/mcp/server.py" in text
    assert SERVER_FILE.is_file(), f"{SERVER_FILE} does not exist"
    assert importlib.util.find_spec("triagedesk.mcp.server") is not None


def test_runbook_lists_every_installer_harness() -> None:
    """Every harness the installer knows is documented, and vice versa."""
    install_mcp = _installer()
    text = _text()
    documented = set(re.findall(r"`--harness ([a-z-]+)`", text))
    assert documented, "docs/MCP.md documents no --harness invocation"
    assert documented <= set(install_mcp.HARNESSES), (
        f"docs/MCP.md names harnesses the installer does not know: "
        f"{sorted(documented - set(install_mcp.HARNESSES))}"
    )
    for key in install_mcp.HARNESSES:
        assert f"| `--harness {key}` |" in text, f"docs/MCP.md does not list the {key} harness"


def test_opencode_block_is_a_local_server_that_launches_the_module() -> None:
    """The OpenCode block is the shape OpenCode requires (type/cwd/timeout)."""
    blocks = [doc for doc in _json_documents() if isinstance(doc, dict) and "mcp" in doc]
    assert blocks, "docs/MCP.md has no parsable OpenCode 'mcp' block"
    entry = blocks[0]["mcp"]["triagedesk"]
    assert entry["type"] == "local"
    assert isinstance(entry["command"], list)
    assert "triagedesk.mcp.server" in entry["command"]
    assert "cwd" in entry
    assert entry["timeout"] >= 60_000


def test_portable_mcpservers_block_is_stdio_and_complete() -> None:
    """The Claude-style block is a stdio entry with a timeout for CPU inference."""
    blocks = [doc for doc in _json_documents() if isinstance(doc, dict) and "mcpServers" in doc]
    assert blocks, "docs/MCP.md has no parsable 'mcpServers' block"
    entry = blocks[0]["mcpServers"]["triagedesk"]
    assert entry["type"] == "stdio"
    assert entry["command"] == "uv"
    assert entry["args"][-2:] == ["-m", "triagedesk.mcp.server"]
    assert entry["timeout"] >= 60_000


def test_documented_approval_tokens_pass_the_real_validator() -> None:
    """Every documented token is a token the gate would accept (or is a dismissal)."""
    tokens = [doc for doc in _json_documents() if isinstance(doc, dict) and "decision" in doc]
    assert tokens, "docs/MCP.md has no parsable approval token"
    decisions = set()
    for raw in tokens:
        token = ApprovalToken.model_validate(raw)
        decisions.add(token.decision)
        if token.decision != "dismiss":
            assert token.approved_by.strip() and token.role.strip()
            assert token.final_colour.strip()
    assert {"approve", "dismiss"} <= decisions, (
        f"docs/MCP.md documents decisions {sorted(decisions)}; both an approve and a "
        "dismiss must be shown"
    )


def test_audit_example_names_every_record_field() -> None:
    """The audit example carries every field ``AuditRecord`` seals (model-driven)."""
    blocks = [doc for doc in _json_documents() if isinstance(doc, dict) and "prev_hash" in doc]
    assert blocks, "docs/MCP.md has no parsable audit record"
    example = blocks[0]
    missing = set(AuditRecord.model_fields) - set(example)
    assert not missing, f"the audit example omits the record fields {sorted(missing)}"


def test_runbook_names_the_runtime_artefacts_and_they_are_gitignored() -> None:
    """``triage.db`` and ``spans.jsonl`` are documented AND already ignored."""
    text = _text()
    ignored = GITIGNORE.read_text(encoding="utf-8")
    for artefact in ("triage.db", "spans.jsonl"):
        assert artefact in text, f"docs/MCP.md does not name {artefact}"
    assert "*.db" in ignored, "triage.db is no longer covered by .gitignore"
    assert "spans.jsonl" in ignored, "spans.jsonl is no longer covered by .gitignore"


def test_runbook_does_not_claim_a_log_directory() -> None:
    """The stale ``log/audit.jsonl`` claim must not reappear (audit is the SQLite table)."""
    assert "log/audit.jsonl" not in _text()
    assert "SQLite audit table" in _text() or "audit record" in _text()
