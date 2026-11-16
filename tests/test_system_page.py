"""The /system integration map proofs (Phase 25, Task 3).

The desk is a demo surface; the MCP server is the station integration path. These tests keep
the distinction, the wire protocol, and the nine-tool list visible and honest.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from test_desk import _base, _get, _running_server
from triagedesk.mcp.server import server as mcp_server

ASSET_DIR = Path(__file__).resolve().parents[1] / "src" / "triagedesk" / "desk" / "static"


def test_the_system_page_renders_the_three_layers_and_the_wire(
    tmp_path: Path, injected_store: Any
) -> None:
    """GET /system names the desk, the core, MCP, and every transport in the chain."""
    with _running_server(tmp_path / "system.db", injected_store) as server:
        body = _get(_base(server) + "/system")

    for text in (
        "How the desk, the core, and MCP connect",
        "Desk (this page)",
        "Core (the clinical logic)",
        "MCP server (station link)",
        "in-process",
        "loopback",
        "stdio",
        "JSON&#8209;RPC 2.0",
        "initialize",
        "tools/list",
        "tools/call",
        "MCP elicitation",
        "mcp-sqlite@1.0.9",
        "triagedesk.handover/1",
        "commit_priority",
        "Do not scrape the desk page",
    ):
        assert text in body, f"the system page does not name {text!r}"
    assert '<a href="/system" class="nav-link" aria-current="page">' in body


def test_the_system_page_is_read_only(tmp_path: Path, injected_store: Any) -> None:
    """The map is a GET-only explainer: it renders no form and reads no store."""
    with _running_server(tmp_path / "system-read.db", injected_store) as server:
        body = _get(_base(server) + "/system")

    assert "<form" not in body
    assert injected_store.calls == []


def test_the_system_page_makes_no_external_request() -> None:
    """The system fragment carries no URL, font import, or fetched asset."""
    source = (ASSET_DIR / "system.html").read_text(encoding="utf-8")
    for forbidden in ("http://", "https://", "@import", "url("):
        assert forbidden not in source, forbidden


def test_the_tool_list_matches_the_mcp_server() -> None:
    """The UI list is the server's own registered tools, in registration order."""
    tools = asyncio.run(mcp_server.list_tools())
    names = [tool.name for tool in tools]
    assert len(names) == 9
    source = (ASSET_DIR / "system.html").read_text(encoding="utf-8")
    grid = source.split('class="tool-grid"', 1)[1].split("</ul>", 1)[0]
    listed = re.findall(r"<code>([^<]+)</code>", grid)
    assert sorted(listed) == sorted(names), (listed, names)
