# MCP — install & use

> **Every step below is runnable.** The owned server is one stdio process; this runbook is how to
> start it, how to install it into a harness, and how to call each tool. The commands and blocks are
> checked by [`tests/test_mcp_runbook.py`](../tests/test_mcp_runbook.py), and each harness block
> follows the shape [`scripts/install_mcp.py`](../scripts/install_mcp.py) writes — the doc links to
> the generator instead of restating nine near-identical configs (DRY).

## 1. What gets installed

TriageDesk runs **two** MCP servers, and only one of them is installed into a harness:

| Component | Role | How it is installed |
| --- | --- | --- |
| `triagedesk-triage` (**owned server**, SDK v2; nine tools) | scoring, matching, retrieval, recheck, gated commit | you install it — this page |
| `mcp-sqlite@1.0.9` (**borrowed server**) | storage: queue rows + the hash-chained audit | launched by the owned server's audit path, on demand |
| `triagedesk-triage` (**usage skill**) | the agent-facing safe sequence and fail-closed stop rules | copied by the same installer into the harness's skills directory |

The skill is what teaches the calling agent the safe sequence and the fail-closed rules; without it a
harness can call `score_priority` directly and present a colour for a case with no age. It ships inside
the Python package (`src/triagedesk/skills/triagedesk-triage/`) and is copied by the same installer,
so it travels with the MCP.

Tool contracts and the tool table live in [`ARCHITECTURE.md`](../ARCHITECTURE.md) §4; the skill's
own self-contained contracts are in
[`src/triagedesk/skills/triagedesk-triage/references/tool-contracts.md`](../src/triagedesk/skills/triagedesk-triage/references/tool-contracts.md).
This page does not restate them. **Prerequisites:**

```bash
uv --version          # the lock is synced by `uv run`; no separate install step
npx --version         # the borrowed server, fetched once on the first tool call
ollama pull qwen2.5:1.5b   # ONLY needed for normalize_case
```

No model is needed for the other six tools; the first call may fetch the pinned
`mcp-sqlite@1.0.9` for the audit path (see §4).

## 2. Start it without a harness

```bash
# Speak stdio directly (Ctrl-C / EOF to stop). This is the process a harness launches.
uv run python -m triagedesk.mcp.server

# Same server through the SDK's runner, and the Inspector for interactive debugging.
uv run mcp run src/triagedesk/mcp/server.py
uv run mcp dev -e . src/triagedesk/mcp/server.py
```

`-e .` is required for the Inspector: it builds an isolated environment, and the server resolves
`data/*.yaml` from its own source location (`core/rules.py` → `parents[3]`), so a non-editable
install loses the SATS substrate.

## 3. Install into a harness

One command installs, or prints, the config your harness expects:

```bash
uv run python scripts/install_mcp.py --list                     # harness, config path, skill target
uv run python scripts/install_mcp.py --harness opencode         # print the block (default)
uv run python scripts/install_mcp.py --harness cursor --write    # config + skill
uv run python scripts/install_mcp.py --harness opencode --write --no-skill   # config only
```

`--write` merges a JSON config without touching any other key, and is idempotent. A differing
existing `triagedesk` entry is never replaced silently (`--force` does that). The Codex `config.toml`
is only ever **appended** when its table is absent. Without `--write`, every harness is print-only.

`--write` also copies the whole `triagedesk-triage` skill directory (including `references/`) into the
harness's skills directory. A locally edited skill is never overwritten without `--force`. `--no-skill`
skips the copy; `--skill-path DIR` overrides the destination (the installer creates
`DIR/triagedesk-triage/`).

The skill is package data, so an installed package can install it without the checkout:

```bash
uv run triagedesk skill path                       # from the checkout: print the skill directory
triagedesk skill install --path .opencode/skills   # from an installed package: copy it anywhere
```

| Harness | `--harness` | Config file | Scope |
| --- | --- | --- | --- |
| OpenCode | `--harness opencode` | `opencode.json` / `~/.config/opencode/opencode.json` | project, user |
| Claude Desktop | `--harness claude-desktop` | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS), `~/.config/Claude/…` (Linux), `%APPDATA%\Claude\…` (Windows) | user |
| Claude Code | `--harness claude-code` | `.mcp.json` / `~/.claude.json` | project, user |
| Cursor | `--harness cursor` | `.cursor/mcp.json` / `~/.cursor/mcp.json` | project, user |
| VS Code (Copilot) | `--harness vscode` | `.vscode/mcp.json` (portable `.mcp.json` also works) | project |
| Codex CLI / ChatGPT desktop | `--harness codex` | `.codex/config.toml` / `~/.codex/config.toml` | project, user |
| Gemini CLI | `--harness gemini` | `.gemini/settings.json` / `~/.gemini/settings.json` | project, user |
| Zed | `--harness zed` | `~/.config/zed/settings.json` | user |
| Windsurf / Devin Desktop | `--harness windsurf` | `.devin/mcp_config.json` / `~/.config/devin/mcp_config.json` | project, user |

The skill goes to the harness's native skills directory where it has one, and to the portable
`.agents/skills` convention otherwise:

| Harness | Project skill directory | User skill directory |
| --- | --- | --- |
| OpenCode | `.opencode/skills` | `~/.config/opencode/skills` |
| Claude Code | `.claude/skills` | `~/.claude/skills` |
| Cursor | `.cursor/skills` | `~/.cursor/skills` |
| VS Code (Copilot) | `.github/skills` | — |
| Codex CLI / ChatGPT desktop | `.codex/skills` | `~/.codex/skills` |
| Claude Desktop, Gemini CLI, Zed, Windsurf/Devin | `.agents/skills` (portable) | `~/.agents/skills` (portable) |

Where `REPO` below is **the absolute path to this checkout** (the default print mode fills it in for
you). Replace it with a harness variable — `${workspaceFolder}` (Cursor), `${CLAUDE_PROJECT_DIR}`
(Claude Code) — if you commit the file. OpenCode needs none of that: `"cwd": "."` resolves from the
workspace root, which is the form this repository ships in `opencode.json`.

**OpenCode** — local servers take one argv array, a `cwd`, and a timeout:

```json
{
  "mcp": {
    "triagedesk": {
      "type": "local",
      "command": ["uv", "run", "--frozen", "python", "-m", "triagedesk.mcp.server"],
      "cwd": ".",
      "enabled": true,
      "timeout": 120000
    }
  }
}
```

**Claude Code** — also installable with the CLI:
`claude mcp add --transport stdio triagedesk -- uv run --frozen --project REPO python -m triagedesk.mcp.server`
(the script prints this exact line):

```json
{
  "mcpServers": {
    "triagedesk": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--frozen", "--project", "REPO", "python", "-m", "triagedesk.mcp.server"],
      "timeout": 120000
    }
  }
}
```

**Claude Desktop, Cursor, Windsurf/Devin and Gemini CLI** all use this `mcpServers` shape: Cursor
requires `"type": "stdio"`, Gemini CLI adds `"cwd"` and `"timeout"`, Claude Desktop takes neither.
**VS Code** uses `servers` instead of `mcpServers`; **Zed** uses `context_servers` with a flat
`command`/`args`/`env`. **Codex** is TOML:

```toml
[mcp_servers.triagedesk]
command = "uv"
args = ["run", "--frozen", "--project", "REPO", "python", "-m", "triagedesk.mcp.server"]
cwd = "REPO"
tool_timeout_sec = 120
startup_timeout_sec = 30
```

The timeout matters: a harness's default is often 30 s, and `normalize_case` drives the local model
on CPU.

## 4. Verify the connection

Restart the harness, then check that the tools are listed (`/mcp` in most CLIs) — all nine:
the seven kernel tools plus `plan_next_step` and `request_clarification`, which the graph's `plan`
and `ask_question` nodes call — and call one low-risk tool by name:

```bash
# from a shell, before blaming the harness
uv run python -m triagedesk.mcp.server </dev/null && echo "server starts and exits cleanly"
```

> "Use the triagedesk MCP server's `match_discriminators` on 'chest pain and shortness of breath'."

A working install returns `acute_shortness_of_breath` and `chest_pain`. The first call also fetches
`mcp-sqlite@1.0.9` and creates `triage.db` — that is the audit path, not an error.

### The installed skill

`--write` leaves the skill at `<skills dir>/triagedesk-triage/SKILL.md` (and `references/` beside it).
The harness discovers it by its `description`; ask a triage question and the skill should load before
the first tool call. It is the agent-facing contract:

- the safe sequence: normalize → match → score → evidence → confidence → clinician approval → commit;
- the stop rules: `out_of_scope`, `abstained`, `missing_vitals`, `no_match`, `deferral`, `refused`;
- the exact `ApprovalToken` shape and the rule that only a named clinician supplies it;
- a self-contained tool reference, so it still works when the checkout is not on the harness's path.

If the harness does not list the skill, confirm the file exists at the target printed by `--list` and
that the harness's skill discovery is enabled. The MCP server works without the skill, but the agent
then has to be told the safe sequence explicitly — install the skill for any real triage use.

## 5. Use: the nine shipped tools

### `normalize_case`

A note → the typed case schema (needs Ollama). Unknown discriminator ids are dropped, never guessed:

```json
{"raw_note": "RR 24, HR 118, BP 108/70, temp 38.9, alert, coughing and fast breathing"}
```

Returns `{"case": {…}, "matched_discriminator_ids": [], "no_discriminator_matched": true}`; a recorded
real response is in [`evidence/mcp-spike.json`](../evidence/mcp-spike.json).

### `score_priority`

The deterministic path — no model. Missing age makes it fail closed:

```json
{"case": {"age_years": 34, "respiratory_rate": 24, "heart_rate": 118,
          "systolic_bp": 108, "temperature_c": 38.9, "avpu": "alert",
          "mobility": "walking", "trauma": false},
 "matched_discriminator_ids": ["acute_shortness_of_breath"]}
```

```json
{"colour": "ORANGE", "tews": 6, "target": "< 10 min", "destination": "Majors",
 "triggered_rules": [{"rule_id": "respiratory_rate", "detail": "respiratory_rate=24 -> 2 points",
                      "points": 2, "citation": "SATS Training Manual 2012 (EMSSA), adult TEWS — respiratory_rate band"}, "…"],
 "citations": ["…one per triggered rule…"], "missing_vitals": [],
 "out_of_scope": false, "abstained": false, "reason": null}
```

Omit `age_years` and it returns `{"colour": null, "abstained": true, "reason": "age is missing; …"}` —
a refusal, not a guess.

### `assess_confidence`

```json
{"matched_ids": ["acute_shortness_of_breath"], "no_match": false, "priority": <PriorityResult>,
 "retrieval_status": "matched", "candidates": [], "questions": [], "clarification_round": 0}
```

Returns `action` (`deliver` / `clarify` / `defer`), `deferral`, a closed-set `level`, and per-component
evidence. A `clarify` action carries at most three targeted `questions`; it never carries a colour.
There is no percentage and no score field, by design.

### `match_discriminators`

```json
{"complaint": "chest pain and shortness of breath", "note": "<optional full note>"}
```

```json
{"matched_ids": ["acute_shortness_of_breath", "chest_pain"], "no_match": false, "warning": null,
 "retrieval_status": "matched", "candidates": ["acute_shortness_of_breath", "chest_pain"], "questions": []}
```

`retrieval_status` classifies coverage — `matched`, `ambiguous`, or `no_candidate` — and never adds an
id to `matched_ids`.

### `retrieve_evidence`

```json
{"complaint": "chest pain"}
```

Returns ranked, attributed `passages` (`discriminator_id`, `label`, `citation`, `score`, `rank`) or
`no_match`. It carries no colour field, so it can show grounding but never set a priority.

### `raise_recheck_flag`

Serial vitals, never a re-classification:

```json
{"previous": {"respiratory_rate": 18, "heart_rate": 92, "temperature_c": 38.9, "avpu": "alert"},
 "current":  {"respiratory_rate": 24, "heart_rate": 118, "temperature_c": 38.9, "avpu": "alert"}}
```

Returns `{"flag": true, "deteriorations": ["respiratory_rate", "heart_rate"], "changes": […],
"reason": "serial vitals show deterioration; a second look is required"}`.

### `plan_next_step`

The planner tool the graph's `plan` node calls: the local model **proposes** the next
investigation action and a
deterministic guard decides. Read-only — no queue row, no colour, no approval token — and **not yet
wired into the shipped graph**, so the shipped run never calls it.

```json
{"investigation": {"complaint": "chest pain", "retrieval_status": "matched",
                   "has_evidence": false, "step": 0, "budget_left": 3}}
```

```json
{"action": "gather_evidence", "rationale": "no excerpt is in hand yet", "signals": [],
 "step": 1, "budget_left": 2, "proposed_action": "gather_evidence",
 "overridden": false, "override_reason": null}
```

The closed action set is `gather_evidence`, `ask_question`, `re_extract` and
`finish_investigation` — the last is the only exit to the deterministic kernel and the default. When
the proposal is inadmissible, missing, malformed or the budget is spent, the guard returns
`finish_investigation` with `overridden: true` and a reason. When the only admissible action is
`finish_investigation`, the model is not called at all.

### `request_clarification`

The clarification tool the graph's `ask_question` node calls: it asks the nurse at most **three**
questions **inside** the tool call, and returns a typed answer. Read-only — no store, no queue row,
no approval token, no colour — and **not yet wired into the shipped graph**, so the shipped run
never calls it.

```json
{"candidates": ["chest_pain", "acute_shortness_of_breath"]}
```

```json
{"outcome": "accepted", "answers": ["crushing central pain, worse on exertion"], "reason": null}
```

- The caller supplies **closed-set discriminator ids only**. Each question is derived from the loaded
  discriminator definitions through the one helper the coverage classifier uses, so a caller cannot
  author question text and a question that does not trace to a definition is not asked.
- At most three are asked; an id outside the closed set is skipped.
- Four outcomes are distinguished — and only `accepted` carries an answer:

| `outcome` | Meaning | Carries an answer? |
| --- | --- | --- |
| `accepted` | the nurse answered | yes |
| `declined` | the nurse declined the question | no |
| `cancelled` | the client abandoned the call | no |
| `unavailable` | the client cannot elicit at all | no |

```json
{"outcome": "declined", "answers": [], "reason": null}
```

A `declined`, `cancelled` or `unavailable` result is **not** a negative clinical finding and is never
converted into a value. An answer is an **observation**, not an approval: it can be appended to the
case facts and it never advances a case past the clinician's gate, never becomes a colour, and never
writes a queue row.

#### How the round-trip works

The shipped adapter (`langchain.mcp.MCPAdapter`) turns the server's mid-call question into a LangGraph
`interrupt()`:

1. the tool call reaches `request_clarification` and the server returns an `input_required` result
   carrying one form request (the 2026-07-28 revision forbids a server-initiated request);
2. the adapter raises `interrupt({"type": "mcp_elicitation", "tool_name": …, "requests": […]})`;
3. the caller resumes the graph with `{"responses": {"clarification": {"action": "accept",
   "content": {"q1": "…"}}}}` — or `{"action": "decline"}`;
4. the call completes and the tool returns the `ClarificationAnswer`.

The approval gate's payload carries `"type": "approval"`, so the two interrupts are never confused: a
question is not a decision. Both surfaces present them differently — `triagedesk resume` takes
repeatable `--answer` (and declines by default when none is given), and the desk renders a question
panel instead of the approval gate.

#### Answering from the CLI

```bash
# Answer the question, in the order it was asked (repeat the flag per question).
uv run triagedesk resume --thread-id <id> --answer "crushing central pain" --answer "worse on exertion"

# No --answer: the question is declined. Nothing is recorded as a finding.
uv run triagedesk resume --thread-id <id>
```

`--decision` is only needed when an **approval** is pending; without it the CLI says so and names the
flag rather than inventing a decision. If answering the question reveals the approval gate, the CLI
prints that it paused again at the gate and exits 0 — **nothing was committed**, and a second
`resume --decision …` finishes the case.

#### Answering from the desk

The desk renders a **question panel** — the derived questions, one free-text field each, and a
"Decline to answer" control — instead of the approval gate. The panel has no approve, edit or dismiss
control, no colour control and no commit path: `POST /clarify` resumes with the answers through the
same gated plumbing and then shows whatever comes next (usually the gate) as itself.

The fail-closed rules both surfaces obey:

- a **decline** (or a cancel, or a client that cannot elicit) is **not** a negative clinical finding
  and is never converted into a value;
- **answering is not approval**: an answer is an observation appended to the case facts, and it never
  advances a case past the clinician's gate, never becomes a colour and never writes a queue row;
- an answered question is **not asked twice**, and a resume cannot duplicate a queue commit (the
  write is idempotent on the case's content hash).

> **Honest scope:** no shipped graph node calls `request_clarification` yet — the `plan` node that
> will call it is Phase 23. Everything above is the shipped surface contract, proved by tests
> (`tests/test_elicitation_tool.py`, `tests/test_elicitation_roundtrip.py`, `tests/test_durable_cli.py`,
> `tests/test_desk.py`), not a storyboard step.

### `commit_priority`

The only queue-affecting tool. Refuses without a valid token, and the refusal touches no store:

```json
{"case_id": "0417", "colour": "ORANGE", "case": <CaseInput>, "approval_token": <ApprovalToken>}
```

```json
{"committed": false, "refused": true, "reason": "no approval token supplied; refusing to commit", "position": null}
```

## 6. The approval token

`commit_priority` validates this exact shape (see `core/schema.py` → `ApprovalToken`):

```json
{"decision": "approve", "approved_at": "2026-11-03T10:00:00Z",
 "approved_by": "Nurse Demo", "role": "triage nurse", "final_colour": "ORANGE"}
```

- `approve` / `edit` require a non-blank `approved_by` **and** `role`, and a `final_colour` drawn
  from the colours the loaded substrate declares (it is required for `approve` too).
- `dismiss` carries no identity and no colour — only `decision` and `approved_at` — and commits
  nothing:

```json
{"decision": "dismiss", "approved_at": "2026-11-03T10:00:00Z"}
```

The write is idempotent on (`case_id`, immutable case-content hash): a repeat approve, or an edit of
the same case, re-derives the same key and supersedes one queue row instead of adding a second.

## 7. What each call writes

Every tool call — including read-only ones — appends **one** hash-chained audit record through the
borrowed store, and emits **one** `tool` span to `spans.jsonl`:

```json
{"seq": 7, "ts": "2026-11-03T10:00:00Z", "case_id": "0417", "tool": "score_priority",
 "actor": "agent", "inputs": {"case_id": "0417"}, "outputs": {"colour": "ORANGE"},
 "approved_by": null, "role": null, "trace_id": "…", "prev_hash": "…", "hash": "…"}
```

Both artefacts land in the **harness's working directory**: `triage.db` (queue + audit) and
`spans.jsonl` (local trace stream). Both are covered by `.gitignore`. Point the harness's `cwd` at
this checkout if you want them here — but note that `tests/test_observability.py` asserts
`spans.jsonl` is **absent from the repository root**, so delete it before running the suite if you
have been calling these tools from the checkout.

> Nothing a harness does can reach a patient: the only queue-affecting tool is `commit_priority`, and
> it refuses without the named token in §6.

## 8. How it is wired at runtime

The shipped demo, harness and desk call the same tool **implementations** in-process, so the recording
shows real tool calls without a subprocess. The stdio transport is exercised by
`graph.build.load_graph_tools` / `run_case` and by `scripts/spike_mcp.py`; the adapter decision and
the both-servers handshake are recorded in [`evidence/mcp-spike.json`](../evidence/mcp-spike.json).

## 9. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Every call fails, including read-only ones | the audit path needs the borrowed store | install Node, check `npx --version`, allow the first fetch of `mcp-sqlite@1.0.9` |
| Server starts, harness shows zero tools | wrong `command`/`args`, or a copied block still says `REPO` | re-run `--harness <key>` and paste the resolved block |
| `ModuleNotFoundError: triagedesk` | installed non-editable, or launched outside the checkout | keep `--project REPO`; for the Inspector use `mcp dev -e .` |
| Tools error with a `data/*.yaml` path | the server was installed as a wheel | install editable (`uv pip install -e .`) |
| `normalize_case` fails, others work | Ollama not running, or model not pulled | `ollama serve`, `ollama pull qwen2.5:1.5b` |
| `commit_priority` returns `refused: true` | missing, malformed, or `dismiss` token | send the five-field token; a dismissal is meant to refuse |
| A tool times out in the harness | harness default (often 30 s) vs CPU inference | raise the harness timeout — 120 000 ms is written for you |
| The `triagedesk-triage` skill is not listed | the skill was skipped, or the harness does not read that directory | re-run `--harness <key> --write` (not `--no-skill`); check the target printed by `--list`; use `--skill-path DIR` for a harness with no native skill dir |
