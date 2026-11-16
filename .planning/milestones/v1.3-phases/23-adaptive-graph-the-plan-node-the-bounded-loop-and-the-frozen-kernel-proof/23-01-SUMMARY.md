# 23-01 — SUMMARY

**Status:** complete · **Commit:** `18bc16f`

- New `graph/planning.py`: `plan`, `gather_evidence`, `ask_question`, `re_extract`, `finish_investigation`,
  wired through `make_nodes`/`build_graph`; `TRACER_NODES` and `graph/__init__.py` updated.
- Exact topology: `retrieve → plan` (normal) and `retrieve → finish_investigation` (emergency), with
  `finish_investigation → score` as the only kernel entry.
- New `core/merge.py`: pure `merge_monotone` — fills only `None`, a stated value always wins, the original
  complaint and nurse answers are never overwritten.
- `InvestigationFacts` + the `plan`/`investigation`/`nurse_answers` state channels.
- Tests: `test_graph_planning.py`, `test_merge_monotone.py`; tool fakes and durability fixtures moved with
  the topology.
