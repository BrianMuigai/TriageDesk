# Phase 24 — SUMMARY

**Status:** complete · **Commits:** `ed4a095`, `1b8cf76`, `91e64c0`

The milestone's last phase measured the envelope, published the cost honestly, and answered the
reviewer's question in a dedicated document.

## Measured result (the headline)

On the full 24-case suite (real mode, 1 run per arm), the adaptive arm takes **2.1 steps** and the
baseline takes **0.0**; the guard overrode **3 of 23** proposals; the p50 rises from **18.26 s** to
**25.99 s** and p95 from **24.06 s** to **50.47 s**. Colour correctness (16/16), coverage (16/20),
clarifications (3) and the gate verdict are identical in both arms. The envelope buys adaptive behaviour,
not accuracy, on this suite — and the docs say exactly that.

## Verification

- `uv run pytest -q` → **900 passed**.
- `uv run ruff check src tests scripts` → clean.
- `uv run python scripts/emit_evals.py --check` → exit 0.
- `ARCHITECTURE.md` 663 words / 93 lines (guard ≤700 / ≤110).

## Honest gaps

- The comparison is 1 run per arm; the 3-run stability measurement remains §3.
- The eval harness cannot answer an elicitation (in-process, no MCP client), so every `ask_question`
  outcome is `unavailable` there. The real round-trip is proven at the adapter layer in Phase 21.
- A four-state observation model remains an outstanding limitation.
