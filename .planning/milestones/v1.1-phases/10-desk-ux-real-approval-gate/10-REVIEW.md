---
phase: 10-desk-ux-real-approval-gate
reviewed: 2026-10-12T23:33:09Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - docs/DECISIONS.md
  - docs/DESK.md
  - pyproject.toml
  - src/triagedesk/cli.py
  - src/triagedesk/desk/__init__.py
  - src/triagedesk/desk/server.py
  - src/triagedesk/desk/static/index.html
  - src/triagedesk/desk/static/styles.css
  - tests/test_desk.py
  - tests/test_desk_runbook.py
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: clean
---

# Phase 10: Code Review Report

**Reviewed:** 2026-10-12T23:33:09Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** clean

## Summary

This is the **final convergence review** after a targeted 3rd fix pass. The prior pass left exactly
two warnings (both in the iteration-2 CSRF hardening) plus two info items; all four were re-verified
against the **current** source and, where testable, against a **running server driven by raw sockets**
with exact header control (urllib cannot forge a `Host`, so the raw path is the only honest way to
probe the Host/Origin defences). **No critical or warning findings remain.**

`uv run pytest -q` → **421 passed**. `ruff check` and `mypy` (strict) are clean on the desk surface and
CLI. The phase diff (`e973635~1..HEAD`) touches exactly the ten reviewed files plus `tests/conftest.py`
— no `src/triagedesk/core/` file appears, so the frozen spine is intact.

### The four fix commits — verified against current source

- **`0f6b4be` — WR-01 (non-ASCII token).** `_csrf_ok` now compares UTF-8 **bytes**
  (`server.py:913-916`): `supplied.encode("utf-8")` is total for any attacker-controlled `str`
  (`parse_qs` percent-decodes UTF-8), and `secrets.compare_digest(bytes, bytes)` cannot raise
  `TypeError`. **Probed live:** `csrf_token=%C3%A9` → `HTTP/1.0 200 OK`, the documented failure panel
  (`The case could not be scored.`) rendered, **zero rows** written, connection never dropped. The
  handler-crash path is closed.
- **`b308be5` — WR-02 (DNS rebinding).** `_loopback_host` (`server.py:836-860`) is called first in
  both `do_GET` (`server.py:927`) and `do_POST` (`server.py:957`); a non-loopback `Host` is refused
  before anything else, so `_cross_origin` can no longer be satisfied with an attacker-set foreign
  `Host`. **Probed live:** foreign `Host` alone, foreign `Host` + matching `Origin`, `user@host`
  smuggling, foreign bracketed IPv6, a token replayed from a second server, and a POST with **no**
  `Host` header — every one refused with the failure panel and **zero rows**. A genuine same-origin
  approve still commits exactly one row; `Host: [::1]:<port>` is correctly accepted as loopback.
- **`fc1a92a` — IN-01 (duplicate-key trauma).** `test_checked_trauma_duplicate_key_reaches_the_card_and_gate`
  posts the browser's real checked-box serialisation (`trauma=true` **then** `trauma=false`, hand-built
  because a dict cannot express the duplicate key), asserts the card + gate render, and pins the
  committed row's idempotency hash to the `trauma=True` case (and asserts it differs from `trauma=False`).
  **Confirmed passing** — the exact browser path the phase cares about is now covered by a request, not
  only by a DOM-order assertion.
- **`73d1d69` — IN-02 (relative dynamic import).** `_literal_dynamic_imports` + `_resolve_relative`
  (`tests/conftest.py:115-161`) now resolve `importlib.import_module("..store.queue", "triagedesk.desk")`
  to `triagedesk.store.queue` via importlib's own algorithm (`level-1` components stripped from the
  anchor). **Confirmed:** the guard's negative-control test asserts the relative form is caught, so the
  no-self-commit claim is no longer evadable by a relative literal dynamic import.

### Final adversarial sweep of the CSRF + Host defences

| Attack (raw socket) | Result | Rows written | Panel |
|---|---|---|---|
| non-ASCII `csrf_token` (`%C3%A9`) | refused | 0 | yes |
| foreign `Host` alone | refused | 0 | yes |
| foreign `Host` + matching `Origin` | refused | 0 | yes |
| `Host: 127.0.0.1@evil.example` (userinfo smuggling) | refused | 0 | yes |
| `Host: evil@127.0.0.1` | refused | 0 | yes |
| `Host: [2001:db8::1]` (foreign IPv6) | refused | 0 | yes |
| `Host: [::1]:<port>` (loopback IPv6) | **accepted** (card rendered) | 0 | n/a |
| token replayed from a second server | refused | 0 | yes |
| POST with **no** `Host` header | refused | 0 | yes |
| `/decision` valid-token + foreign `Host` (commit path) | refused | 0 | yes |
| legit same-origin approve | committed | **1** | n/a |

Every refusal writes **zero** rows and renders the documented failure panel; the one legitimate
same-origin approve commits exactly one row. `ipaddress` was also checked directly: no non-loopback
string (`2130706433`, `0x7f000001`, `0177.0.0.1`, `127.1`, `127.0.0.1.`, `evil.example`) is accepted
as loopback, so no attacker-controlled hostname can satisfy `_loopback_host`.

### No regression elsewhere

The banner/gate split (D10-17 — the banner fires only from `banner_trigger`, and a `no_match` forces
`deferral=True` so a gate case never carries the trigger), the gate-derived edit set (D10-18 —
`editable_colours()` equals `{band.colour for band in get_tews().tews_to_colour}` and equals the
rendered radio set and the CSS swatches), the trauma committable path, escaping of every rendered value
(complaint, colour-class attribute, panel copy, state panels), the fixed two-name asset allowlist
(no path built from `self.path`), no egress (`index.html`/`styles.css` carry no URL, `@import`, `url(`,
or off-host script), `harden_offline()` before the lazy handler import, hermeticity (injected store +
`tmp_path` checkpoints + redirected span sink), the frozen spine, no SATS colour literal in Python (the
names live only in `styles.css`), and the no-diagnostic / no-percentage copy — all confirmed by the
passing suite and direct inspection. `_cross_origin` remains meaningful because it now runs only after
`_host_ok()` has pinned `Host` to loopback.

## Narrative Findings (AI reviewer)

No critical or warning findings. Three sub-threshold advisories are recorded for completeness; none is
exploitable against a browser and none affects a commit path.

### IN-01: `_loopback_host` accepts a bracket-suffixed `Host` (strictness nit, not exploitable)

**File:** `src/triagedesk/desk/server.py:848-852`

**Issue:** the bracketed branch takes `host[1:host.find("]")]` without requiring the `]` to terminate
the header, so a raw client could send `Host: [::1]evil` or `[::1]:8765]` and still be treated as
loopback. This is **not** a security gap: a browser derives `Host` from the URL and cannot be made to
send such a value, and a raw client can already send `Host: 127.0.0.1` directly — the check exists to
defeat DNS rebinding (browser-set `Host`), which it does.

**Fix (optional, for exactness):** require the closing bracket to end the host portion, e.g. reject when
`host[end+1:]` is non-empty and not `":<digits>"`.

### IN-02: `_loopback_host` over-refuses valid loopback shorthands (usability nit)

**File:** `src/triagedesk/desk/server.py:857-860`

**Issue:** `ipaddress.ip_address` rejects `127.1` (a valid inet-atom shorthand for `127.0.0.1`) and
`localhost.` (a trailing-dot FQDN), so a user who opens `http://localhost.:8765` would get a 403 rather
than the page. Conservative over-refusal — a usability edge, never a safety gap (refusing a real
loopback name cannot let an attack through).

**Fix (optional):** strip a single trailing dot from `hostname` before the `_LOOPBACK_HOSTNAMES`/`ipaddress`
checks; leave `127.1` refused (its acceptance is not worth the parser complexity).

### IN-03: no per-connection read timeout on a declared `Content-Length` (robustness, loopback-only)

**File:** `src/triagedesk/desk/server.py:963-970`

**Issue:** the 64 KiB body cap bounds the *read size* but not the *read duration*: `rfile.read(length)`
blocks until `length` bytes arrive, and `BaseHTTPRequestHandler` sets no socket timeout, so a local
client that sends `Content-Length: 65536` and then stalls pins one request thread. `ThreadingHTTPServer`
keeps serving other connections, and the surface is loopback-only and unauthenticated by design, so this
is a local resource nit rather than a defect; it is noted because it is adjacent to the IN-01 cap that
was added.

**Fix (optional):** set a small `timeout` on the handler (e.g. `DeskHandler.timeout = 5`) so a stalled
read raises and the failure panel is rendered.

---

_Reviewed: 2026-10-12T23:33:09Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
