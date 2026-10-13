# REVIEW — TriageDesk live-review rehearsal runbook

> **One page, driven from the page.** This is the 10-minute Stage-2 live technical review. Every
> `uv run triagedesk …` invocation below is exercised against the shipped CLI by
> [`tests/test_review_runbook.py`](../tests/test_review_runbook.py), and the Beat-3 durable dismissal
> is driven **end-to-end** (pause → resume over a throwaway checkpoint file), so the walkthrough cannot
> drift from what the entry point actually runs. The headline claim is that the live extension is a
> **data edit** — one line in `data/sats_discriminators.yaml`, no code change.

> **What is human.** The screen recording and the public upload (YouTube/Vimeo) are **HUMAN** actions.
> This runbook prepares the beats and a runnable dry-run; it does **not** claim a video exists or is
> hosted. Everything else here is driven live from the page.

> **"Reload" means a fresh process.** The discriminator substrate is loaded **once per process**
> (`get_discriminators()` is `@lru_cache`d), so a YAML edit is honoured by running a **NEW**
> `uv run triagedesk …` command. There is **no** `--reload` flag and **no** cache-clear flag; do not
> imply a hot reload.

The measured artefacts this page links to are [`DEMO.md`](DEMO.md) (the demo runbook),
[`EVALS.md`](../EVALS.md) (the single source for every measured number) and
[`CONVENTIONS.md`](CONVENTIONS.md) (the DRY + SOLID rule the live edit demonstrates).

## Beat 0 — The shipped suite is green (baseline)

Before anything: the whole suite passes, so every claim later is against a green baseline.

```bash
uv run pytest -q
```

## Beat 1 — The agent works, on screen

Run the whole storyboard offline: real tool calls, real citations, no model and no network.

```bash
uv run triagedesk demo
```

## Beat 2 — Durability: a paused case survives a restart

Run one beat to the durable approval gate over the on-disk checkpointer, then resume it in a **new
process** under the named nurse. The `thread_id` is content-derived and printed by the first command;
paste it into the second.

```bash
uv run triagedesk demo --durable --beat escalation
uv run triagedesk resume --thread-id <content-id> --decision approve --approver "Nurse Demo" --role "triage nurse"
```

## Beat 3 — A legitimate refusal

A `dismiss` needs no identity and commits nothing — the gate refuses it and writes no queue row. A
dismissal resumes a **paused** thread, so the beat is **two** commands: pause a fresh case into a
throwaway checkpoint file, then resume the SAME thread/db and watch the gate refuse. The throwaway
file leaves the Beat-2 durable demo state untouched.

```bash
uv run triagedesk demo --durable --beat escalation --db /tmp/review-dismiss.db
uv run triagedesk resume --thread-id <content-id> --decision dismiss --db /tmp/review-dismiss.db
```

## Beat 4 — Read-only replay

Reconstruct a past case from the checkpoint plus the local span stream. Replay re-runs nothing and
writes nothing. Run this **after Beat 2** — it reads the case that pause left in the default
`checkpoints.db` (standalone, with no such checkpoint, it exits non-zero: `no checkpoint for
thread_id …`).

```bash
uv run triagedesk replay --thread-id <content-id>
```

## Beat 5 — The desk surface

Serve the one local page (loopback only). Open `http://127.0.0.1:8765`, enter vitals and a complaint,
read the sourced suggestion, then approve, edit or dismiss.

```bash
uv run triagedesk desk
```

## Beat 6 — The measured eval, honestly

The committed report is `mode: real` (3 runs × 16 cases ≈ 10 minutes) and is **silent** — it is **not**
streamed on screen. The measured artefact you show is the committed [`EVALS.md`](../EVALS.md) (opened in
an editor) plus the live `failure` beat, which prints the declared-vs-measured mismatch. The `--offline`
run below is the fast, deterministic rehearsal of the same harness.

```bash
uv run triagedesk eval --cases evals/cases --runs 3 --report /tmp/review-report.json --offline
uv run triagedesk demo --beat failure
```

The `failure` beat is the **E-09** declared failure: the vague complaint matches no discriminator, so
the score falls back to vitals alone and the beat prints `DECLARED: ORANGE` / `MEASURED: GREEN (SHOWN
MISMATCH)`. It is shown, unedited and un-tuned — never hidden.

## Beat 7 — THE HEADLINE: the live extension is a data edit

A reviewer adds ONE discriminator to `data/sats_discriminators.yaml`, reloads (a fresh process), and the
system re-scores with **no code change**.

1. **Show the starting state.** In the desk, enter the complaint `severe headache`. It matches no
   discriminator, so the case defers with the no-match banner — nothing is queued.
2. **Back up the machine authority**, then append ONE discriminator to an **existing** category
   (`very_urgent`) with a **unique** alias:

   ```yaml
   - id: severe_headache
     category: very_urgent
     label: "Severe headache"
     aliases: ["severe headache"]
   ```

3. **Reload = a NEW process.** Run the desk again and re-enter the same complaint; it now suggests
   ORANGE. Nothing was recompiled and no code was edited.
4. **Prove no code changed** — this must print nothing:

   ```bash
   cp data/sats_discriminators.yaml /tmp/sats_discriminators.bak.yaml
   git status --porcelain -- src/
   ```

5. **The safety suite is green WITH the addition** (the substrate-shape predicates hold for the new
   entry):

   ```bash
   uv run pytest -q
   ```

6. **Revert the data edit** (there is no in-band revert):

   ```bash
   git checkout -- data/sats_discriminators.yaml
   ```

**Legend:** add into an **existing** category — a new category reusing an existing colour, or a
duplicate alias, correctly fails the substrate-shape safety tests. The chosen alias is deliberately
**absent from every published `evals/cases/*.yaml`** fixture, so the demonstration adds a capability
rather than re-tuning a published case (it must never tune **E-09** green). This is the project's
open/closed claim (SOLID: O) shown live: extend by data, not by editing working code.

## House-keeping — the freeze

Any remaining documentation edit must land **before** the repository freeze — a post-deadline commit
disqualifies. The freeze itself is **not** rehearsed on the day; it lives in
[`ROADMAP.md`](ROADMAP.md) §Freeze.
