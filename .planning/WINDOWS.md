---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 1
total_count: 2
last_updated: 2026-10-09T16:26:50.495Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 02 | stub | src/triagedesk/mcp/server.py | 96 | commit_priority is a Phase-2 gated stub: it refuses without a valid approval token and performs no queue/store write; the real LangGraph gate + idempotent commit is Phase 3 (GATE-01..04, TOOL-05) | fixed |  | 2026-10-09T15:12:43.518Z | 2026-10-09T16:26:50.495Z |
| 2 | 3 | stub | src/triagedesk/graph/nodes.py | 232 | handover.second_look is None in the tracer: the serial-vitals recheck is wired in a later Phase-3 plan (D-07), so no recheck flag flows yet | open |  | 2026-10-09T16:08:12.701Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "02",
    "file": "src/triagedesk/mcp/server.py",
    "line": 96,
    "description": "commit_priority is a Phase-2 gated stub: it refuses without a valid approval token and performs no queue/store write; the real LangGraph gate + idempotent commit is Phase 3 (GATE-01..04, TOOL-05)",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-10-09T15:12:43.518Z",
    "resolved_at": "2026-10-09T16:26:50.495Z"
  },
  {
    "id": 2,
    "kind": "stub",
    "phase": "3",
    "file": "src/triagedesk/graph/nodes.py",
    "line": 232,
    "description": "handover.second_look is None in the tracer: the serial-vitals recheck is wired in a later Phase-3 plan (D-07), so no recheck flag flows yet",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-09T16:08:12.701Z",
    "resolved_at": null
  }
]
````
