"""D-07 MCP retirement evidence: list + call one tool on BOTH servers.

Retires Day-1 unknown (b) (Roadmap SC4): proves the beta adapter
(``langchain.mcp.MCPAdapter``) can list tools and invoke one tool on BOTH the
owned SDK-v2 server and the borrowed legacy SQLite server — each through its OWN
adapter context (never one merged ``MCPConfig``; see 01-RESEARCH Pattern 3).

The borrowed server is storage only; the gate stays ours (D-06). This spike
proves the adapter can *reach* it, not that it may mutate queue state.

Writes ``evidence/mcp-spike.json`` and exits non-zero if either handshake fails.

Usage:
    uv run python scripts/spike_mcp.py --report evidence/mcp-spike.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from triagedesk.mcp.adapter import (
    BORROWED_SERVER_PACKAGE,
    load_borrowed_tools,
    load_tools,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = REPO_ROOT / "evidence" / "mcp-spike.json"
# The borrowed server is storage only; this DB exists solely to prove the
# handshake. It is a runtime artefact (*.db is gitignored), never committed.
DEFAULT_DB = REPO_ROOT / "triage.db"

OWNED_TOOL = "normalize_case"
BORROWED_TOOL = "db_info"
NOTE = "RR 24, HR 118, BP 108/70, temp 38.9, alert, coughing and fast breathing"


def _jsonable(value: Any) -> Any:
    """Best-effort JSON-serialisable view of an MCP / tool result."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


async def _probe_owned() -> dict:
    """List tools and call one tool on the owned server through the adapter."""
    tools = await load_tools()
    names = [t.name for t in tools]
    result: dict = {"tool_list": names}
    tool = next((t for t in tools if t.name == OWNED_TOOL), None)
    if tool is None:
        raise RuntimeError(f"owned server did not expose {OWNED_TOOL!r}: {names}")
    payload = await tool.ainvoke({"raw_note": NOTE})
    result["called"] = {
        "tool": OWNED_TOOL,
        "arguments": {"raw_note": NOTE},
        "result": _jsonable(payload),
    }
    return result


async def _probe_borrowed(db_path: Path) -> dict:
    """List tools and call one tool on the borrowed server (separate context)."""
    tools = await load_borrowed_tools(db_path)
    names = [t.name for t in tools]
    result: dict = {
        "tool_list": names,
        "launch": f"npx -y {BORROWED_SERVER_PACKAGE} {db_path}",
    }
    tool = next((t for t in tools if t.name == BORROWED_TOOL), None)
    if tool is None:
        raise RuntimeError(f"borrowed server did not expose {BORROWED_TOOL!r}: {names}")
    payload = await tool.ainvoke({})
    result["called"] = {
        "tool": BORROWED_TOOL,
        "arguments": {},
        "result": _jsonable(payload),
    }
    return result


async def main() -> int:
    parser = argparse.ArgumentParser(description="MCP handshake spike (D-07)")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    report: dict = {
        "world_decision": None,
        "owned_server": {},
        "borrowed_server": {},
        "errors": [],
    }
    ok = True
    try:
        report["owned_server"] = await _probe_owned()
    except Exception as exc:  # noqa: BLE001 — recorded as evidence, not raised
        report["errors"].append(f"owned handshake failed: {type(exc).__name__}: {exc}")
        ok = False
    try:
        report["borrowed_server"] = await _probe_borrowed(args.db)
    except Exception as exc:  # noqa: BLE001 — recorded as evidence, not raised
        report["errors"].append(f"borrowed handshake failed: {type(exc).__name__}: {exc}")
        ok = False

    # The World A/B decision (D-04). World A is adopted when BOTH handshakes
    # succeed on the modern adapter; otherwise the one-module World-B fallback
    # (langchain-mcp-adapters + mcp<2 + v1 FastMCP server) is the documented path.
    if ok:
        report["world_decision"] = {
            "world": "A",
            "adapter": "langchain.mcp.MCPAdapter",
            "reason": (
                "Both the owned SDK-v2 server and the borrowed legacy SQLite server "
                "listed tools and answered one call through separate MCPAdapter "
                "contexts (no era collapse). World A adopted (D-04)."
            ),
        }
    else:
        report["world_decision"] = {
            "world": "B (fallback required)",
            "adapter": "langchain-mcp-adapters.MultiServerMCPClient + mcp<2",
            "reason": (
                "At least one handshake failed on World A; the one-module World-B "
                "fallback is the documented path (D-04)."
            ),
        }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
