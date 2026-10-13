---
phase: 10
review: 10-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "an uncaught ValueError on browser-reachable input (1e2) dropped the connection instead of surfacing the schema error"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "do_POST parsed Content-Length/body with no guard"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "loopback-only was not enforced; a wildcard bind exposed an unauthenticated surface"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "the vitals form was not repopulated on a validation error"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "the no-self-commit guard was evadable (relative imports, subpackages)"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "the trauma checkbox made the default path unreachable (unchecked → trauma omitted → recovery terminal, no gate) (iteration 2)"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "the unauthenticated surface was CSRF-reachable — a drive-by page could commit with a fabricated identity (iteration 2)"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "the guard was still evadable by importlib/__import__ (iteration 2)"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "a non-ASCII csrf_token crashed do_POST (compare_digest TypeError) (iteration 3)"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "the Origin check trusted the attacker-controlled Host, so DNS rebinding could commit a row (iteration 3)"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "an unescaped attribute interpolation / body-cap / duplicate render / lock / loopback-in-class (iteration 1 and 2 infos)"
  - id: IN-01
    severity: info
    disposition: open
    title: "the loopback Host parser accepts a bracket-suffixed host (raw-client-only, not browser-reachable) (final advisory)"
  - id: IN-02
    severity: info
    disposition: open
    title: "the loopback Host parser over-refuses some valid shorthands (127.1, localhost.) — usability nit (final advisory)"
  - id: IN-03
    severity: info
    disposition: open
    title: "no per-connection read timeout on a declared Content-Length — robustness nit on a loopback-only server (final advisory)"
open: 3
total: 14
recorded: 2026-10-13T03:40:00.000Z
---

# Phase 10: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | fixed in 62cd159 — the `int()`/`float()` pre-cast removed so the ONE `CaseInput` schema is the single coercion+validation rule; tests post `1e2`/`abc`/`40.5` and assert the rendered schema error *(iteration 1)* |
| WR-01 | warning | fixed | fixed in 01fc7ec — the `do_POST` header/body parse is guarded and renders the failure panel *(iteration 1)* |
| WR-02 | warning | fixed | fixed in f86608d — loopback enforced; a wildcard host refused unless explicitly opted in *(iteration 1)* |
| WR-03 | warning | fixed | fixed in 7f8a268 — the vitals form repopulates; the HTML bounds are derived from `CaseInput` *(iteration 1)* |
| WR-04 | warning | fixed | fixed in 186599d — the guard recurses the package and resolves relative imports *(iteration 1)* |
| CR-01 | critical | fixed | fixed in c43de4f — the Trauma checkbox is paired with a hidden `trauma=false` placed AFTER it, so an unchecked box submits an explicit `false` and the default submission reaches the card + gate *(iteration 2)* |
| WR-01 | warning | fixed | fixed in b61a792 — a per-server `secrets` CSRF token required on every POST (constant-time compare) + an `Origin`/`Host` same-origin check; a fabricated `/decision` commits zero rows *(iteration 2)* |
| WR-02 | warning | fixed | fixed in a357951 — the guard resolves literal `import_module`/`__import__` args AND the docstring claim was narrowed honestly *(iteration 2)* |
| WR-01 | warning | fixed | fixed in 0f6b4be — the CSRF token is compared as UTF-8 bytes, so a non-ASCII token cannot crash `do_POST` *(iteration 3)* |
| WR-02 | warning | fixed | fixed in b308be5 — a non-loopback `Host` is refused via a loopback allowlist before anything else, closing the DNS-rebinding path *(iteration 3)* |
| IN-01 | info | fixed | fixed across 1b48600, d0011c6, 213c382, 299fa67 (iteration 1) and 7de655a, 3c33674, 0e4cbe3, 30ac6eb (iteration 2) and fc1a92a, 73d1d69 (iteration 3) |
| IN-01 | info | open | sub-threshold advisory from the final review — raw-client-only, not browser-reachable; see 10-REVIEW.md |
| IN-02 | info | open | sub-threshold advisory (usability nit) — see 10-REVIEW.md |
| IN-03 | info | open | sub-threshold advisory (robustness nit on a loopback-only server) — see 10-REVIEW.md |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently.

> **Note on id reuse during the `--auto` loop.** `gsd-code-reviewer` numbers `WR-NN`/`IN-NN` per review pass, so
> an id is only stable within one iteration. Each row above carries a free-text Source cell naming the commit
> that fixed it and its iteration, so a reused id is unambiguous. Three ids are reused (`CR-01`, `WR-01`,
> `WR-02`) — each names a DIFFERENT defect, and all are fixed. The three `open` rows are the final review's
> sub-threshold advisories, which never blocked the phase.
