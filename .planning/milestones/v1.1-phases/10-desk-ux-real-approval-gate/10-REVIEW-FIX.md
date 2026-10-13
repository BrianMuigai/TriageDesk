---
phase: 10-desk-ux-real-approval-gate
fixed_at: 2026-10-12T23:27:34Z
review_path: .planning/phases/10-desk-ux-real-approval-gate/10-REVIEW.md
iteration: 3
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-10-12T23:27:34Z
**Source review:** `.planning/phases/10-desk-ux-real-approval-gate/10-REVIEW.md`
**Iteration:** 3

**Summary:**
- Findings in scope: 4 (the two remaining **warnings**, WR-01 and WR-02, plus the two **INFO** items
  the iteration-3 prompt directed to be fixed if cheap: IN-01 and IN-02)
- Fixed: 4
- Skipped: 0

The two warnings were both residual gaps in the iteration-2 CSRF hardening: one reachable unhandled
exception (WR-01) and one attacker-controlled trust anchor (WR-02). Each fix is pinned by a
regression test that was verified to **fail before** the fix and pass after.

## Fixed Issues

### WR-01: A non-ASCII `csrf_token` raised `TypeError` inside `do_POST` — the handler crashed and dropped the connection instead of rendering the failure panel

**Files modified:** `src/triagedesk/desk/server.py`, `tests/test_desk.py`
**Commit:** `0f6b4be`
**Applied fix:** Root-cause fix in `_csrf_ok` — compare on UTF-8 **bytes** rather than `str`:

```python
return bool(supplied) and secrets.compare_digest(
    supplied.encode("utf-8"), self.server.csrf_token.encode("utf-8")
)
```

`secrets.compare_digest` raises `TypeError` on a `str` carrying non-ASCII characters, and
`supplied` is attacker-controlled (`parse_qs` percent-decodes UTF-8). The server token is ASCII
(`secrets.token_urlsafe`), so encoding **both** sides is total and can never raise — the comparison
is now crash-proof rather than merely guarded. `_csrf_ok`'s docstring records why the bytes form is
required.

Regression test added: `test_non_ascii_csrf_token_renders_the_failure_panel` posts
`csrf_token=%C3%A9` (a single non-ASCII field) and asserts `200` + the documented failure panel
(`The case could not be scored.`) with zero rows. Verified: this test **fails before** the fix (the
connection is dropped and `urlopen` raises `RemoteDisconnected`).

### WR-02: The CSRF `Origin` check trusted the attacker-controlled `Host` header — a DNS-rebinding page reached the commit path

**Files modified:** `src/triagedesk/desk/server.py`, `tests/test_desk.py`
**Commit:** `b308be5`
**Applied fix:** Pinned the accepted `Host` to loopback, so the `Origin` comparison only ever sees a
genuine loopback origin:

- A new `_LOOPBACK_HOSTNAMES` (`{"localhost"}`) plus a module-level `_loopback_host(host_header)`
  parser: the bracketed IPv6 form (`[::1]`) else the part before the last colon, then
  `ipaddress.ip_address(...).is_loopback` (accepts any `127.0.0.0/8` address and `::1`). The port is
  deliberately ignored — a rebind reaches the real port, so the **hostname** is the discriminator.
  Parsing is by hand rather than `urlsplit` so a `user@host` userinfo trick cannot smuggle a
  loopback tail past the check; a malformed or absent `Host` is refused.
- `DeskHandler._host_ok()` delegates to it. `do_POST` refuses a non-loopback `Host` **first** with
  the documented failure panel (`_FAILURE_COPY`); `do_GET` refuses it with `403`, so the token page
  is never served under a foreign host a rebinding page could read. `do_POST`'s docstring now
  documents the three pre-dispatch defences (host, origin, token).

Tests added (three): `test_dns_rebinding_foreign_host_is_refused` posts a valid token with
`Host: evil.example` **and** a matching `Origin: http://evil.example` and asserts the failure panel
+ zero rows (verified to **commit a row before** the fix); `test_foreign_host_get_is_refused`
asserts a foreign-host `GET /` is `403`; `test_loopback_host_accepts_only_loopback` pins the parser
(loopback with/without port, IPv6 brackets, `localhost` accepted; foreign names, `0.0.0.0`,
`192.0.2.1`, malformed `[::1`, and `evil@127.0.0.1` refused).

**Supporting edits.** The three raw-socket malformed-request tests (`test_malformed_request_*`,
`test_oversized_content_length_is_refused_without_reading`) now send `Host: 127.0.0.1` instead of
`Host: x`, so they keep exercising the `Content-Length`/body path rather than being short-circuited
by the new host check. `_post_status` was refactored into a generic `_request_status(url, data,
headers)` with `_post_status` delegating to it (DRY — the new GET test reuses the same
status/HTTPError handling).

### IN-01: The browser's checked-box serialisation (a duplicated `trauma` key) was not exercised end-to-end

**Files modified:** `tests/test_desk.py`
**Commit:** `fc1a92a`
**Applied fix:** Added `test_checked_trauma_duplicate_key_reaches_the_card_and_gate`, which builds
the exact body a browser sends for a **checked** Trauma box — the key twice, `trauma=true` then
`trauma=false`, via `urlencode([...], doseq=True)` (a dict cannot express the duplicate). It asserts
the card + gate render (not the recovery terminal) and, after a named approve, that the committed
row's idempotency hash (which covers the immutable case input, `trauma` included) equals
`content_hash(case_id, form_to_case({... "trauma": "true"}))` and differs from the `trauma=False`
hash — proving the row carries `trauma=True`.

### IN-02: The no-self-commit guard did not resolve a *relative* literal dynamic-import argument

**Files modified:** `tests/conftest.py`, `tests/test_desk.py`
**Commit:** `73d1d69`
**Applied fix:** Handled it (rather than only noting it). `_literal_dynamic_imports` now resolves a
relative `importlib.import_module(name, package)` whose first argument is a string literal against a
literal `package=` second argument, using `importlib`'s own algorithm (`_resolve_relative`, with a
`_literal_str_arg` helper): `importlib.import_module("..store.queue", "triagedesk.desk")` resolves
to `triagedesk.store.queue` and is caught, matching its absolute form. A name that climbs beyond the
package, or a relative call with no literal `package=`, is honestly reported unresolved — the
docstring's "literal" scoping is preserved. `test_commit_path_guard_catches_literal_dynamic_imports`
gains the relative case.

## Skipped Issues

None.

## Verification

- **Environment:** `workflow.use_worktrees` is `false`, so all fixes were edited and committed in the
  **main checkout** (no isolated worktree). The gate results below are reproducible from this tree.
- **Per-fix (Tier 1):** each modified section was re-read after editing; the staged diff for each
  atomic commit was inspected before committing.
- **Per-fix (Tier 2):** `ruff check` clean on every changed module (`server.py`, `test_desk.py`,
  `conftest.py`).
- **Regression proof:** the WR-01 and WR-02 tests were run against the pre-fix `server.py` (via a
  temporary `git stash` of only that file) and all **failed** as expected (`RemoteDisconnected` for
  the non-ASCII token; a committed row / `200` instead of refusal for the rebinding pair); they pass
  with the fix.
- **Suite:** `uv run pytest -q` -> **421 passed** (416 before this pass; +5 new test functions).
- **Atomic commits:** four, one per finding — `0f6b4be` (WR-01), `b308be5` (WR-02), `fc1a92a`
  (IN-01), `73d1d69` (IN-02) — each an additive, self-consistent subset.
- **Frozen spine untouched:** no change to `core/scorer.py` arithmetic, the citation helper, the
  `@audited` audit behaviour, the graph topology, the `durable` plumbing, `data/*.yaml`, or the
  `desk/` presentation contract beyond the two pre-dispatch guards; no new dependency; no SATS
  literal introduced in Python. Tests remain hermetic (loopback + injected store + `tmp_path`).
- **Logic caveat:** WR-01 (bytes comparison) and WR-02 (loopback `Host` allowlist) change conditions
  on the security path rather than being purely mechanical edits. Their behaviour is pinned by the
  five new tests above (each verified to fail pre-fix), so they are marked `fixed`; a human may still
  wish to confirm the accepted-host set (`127.0.0.0/8`, `::1`, `localhost`) matches the intended
  deployment.

---

_Fixed: 2026-10-12T23:27:34Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 3_

---

## UI review fixes (10-UI-REVIEW.md)

**Applied at:** 2026-10-13T00:03:59Z
**Source review:** `.planning/phases/10-desk-ux-real-approval-gate/10-UI-REVIEW.md`
(ADVISORY, 20/24, no BLOCKERs — three PRIORITY fixes + three cheap minors)
**Scope:** the three priority fixes and the three minor recommendations.

**Summary:**
- Priority fixes applied: **3** — each committed atomically.
- Minor recommendations applied: **3** (two as `10-UI-SPEC.md` contract amendments; one as code).
- Commits: **4** (`5b019ae`, `62de640`, `b2c217c`, `05eeccb`) — code-only; the planning-doc edits
  are left uncommitted (see *Doc handling*).
- Suite: `uv run pytest -q` → **424 passed** (421 before this pass; **+3** tests, one test replaced
  1:1). Hermetic — no repo-root `spans.jsonl`/`*.db` left behind.

### UI-1 (priority): declare the missing fifth SATS token

**Files modified:** `src/triagedesk/desk/static/styles.css`, `tests/test_desk.py`
**Commit:** `5b019ae`
**Applied fix:** Declared `--colour-blue: #0B3D91` and the `.colour-blue { background: …; color:
var(--surface); }` swatch, consistent with the other four tokens (on-colour `#FFFFFF`, contrast
10.2:1 — AA). `server.py` already maps a substrate `BLUE` to `colour-blue` (`_colour_class`), so a
future BLUE band now renders a coloured block instead of a transparent one. The colour *name* was
already shown as text, so colour was never the only signal.

Test: replaced `test_css_declares_exactly_the_editable_colour_swatches` with
`test_css_declares_every_substrate_colour_token`, which pins **all five** tokens by deriving the
expected set from the substrate's own `target_times` keys — never a Python literal (CONVENTIONS §1)
— and asserts the gate's offerable colours are a subset of the swatches (the gate can never offer a
colour it cannot render). The previous "no dead rule" equality is intentionally relaxed: the
contract declares BLUE for completeness even though the current `tews_to_colour` bands never
produce it.

### UI-2 (priority): make the schema-rejection copy true

**Files modified:** `src/triagedesk/desk/server.py`, `src/triagedesk/desk/static/styles.css`,
`tests/test_desk.py`
**Commit:** `62de640`
**Applied fix:** Chose the *highlight-the-field* branch (rather than rewording), so the mandated
copy `Check the highlighted field and try again.` is now literally true **and** the UI-SPEC's
`## UI Considerations` `error | vitals-form` row ("the schema's own message **beside that field**")
holds. Changes:

- `_vitals_field` gained an optional `field_error: (field, message)`; when it names the field, the
  control gets `aria-invalid="true"`, the `.field` gets a `.field-error` class, and the schema's own
  message renders inside that field (`role="alert"`). `_vitals_field` was refactored so all four
  control kinds share ONE wrapper (DRY) instead of four duplicated returns.
- `_validation_field(exc)` returns the first error's `loc` head; `_handle_case` renders a
  schema rejection **beside** the field (`render_state(field_error=…)`) and falls back to the error
  panel only for a (hypothetical) model-level error. The `state-panel` is now reserved for
  server/graph failures — which is what its component-table row always implied ("`vitals-form` …
  renders the schema's own rejection inline").
- `styles.css`: `.field-error` outlines the control in `--error-border`; `.field-error-message` is
  Body prose in `--error-text` (no new size/weight — the type scale is unchanged).

The Copywriting Contract's schema-rejection string is **unchanged** (it is now accurate), so no
copy edit was needed. Test added: `test_schema_rejection_renders_beside_the_offending_field`
(asserts the offending field carries `field-error` + `aria-invalid` + the message inside it, and
that the rejection is **not** only a panel below the form).

### UI-3 (priority): reconcile `--space-xl`

**Files modified:** `src/triagedesk/desk/static/styles.css`, `tests/test_desk.py`
**Commit:** `b2c217c`
**Applied fix:** Made the implementation match the contract rather than amending it: the card's
bottom margin is overridden to `var(--space-xl)` (32px) — the UI-SPEC's declared use ("Gap between
the card and the gate panel") — so the card↔gate gap renders at 32px, not the 48px section break,
and the previously-orphaned `--space-xl` token is now applied. Test added:
`test_card_gate_gap_uses_the_declared_xl_token`.

### Minor 1: accent on the form CTA

**Applied as a `10-UI-SPEC.md` contract amendment** (uncommitted — see *Doc handling*).
The reserved-for list named only the gate's `Approve suggestion`, but the form's
`Get suggested priority` is also a primary CTA (the review called this "defensible"). The list now
names both CTAs. The surface's accent usage is unchanged (two primary buttons + the focus ring),
still well within the 60/30/10 budget.

### Minor 2: the unfulfilled reserved accent use

**Applied as a `10-UI-SPEC.md` contract amendment** (uncommitted). The quickstart renders its four
steps as one prose line with no step indicator, so there is no "active step" to accent; the
unfulfilled reservation was removed and replaced with a one-line note recording why.

### Minor 3: client-side required affordance on the gate identity fields

**Files modified:** `src/triagedesk/desk/server.py`, `tests/test_desk.py`
**Commit:** `05eeccb`
**Applied fix:** `Your name`/`Your role` now carry `required`, so an approve/edit with a blank
identity is refused before the round-trip; the `Dismiss (commit nothing)` button carries
`formnovalidate` so the identity-free dismiss action is not blocked (dismiss commits nothing). The
server still enforces non-blank (whitespace-only) identity through `durable` — the attribute is a
cue, never the enforcement. Test added: `test_gate_identity_fields_carry_a_required_affordance`.

### Doc handling

- The two contract amendments above edit
  `.planning/phases/10-desk-ux-real-approval-gate/10-UI-SPEC.md`. That file lives under an
  **untracked** phase directory and the project sets `commit_docs: false`, so the fixer
  deliberately did **not** commit it (the same convention that leaves this `10-REVIEW-FIX.md`
  uncommitted); it is left in the working tree for the orchestrator's doc-handling step.
- No source file was left modified: `git status --short src tests` is clean after the four commits.

### Verification

- **Environment:** `workflow.use_worktrees` is `false`, so all fixes were edited and committed in the
  **main checkout** (no isolated worktree). The gate results below are reproducible from this tree.
- **Per-fix (Tier 1):** each modified section was re-read after editing; each atomic commit's staged
  diff was inspected before committing.
- **Per-fix (Tier 2):** `uv run python -c "ast.parse(...)"` clean on `server.py`; `uv run ruff check`
  clean on `server.py` and `test_desk.py`.
- **Suite:** `uv run pytest -q` → **424 passed** (421 before this pass). A repo-root `spans.jsonl` +
  `checkpoints.db` + `triage.db` left by an earlier probe (mtime 02:44, before this pass) were removed
  per the hermeticity rule; a re-run leaves none.
- **Frozen spine untouched:** no change to `core/scorer.py` arithmetic, the citation helper, the
  `@audited` audit behaviour, the graph topology, the `durable` plumbing, `data/*.yaml`, or the
  `desk/` presentation contract beyond the render plumbing above. No new dependency. No SATS literal
  introduced in Python — the colour names live only in `styles.css`, and the new test derives the
  five-token set from the substrate.
- **Logic caveat:** UI-2 and UI-3 change *which* markup/token is emitted on a live path rather than
  being purely mechanical, so they are marked `fixed: requires human verification` — both are pinned
  by the new tests, but a human may wish to glance at the rendered error state and the card↔gate gap
  in a browser.

---

_UI review fixes applied: 2026-10-13T00:03:59Z_
_Fixer: the agent (gsd-code-fixer)_
