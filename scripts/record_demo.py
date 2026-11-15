#!/usr/bin/env python3
"""Record the TriageDesk submission demo: an asciinema cast plus its captions.

A real interactive ``bash`` is driven through a pty — each command is typed character by
character, submitted, and the real terminal output is captured with real timestamps. No value
is invented: every line is what the shipped ``uv run triagedesk demo`` prints. The escalation
and clarify beats run ONLINE on the real local model (their mode line says so); the refusal and
failure beats replay the bundled synthetic fixture offline (their mode line says that too).

In the clarify beat the recorder waits for the agent's real ``[nurse] <field>>`` prompt — the
run paused inside the ``request_clarification`` MCP call — and only then types the presenter's
answer (Enter for each further prompt). It never passes ``--answer``; a clarify run in which the
model asks nothing aborts the recording.

Captions are timed from, and guarded by, the output they narrate: each cue starts when its
marker first appears on screen, and a missing marker, a missing mode line, a missing expected
outcome, a traceback or a warning on screen, or a run that does not return to the shell prompt
in time aborts the recording before any video is rendered. Beat names come from the ONE beat
manifest (``demo/storyboard.yaml``); every screen literal matched here is imported from
``triagedesk.demo.run``; the projection caption's figures are computed from the committed
report by the same ``Report`` + ``analyse`` the EVALS generator uses.

Usage: ``uv run python scripts/record_demo.py --cast out.cast --captions out.ass``
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import pty
import re
import select
import signal
import struct
import termios
import time
from dataclasses import dataclass
from pathlib import Path

from triagedesk.demo.run import (
    ELICIT_PREFIX,
    NURSE_PREFIX,
    TOOL_PREFIX,
    load_storyboard,
    mode_line,
)
from triagedesk.evals.analysis import analyse
from triagedesk.evals.invariants import INVARIANT_IDS
from triagedesk.evals.report import Report

REPO = Path(__file__).resolve().parents[1]
STORYBOARD = REPO / "demo" / "storyboard.yaml"
REPORT = REPO / "evals" / "results" / "report.json"

# The child shell's PS1 — and the text whose return marks a finished run (one literal, two uses).
PROMPT = "desk $ "
COLS, ROWS = 200, 48
TYPE_DELAY = 0.026  # seconds per typed character
INTRO_HOLD = 4.5
ANSWER_PAUSE = 1.8  # viewers read the question before the answer is typed
POLL = 0.1  # pump slice while waiting for a run to finish
SEGMENT_TIMEOUT = 150.0  # a run that does not return to the prompt in time aborts the recording
MAX_CAPTION_CHARS = 170  # two lines in the 142 px caption band

# The presenter's typed answer in the clarify beat: the nurse's free-text observation (the same
# words as the live run documented in docs/DEMO.md "Live final"), NOT a rule — the deterministic
# matcher decides what, if anything, it resolves.
CLARIFY_ANSWER = "low glucose, 2.1 mmol/L"

# The on-screen projection of the committed, measured evaluation (never the ~10-minute silent
# run — `docs/DEMO.md` is the single source for that rationale). A heading-to-source-line range,
# so line drift in EVALS.md cannot cut the table.
PROJECTION_CMD = "sed -n '/^## 3. Reliability metrics/,/Measured source/p' EVALS.md"
PROJECTION_MARKER = "Reliability metrics"

# Output that must never sit under a caption: a crash or any warning line. (A JSON
# ``"warning": null`` field is data, not a warning — the quote breaks the match.)
FORBIDDEN_OUTPUT = re.compile(r"Traceback \(most recent call last\)|warning:", re.IGNORECASE)

_NURSE_PROMPT = re.compile(re.escape(NURSE_PREFIX) + r" (\S+)> ")
_TOOL_LINE = re.compile(re.escape(TOOL_PREFIX) + r" (\S+) ")

INTRO = (
    "A busy OPD desk: 60-90 minute waits. An unsourced colour is dangerous, so every "
    "priority is cited and nothing is queued without a named nurse."
)
CLOSE = (
    "Open source, local, synthetic data. Every priority cited; every commit gated by a "
    "named nurse. TriageDesk."
)

# The outcome lines the demo prints, as patterns (the colour/state is the only varying part).
_COMMIT = r"commit\s*:\s*committed case \S+ at queue position \d+ \({colour}\)"


@dataclass(frozen=True)
class Cue:
    """One caption: shown from the moment *marker* (a regex) first appears in the segment's
    output; ``None`` means the segment's own start (the silent tail)."""

    marker: str | None
    text: str


@dataclass(frozen=True)
class Segment:
    """One recorded step. ``kind``: "beat" runs a storyboard beat, "cmd" runs *target*
    verbatim, "hold" runs nothing. ``hold`` is the reading pause AFTER the run returns to the
    prompt (for "hold", the whole tail). ``answers`` are typed at the run's real nurse prompts;
    ``expect`` are patterns the output must show though no caption starts on them."""

    kind: str
    target: str | None
    cues: tuple[Cue, ...]
    hold: float
    online: bool = False
    answers: tuple[str, ...] = ()
    expect: tuple[str, ...] = ()


def beat_names() -> set[str]:
    """The beat names the CLI exposes, read from the ONE manifest (DRY)."""
    return {beat.name for beat in load_storyboard(STORYBOARD)}


def projection_caption(report_path: Path) -> str:
    """The projection caption — every figure computed from the committed report.

    Loads and analyses the report exactly as ``scripts/emit_evals.py`` does, so the caption
    cannot drift from the EVALS.md table it narrates.
    """
    report = Report.model_validate_json(report_path.read_text(encoding="utf-8"))
    analysis = analyse(report)
    held = sum(1 for ok in report.invariants.values() if ok)
    return (
        f"The committed, measured evaluation: {len(report.cases)} cases x {report.runs} runs "
        f"on the local model - {analysis.colour_correct}/{analysis.colour_runs} colour-expected "
        f"runs correct, under-triage {analysis.under_triage_count}, safety invariants "
        f"{held}/{len(INVARIANT_IDS)}."
    )


def _beat_start(*, online: bool) -> str:
    """A beat's first marker: its own mode line, so the caption starts when the run does."""
    return re.escape(mode_line(offline=not online))


def segments() -> list[Segment]:
    """The video's script, built at call time (importing this module has no side effects)."""
    case = {beat.name: beat.case for beat in load_storyboard(STORYBOARD)}
    return [
        Segment(
            kind="beat",
            target="escalation",
            online=True,
            hold=5.0,
            cues=(
                Cue(
                    _beat_start(online=True),
                    "Online: the local open-weights model reads the nurse's note on CPU. Each "
                    f"{TOOL_PREFIX} line is a real MCP tool call; the colour comes from SATS "
                    "rules, never the model.",
                ),
                Cue(
                    _COMMIT.format(colour="ORANGE"),
                    "ORANGE, cited to the SATS TEWS bands - committed at queue position 1 only "
                    "after a named nurse approves.",
                ),
            ),
        ),
        Segment(
            kind="beat",
            target="clarify",
            online=True,
            hold=6.0,
            answers=(CLARIFY_ANSWER,),
            expect=(_COMMIT.format(colour="RED"),),
            cues=(
                Cue(
                    _beat_start(online=True),
                    "Live MCP elicitation on the same local model. A vague note: 'feeling "
                    "unwell', known diabetic, normal vitals. The planner picks its next step.",
                ),
                Cue(
                    re.escape(ELICIT_PREFIX),
                    "The agent stops INSIDE the request_clarification MCP call and asks the "
                    "nurse. She types what she measured.",
                ),
                Cue(
                    r"elicitation\s*:\s*accepted",
                    "Her answer is re-matched by the deterministic matcher: a cited SATS "
                    "discriminator makes it RED, committed under her named approval.",
                ),
            ),
        ),
        Segment(
            kind="beat",
            target="refusal",
            hold=8.0,
            cues=(
                Cue(
                    _beat_start(online=False),
                    f"Same {case['refusal']} case, replayed offline from the golden fixture "
                    "(the mode line says so) - this time no named nurse approves.",
                ),
                Cue(
                    r"GATE REFUSED",
                    "The approval gate REFUSES: no queue row is written. Nothing reaches the "
                    "queue without her.",
                ),
            ),
        ),
        Segment(
            kind="cmd",
            target=PROJECTION_CMD,
            hold=10.0,
            cues=(Cue(re.escape(PROJECTION_MARKER), projection_caption(REPORT)),),
        ),
        Segment(
            kind="beat",
            target="failure",
            hold=8.0,
            cues=(
                Cue(
                    _beat_start(online=False),
                    "And the failure we did NOT hide: the same vague "
                    f"{case['failure']} note, with no nurse answer (offline fixture).",
                ),
                Cue(
                    r"MEASURED\s*:\s*GREEN \(SHOWN MISMATCH\)",
                    "Declared ORANGE, the rules alone measure GREEN - shown, not hidden. The "
                    "agent can ask; it never guesses a colour.",
                ),
            ),
        ),
        Segment(kind="hold", target=None, hold=6.0, cues=(Cue(None, CLOSE),)),
    ]


def caption_texts(segs: list[Segment]) -> list[str]:
    """Every caption, in screen order: the intro, then each segment's cues."""
    return [INTRO] + [cue.text for segment in segs for cue in segment.cues]


def command_for(segment: Segment) -> str | None:
    """The ONE command builder: a beat invocation (``--online`` from the flag), a literal
    command, or nothing for a silent tail. No built command ever carries ``--answer``."""
    if segment.kind == "beat":
        online = " --online" if segment.online else ""
        return f"uv run triagedesk demo{online} --beat {segment.target}"
    if segment.kind == "cmd":
        return segment.target
    return None


def nurse_prompts(text: str) -> list[str]:
    """The fields of the real ``[nurse] <field>> `` prompts in *text*, in first-seen order.

    Echo lines (``[nurse] q1: …``) are not prompts; a redrawn prompt is not a new question.
    """
    return list(dict.fromkeys(_NURSE_PROMPT.findall(text)))


def answer_for(index: int, answers: tuple[str, ...]) -> str:
    """What to type at the *index*-th prompt: the scripted answer, else blank (Enter)."""
    return answers[index] if index < len(answers) else ""


def tools_on_screen(text: str) -> list[str]:
    """The sorted, distinct tool names of the ``[tool] <name> …`` lines in *text*."""
    return sorted(set(_TOOL_LINE.findall(text)))


def _label(segment: Segment) -> str:
    return f"{segment.kind} {segment.target!r}"


def check_segment(segment: Segment, output: str, answered: int) -> None:
    """Refuse to caption a screen that contradicts its captions (raises ``SystemExit``)."""
    name = _label(segment)
    if segment.kind == "beat":
        expected_mode = mode_line(offline=not segment.online)
        if expected_mode not in output:
            raise SystemExit(f"segment {name}: mode line {expected_mode!r} not on screen")
    for cue in segment.cues:
        if cue.marker is not None and not re.search(cue.marker, output):
            raise SystemExit(f"segment {name}: cue marker {cue.marker!r} never appeared")
    for pattern in segment.expect:
        if not re.search(pattern, output):
            raise SystemExit(f"segment {name}: expected output {pattern!r} never appeared")
    if segment.answers and answered == 0:
        raise SystemExit(f"segment {name}: the model asked nothing - no nurse prompt appeared")
    bad = FORBIDDEN_OUTPUT.search(output)
    if bad:
        raise SystemExit(f"segment {name}: {bad.group(0)!r} on screen")


class Terminal:
    """A real ``bash`` on a pty and the timestamped log of everything it printed."""

    def __init__(self, cwd: Path) -> None:
        env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        env.update(
            {"TERM": "xterm-256color", "PS1": PROMPT, "BASH_SILENCE_DEPRECATION_WARNING": "1"}
        )
        pid, fd = pty.fork()
        if pid == 0:  # child: a stranger's interactive shell in *cwd*
            os.chdir(cwd)
            os.execvpe("bash", ["bash", "--norc", "--noprofile", "-i"], env)
        self.pid, self.fd = pid, fd
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
        self.t0 = time.monotonic()
        self.events: list[tuple[float, str]] = []
        self._open = True

    def now(self) -> float:
        return time.monotonic() - self.t0

    def pump(self, seconds: float) -> None:
        """Capture output for *seconds*."""
        end = time.monotonic() + seconds
        while self._open:
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            ready, _, _ = select.select([self.fd], [], [], min(remaining, 0.02))
            if not ready:
                continue
            try:
                data = os.read(self.fd, 65536)
            except OSError:
                data = b""
            if not data:
                self._open = False
                return
            self.events.append((self.now(), data.decode("utf-8", "replace")))

    def type(self, text: str) -> None:
        for ch in text:
            os.write(self.fd, ch.encode())
            self.pump(TYPE_DELAY)

    def enter(self) -> float:
        """Press Enter; return the time it was pressed."""
        at = self.now()
        os.write(self.fd, b"\r")
        return at

    def output_since(self, t: float) -> str:
        return "".join(data for at, data in self.events if at > t)

    def first_match_after(self, t: float, pattern: str) -> float | None:
        """When the output after *t* first matched *pattern* (the arriving event's time)."""
        buf = ""
        for at, data in self.events:
            if at <= t:
                continue
            buf += data
            if re.search(pattern, buf):
                return at
        return None

    def wait_for(self, pattern: str, timeout: float) -> float:
        start = self.now()
        while self.now() - start < timeout:
            self.pump(POLL)
            at = self.first_match_after(start, pattern)
            if at is not None:
                return at
        raise SystemExit(f"timed out after {timeout:.0f}s waiting for {pattern!r}")

    def close(self) -> None:
        """Exit the shell and reap the child."""
        if self._open:
            try:
                os.write(self.fd, b"exit\r")
            except OSError:
                pass
            self.pump(2.0)
        try:
            done, _ = os.waitpid(self.pid, os.WNOHANG)
            if done == 0:
                os.kill(self.pid, signal.SIGKILL)
                os.waitpid(self.pid, 0)
        except ChildProcessError:
            pass
        os.close(self.fd)


def _await_return(term: Terminal, segment: Segment, enter_at: float) -> int:
    """Wait for the run to return to the shell prompt, answering each real nurse prompt.

    Returns how many prompts were answered. The answer is typed only after the prompt is on
    screen; the number of prompts is read from the output, never assumed.
    """
    deadline = time.monotonic() + SEGMENT_TIMEOUT
    answered = 0
    while True:
        term.pump(POLL)
        output = term.output_since(enter_at)
        if PROMPT in output:
            return answered
        for _field in nurse_prompts(output)[answered:]:
            term.pump(ANSWER_PAUSE)
            term.type(answer_for(answered, segment.answers))
            term.enter()
            answered += 1
        if time.monotonic() > deadline:
            raise SystemExit(f"segment {_label(segment)}: no shell prompt in {SEGMENT_TIMEOUT}s")


def run_segment(term: Terminal, segment: Segment) -> list[float]:
    """Run one segment; return each cue's start time (when its marker reached the screen)."""
    command = command_for(segment)
    if command is None:  # a silent tail
        start = term.now()
        term.pump(segment.hold)
        return [start for _cue in segment.cues]
    term.type(command)
    enter_at = term.enter()
    answered = _await_return(term, segment, enter_at)
    term.pump(segment.hold)
    check_segment(segment, term.output_since(enter_at), answered)
    starts: list[float] = []
    for cue in segment.cues:
        at = enter_at if cue.marker is None else term.first_match_after(enter_at, cue.marker)
        if at is None:
            raise SystemExit(f"segment {_label(segment)}: cue marker {cue.marker!r} not timed")
        starts.append(at)
    if any(later < earlier for earlier, later in zip(starts, starts[1:], strict=False)):
        raise SystemExit(f"segment {_label(segment)}: cues appeared out of order {starts}")
    return starts


def record(cast_path: Path, captions_path: Path) -> None:
    """Record every segment, then write the cast and the caption track it times."""
    segs = segments()
    known = beat_names()
    for segment in segs:
        if segment.kind == "beat" and segment.target not in known:
            raise SystemExit(f"storyboard has no beat {segment.target!r}; known: {sorted(known)}")

    term = Terminal(REPO)
    try:
        term.wait_for(re.escape(PROMPT), 10.0)
        term.pump(INTRO_HOLD)
        starts = [at for segment in segs for at in run_segment(term, segment)]
        # A final visible change (a fresh prompt) so the renderer does not trim the trailing
        # hold — the closing caption must survive to the last frame.
        term.enter()
        term.pump(0.5)
        total = term.now()
        session = term.output_since(-1.0)
    finally:
        term.close()

    header = {
        "version": 2,
        "width": COLS,
        "height": ROWS,
        "timestamp": int(time.time()),
        "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"},
    }
    with cast_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(header) + "\n")
        for at, data in term.events:
            if at <= total:
                fh.write(json.dumps([round(at, 6), "o", data]) + "\n")
        fh.write(json.dumps([round(total, 6), "o", "\u001b[0m"]) + "\n")

    texts = caption_texts(segs)
    write_captions(captions_path, list(zip([0.3, *starts], texts, strict=True)), total)
    tools = tools_on_screen(session)
    print(f"cast: {cast_path} ({len(term.events)} events, {total:.1f}s)")
    print(f"captions: {captions_path} ({len(texts)} cues)")
    print(f"tools on screen: {len(tools)} ({', '.join(tools)})")


def _ts(seconds: float) -> str:
    """Format seconds as an ASS timestamp ``H:MM:SS.cc``."""
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


ASS_HEAD = (
    "[Script Info]\n"
    "ScriptType: v4.00+\n"
    "PlayResX: {w}\n"
    "PlayResY: {h}\n"
    "WrapStyle: 0\n"
    "ScaledBorderAndShadow: yes\n"
    "YCbCr Matrix: TV.709\n"
    "\n"
    "[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
    "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
    "MarginR, MarginV, Encoding\n"
    "Style: Caption,DejaVu Sans,34,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,"
    "0,0,0,0,100,100,0,0,1,2,0,2,70,70,40,1\n"
    "\n"
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)


def write_captions(path: Path, timed: list[tuple[float, str]], total: float) -> None:
    """Write the caption track: each line from its start until the next one's (last: *total*)."""
    width, height = 1946, 1240  # the rendered frame agg + the pad produce (see render-demo.sh)
    lines = [ASS_HEAD.format(w=width, h=height)]
    ends = [start for start, _text in timed[1:]] + [total]
    for (start, text), end in zip(timed, ends, strict=True):
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{text}\n")
    path.write_text("".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cast", type=Path, required=True, help="where to write the asciicast")
    parser.add_argument(
        "--captions", type=Path, required=True, help="where to write the .ass captions"
    )
    args = parser.parse_args(argv)
    record(args.cast, args.captions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
