# Phase 24 — SUMMARY

**Status:** complete · **Commits:** `ed4a095`, `1b8cf76`, `91e64c0`

The milestone's last phase measured the envelope, published the cost honestly, and answered the
reviewer's question in a dedicated document.

## Measured result (the headline)

On the four cases where an investigation action is admissible, the adaptive arm takes **2.8 steps** and
the baseline takes **0.0**; the guard overrode **1 of 4** proposals; the p50 rises from **14.32 s** to
**38.06 s**. Colour outcome is unchanged. The envelope buys adaptive behaviour, not accuracy, on this
suite — and the docs say exactly that.

## Verification

- `uv run pytest -q` → **900 passed**.
- `uv run ruff check src tests scripts` → clean.
- `uv run python scripts/emit_evals.py --check` → exit 0.
- `ARCHITECTURE.md` 663 words / 93 lines (guard ≤700 / ≤110).

## Honest gaps

- The full 24-case suite was **not** re-run in real mode for the comparison (host cost); §3.3 says so and
  §3 remains the last full-suite real measurement.
- The eval harness cannot answer an elicitation (in-process, no MCP client), so every `ask_question`
  outcome is `unavailable` there. The real round-trip is proven at the adapter layer in Phase 21.
- A four-state observation model remains an outstanding limitation.
