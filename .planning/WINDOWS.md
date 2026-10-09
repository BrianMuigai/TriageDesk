---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-10-09T15:12:43.518Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 02 | stub | src/triagedesk/mcp/server.py | 96 | commit_priority is a Phase-2 gated stub: it refuses without a valid approval token and performs no queue/store write; the real LangGraph gate + idempotent commit is Phase 3 (GATE-01..04, TOOL-05) | open |  | 2026-10-09T15:12:43.518Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "02",
    "file": "src/triagedesk/mcp/server.py",
    "line": 96,
    "description": "commit_priority is a Phase-2 gated stub: it refuses without a valid approval token and performs no queue/store write; the real LangGraph gate + idempotent commit is Phase 3 (GATE-01..04, TOOL-05)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-09T15:12:43.518Z",
    "resolved_at": null
  }
]
````
