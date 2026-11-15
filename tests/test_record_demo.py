"""The demo recorder's script, guards and pty answer loop — no Ollama needed.

``scripts/record_demo.py`` drives a real shell over a pty and turns what it captured into the
submission video's cast and caption track. These tests pin its honesty contract: each beat
command is built once (online beats carry ``--online``, none carries ``--answer``), every caption
is backed by output the screen actually shows, the projection caption's figures are read from
the committed report, and the scripted nurse answer is typed only at a real ``[nurse]`` prompt.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from triagedesk.demo.run import ELICIT_PREFIX, NURSE_PREFIX, TOOL_PREFIX, load_storyboard, mode_line
from triagedesk.evals.analysis import analyse
from triagedesk.evals.invariants import INVARIANT_IDS
from triagedesk.evals.report import Report

REPO = Path(__file__).resolve().parents[1]
RECORDER_PATH = REPO / "scripts" / "record_demo.py"
STORYBOARD = REPO / "demo" / "storyboard.yaml"
REPORT = REPO / "evals" / "results" / "report.json"


def _recorder() -> ModuleType:
    """Load ``scripts/record_demo.py`` by path (``scripts/`` is not a package).

    Registered in ``sys.modules`` before execution so its frozen dataclasses resolve their
    defining module (the ``tests/test_install_mcp.py`` pattern).
    """
    spec = importlib.util.spec_from_file_location("_record_demo", RECORDER_PATH)
    assert spec is not None and spec.loader is not None, f"could not load {RECORDER_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rec() -> ModuleType:
    """The recorder module, loaded once for the module's tests."""
    return _recorder()


def _beats(rec: ModuleType) -> list:
    return [s for s in rec.segments() if s.kind == "beat"]


def _well_formed(rec: ModuleType, segment) -> str:
    """Synthetic output satisfying every guard of *segment* (built from its own patterns)."""
    parts = []
    if segment.kind == "beat":
        parts.append(mode_line(offline=not segment.online))
    samples = {
        r"commit\s*:\s*committed case \S+ at queue position \d+ \(ORANGE\)": (
            "  commit       : committed case abc at queue position 1 (ORANGE)"
        ),
        r"commit\s*:\s*committed case \S+ at queue position \d+ \(RED\)": (
            "  commit       : committed case abc at queue position 1 (RED)"
        ),
        r"elicitation\s*:\s*accepted": "  elicitation  : accepted",
        r"GATE REFUSED": "  GATE REFUSED : no queue row written",
        r"MEASURED\s*:\s*GREEN \(SHOWN MISMATCH\)": "  MEASURED     : GREEN (SHOWN MISMATCH)",
        re.escape(ELICIT_PREFIX): f"{ELICIT_PREFIX} request_clarification asks q1: ?",
        re.escape(rec.PROJECTION_MARKER): "## 3. Reliability metrics",
    }
    for pattern in [c.marker for c in segment.cues if c.marker] + list(segment.expect):
        if re.search(pattern, "\n".join(parts)):
            continue
        parts.append(samples[pattern])
    return "\n".join(parts) + "\n"


# --- the segment script -------------------------------------------------------------------


def test_every_beat_segment_names_a_storyboard_beat(rec: ModuleType) -> None:
    known = {beat.name for beat in load_storyboard(STORYBOARD)}
    assert rec.beat_names() == known
    for segment in _beats(rec):
        assert segment.target in known, segment


def test_escalation_and_clarify_are_online_the_rest_offline(rec: ModuleType) -> None:
    online = {s.target: s.online for s in _beats(rec)}
    assert online == {"escalation": True, "clarify": True, "refusal": False, "failure": False}


def test_only_the_clarify_segment_carries_exactly_one_scripted_answer(rec: ModuleType) -> None:
    with_answers = [s for s in rec.segments() if s.answers]
    assert [s.target for s in with_answers] == ["clarify"]
    assert with_answers[0].answers == (rec.CLARIFY_ANSWER,)


# --- the one command builder --------------------------------------------------------------


def test_command_for_inserts_online_from_the_flag(rec: ModuleType) -> None:
    online = rec.Segment(kind="beat", target="clarify", cues=(), hold=0.0, online=True)
    offline = rec.Segment(kind="beat", target="refusal", cues=(), hold=0.0)
    assert rec.command_for(online) == "uv run triagedesk demo --online --beat clarify"
    assert rec.command_for(offline) == "uv run triagedesk demo --beat refusal"


def test_command_for_cmd_is_verbatim_and_hold_runs_nothing(rec: ModuleType) -> None:
    cmd = rec.Segment(kind="cmd", target="echo hi", cues=(), hold=0.0)
    hold = rec.Segment(kind="hold", target=None, cues=(), hold=1.0)
    assert rec.command_for(cmd) == "echo hi"
    assert rec.command_for(hold) is None


def test_no_segment_command_passes_an_answer(rec: ModuleType) -> None:
    for segment in rec.segments():
        assert "--answer" not in (rec.command_for(segment) or "")


# --- captions -----------------------------------------------------------------------------


def test_captions_are_intro_plus_every_cue_in_order(rec: ModuleType) -> None:
    segs = rec.segments()
    expected = [rec.INTRO] + [cue.text for s in segs for cue in s.cues]
    assert rec.caption_texts(segs) == expected


def test_every_caption_fits_the_band_and_is_ass_safe(rec: ModuleType) -> None:
    for text in rec.caption_texts(rec.segments()):
        assert len(text) <= rec.MAX_CAPTION_CHARS, (len(text), text)
        assert not set("{}\n") & set(text), text


def test_no_stale_caption_survives(rec: ModuleType) -> None:
    joined = " ".join(rec.caption_texts(rec.segments()))
    assert "16 cases" not in joined
    assert "DEFERS" not in joined
    assert "request_clarification" in joined


def test_write_captions_times_each_line_to_the_next(rec: ModuleType, tmp_path: Path) -> None:
    texts = rec.caption_texts(rec.segments())
    timed = [(0.3 + 2.0 * i, text) for i, text in enumerate(texts)]
    total = timed[-1][0] + 5.0
    out = tmp_path / "c.ass"
    rec.write_captions(out, timed, total)
    dialogue = [
        ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.startswith("Dialogue:")
    ]
    assert len(dialogue) == len(texts)

    def secs(stamp: str) -> float:
        h, m, s = stamp.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    bounds = [(secs(ln.split(",")[1]), secs(ln.split(",")[2])) for ln in dialogue]
    for start, end in bounds:
        assert start < end
    assert bounds[-1][1] == pytest.approx(total, abs=0.01)


def test_projection_caption_is_computed_from_the_report(rec: ModuleType) -> None:
    report = Report.model_validate_json(REPORT.read_text(encoding="utf-8"))
    analysis = analyse(report)
    held = sum(1 for ok in report.invariants.values() if ok)
    caption = rec.projection_caption(REPORT)
    assert f"{len(report.cases)} cases x {report.runs} runs" in caption
    assert f"{analysis.colour_correct}/{analysis.colour_runs}" in caption
    assert f"under-triage {analysis.under_triage_count}" in caption
    assert f"{held}/{len(INVARIANT_IDS)}" in caption


def test_projection_command_is_a_heading_to_source_range(rec: ModuleType) -> None:
    out = subprocess.run(
        ["bash", "-c", rec.PROJECTION_CMD], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    assert rec.PROJECTION_MARKER in out
    assert "Measured source" in out
    assert len(out.splitlines()) < 30


# --- prompt detection, answers, tools -----------------------------------------------------


def test_nurse_prompts_reads_the_real_prompts_not_echo_lines(rec: ModuleType) -> None:
    text = (
        f"{ELICIT_PREFIX} request_clarification asks q1: Ask about: glucose\r\n"
        f"{ELICIT_PREFIX} request_clarification asks q2: Ask about: ketones\r\n"
        f"{NURSE_PREFIX} q1> low glucose, 2.1 mmol/L\r\n"
        f"{NURSE_PREFIX} q1: low glucose, 2.1 mmol/L\r\n"
        f"{NURSE_PREFIX} q2> "
    )
    assert rec.nurse_prompts(text) == ["q1", "q2"]


def test_answer_for_types_the_script_then_enter(rec: ModuleType) -> None:
    assert rec.answer_for(0, ("A",)) == "A"
    assert rec.answer_for(1, ("A",)) == ""


def test_tools_on_screen_lists_distinct_tool_names(rec: ModuleType) -> None:
    text = (
        f"{TOOL_PREFIX} score_priority {{}} -> {{}}\n"
        f"{TOOL_PREFIX} plan_next_step {{}} -> {{}}\n"
        f"{TOOL_PREFIX} score_priority {{}} -> {{}}\n"
        "noise\n"
    )
    assert rec.tools_on_screen(text) == ["plan_next_step", "score_priority"]


# --- honesty guards -----------------------------------------------------------------------


def test_check_segment_passes_well_formed_output(rec: ModuleType) -> None:
    for segment in rec.segments():
        if segment.kind == "hold":
            continue
        answered = len(segment.answers)
        rec.check_segment(segment, _well_formed(rec, segment), answered)


def _clarify(rec: ModuleType):
    return next(s for s in rec.segments() if s.target == "clarify")


def test_check_segment_requires_the_beats_own_mode_line(rec: ModuleType) -> None:
    segment = _clarify(rec)
    good = _well_formed(rec, segment)
    wrong = good.replace(mode_line(offline=False), mode_line(offline=True))
    with pytest.raises(SystemExit, match="clarify"):
        rec.check_segment(segment, wrong, 1)


def test_check_segment_requires_every_cue_marker(rec: ModuleType) -> None:
    segment = _clarify(rec)
    good = _well_formed(rec, segment)
    with pytest.raises(SystemExit, match="clarify"):
        rec.check_segment(segment, good.replace(ELICIT_PREFIX, "[x]"), 1)


def test_check_segment_requires_every_expect_pattern(rec: ModuleType) -> None:
    segment = _clarify(rec)
    good = _well_formed(rec, segment)
    with pytest.raises(SystemExit, match="clarify"):
        rec.check_segment(segment, good.replace("(RED)", "(GREEN)"), 1)


def test_check_segment_aborts_when_the_model_asked_nothing(rec: ModuleType) -> None:
    segment = _clarify(rec)
    with pytest.raises(SystemExit, match="clarify"):
        rec.check_segment(segment, _well_formed(rec, segment), 0)


@pytest.mark.parametrize(
    "noise",
    [
        "Traceback (most recent call last):\n  File x",
        "LangChainBetaWarning: the API may change",
        "warning: `VIRTUAL_ENV=/x` does not match",
    ],
)
def test_check_segment_refuses_tracebacks_and_warnings(rec: ModuleType, noise: str) -> None:
    segment = _clarify(rec)
    with pytest.raises(SystemExit, match="clarify"):
        rec.check_segment(segment, _well_formed(rec, segment) + noise, 1)


def test_a_json_warning_field_is_not_a_warning(rec: ModuleType) -> None:
    segment = _clarify(rec)
    rec.check_segment(segment, _well_formed(rec, segment) + '{"warning": null}\n', 1)


# --- the real pty round-trip --------------------------------------------------------------


@pytest.mark.skipif(os.name != "posix", reason="needs a POSIX pty")
def test_the_answer_is_typed_only_at_a_real_prompt(rec: ModuleType, tmp_path: Path) -> None:
    script = tmp_path / "ask.py"
    script.write_text(
        f"a = input({NURSE_PREFIX!r} + ' q1> ')\n"
        f"b = input({NURSE_PREFIX!r} + ' q2> ')\n"
        "print('got', repr(a), repr(b))\n",
        encoding="utf-8",
    )
    segment = rec.Segment(
        kind="cmd",
        target=f"{sys.executable} {script.name}",
        cues=(),
        hold=0.2,
        answers=(rec.CLARIFY_ANSWER,),
    )
    term = rec.Terminal(tmp_path)
    try:
        term.wait_for(re.escape(rec.PROMPT), 10.0)
        start = term.now()
        rec.run_segment(term, segment)
        output = term.output_since(start)
    finally:
        term.close()
    assert "got 'low glucose, 2.1 mmol/L' ''" in output
