#!/usr/bin/env python3
"""Record the TriageDesk submission demo: an asciinema cast plus its captions.

A real interactive ``bash`` is driven through a pty — each command is typed
character by character, submitted, and the real terminal output is captured with
real timestamps. No value is invented: every line is what the shipped
``uv run triagedesk demo`` (offline, on the bundled synthetic fixtures) prints.

The beat NAMES are read from the ONE beat manifest (``demo/storyboard.yaml``), so
the video cannot name a beat the CLI does not expose. The narration and the hold
durations are the video's own concern and live here, in one place: this script
writes both the cast (rendered to video by ``agg``) and the ``.ass`` caption track
burned over it, deriving the caption timings from the recording it just made.

Usage: ``python3 scripts/record_demo.py --cast out.cast --captions out.ass``
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import pty
import select
import struct
import termios
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
STORYBOARD = REPO / "demo" / "storyboard.yaml"

COLS, ROWS = 200, 48
TYPE_DELAY = 0.026  # seconds per typed character
INTRO_HOLD = 4.5
CLOSE_HOLD = 6.0

# The on-screen projection of the committed, measured evaluation (never the ~10-minute
# silent run — `docs/DEMO.md` is the single source for that rationale).
PROJECTION_CMD = "sed -n '30,45p' EVALS.md"
PROJECTION_MARKER = "Reliability metrics"

INTRO = (
    "A busy OPD desk: 60-90 minute waits. An unsourced colour is dangerous, so every "
    "priority is cited and nothing is queued without a nurse."
)
CLOSE = "Open source, offline, synthetic. Every priority cited; every commit gated. TriageDesk."

# (kind, target, hold_seconds, caption). kind: "beat" runs `--beat <target>`;
# "cmd" runs <target> verbatim; "hold" runs nothing (a silent tail).
SEGMENTS: list[tuple[str, str | None, float, str]] = [
    (
        "beat",
        "routine",
        26.0,
        "Routine case gives GREEN. The complaint matches no "
        "discriminator, so the agent DEFERS - nothing reaches the queue.",
    ),
    (
        "beat",
        "escalation",
        26.0,
        "Escalated vitals give ORANGE. Only a named nurse's "
        "approval commits it - at queue position 1.",
    ),
    (
        "beat",
        "deterioration",
        24.0,
        "Serial vitals worsen, so the agent raises a "
        "second-look recheck flag. The case defers rather than commit a stale colour.",
    ),
    (
        "beat",
        "refusal",
        24.0,
        "The approval gate REFUSES to commit without the named nurse. No queue row is written.",
    ),
    (
        "cmd",
        PROJECTION_CMD,
        11.0,
        "The committed, measured evaluation: 16 cases x 3 runs; "
        "safety invariants 4/4 - generated from the report.",
    ),
    (
        "beat",
        "failure",
        20.0,
        "And the declared failure we did NOT hide: E-09 - declared "
        "ORANGE, measured GREEN (shown mismatch).",
    ),
    ("hold", None, CLOSE_HOLD, CLOSE),
]


def beat_names() -> set[str]:
    """The beat names the CLI exposes, read from the ONE manifest (DRY)."""
    return {entry["name"] for entry in yaml.safe_load(STORYBOARD.read_text(encoding="utf-8"))}


def command_for(kind: str, target: str | None) -> str | None:
    """The command a segment runs — a beat invocation or a literal command."""
    if kind == "beat":
        return f"uv run triagedesk demo --beat {target}"
    if kind == "cmd":
        return target
    return None


def marker_for(kind: str) -> str | None:
    """The first output a segment prints — so its caption starts when the output shows.

    Keying on the printed header (not the Enter keystroke) is what puts each narration
    line on screen alongside the beat it describes.
    """
    if kind == "beat":
        return "BEAT 1/1"  # the header a single-beat run prints
    if kind == "cmd":
        return PROJECTION_MARKER
    return None


def record(cast_path: Path, captions_path: Path) -> None:
    known = beat_names()
    for kind, target, _hold, _caption in SEGMENTS:
        if kind == "beat" and target not in known:
            raise SystemExit(f"storyboard has no beat named {target!r}; known: {sorted(known)}")

    pid, fd = pty.fork()
    if pid == 0:  # child
        os.chdir(REPO)
        env = dict(os.environ)
        env.update(
            {"TERM": "xterm-256color", "PS1": "desk $ ", "BASH_SILENCE_DEPRECATION_WARNING": "1"}
        )
        os.execvpe("bash", ["bash", "--norc", "--noprofile", "-i"], env)

    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))

    t0 = time.monotonic()
    events: list[list] = []

    def now() -> float:
        return time.monotonic() - t0

    def emit(data: bytes) -> None:
        if data:
            events.append([round(now(), 6), "o", data.decode("utf-8", "replace")])

    def pump(duration: float) -> None:
        end = time.monotonic() + duration
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            r, _, _ = select.select([fd], [], [], min(remaining, 0.02))
            if r:
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    return
                if not data:
                    return
                emit(data)

    def send(text: str) -> None:
        for ch in text:
            os.write(fd, ch.encode())
            pump(TYPE_DELAY)

    def first_output_after(mark: float, marker: str | None) -> float | None:
        """When the segment's own output first appears after *mark* (the Enter time)."""
        if marker is None:
            return None
        buf = ""
        for t, _k, d in events:
            if t <= mark:
                continue
            buf += d
            if marker in buf:
                return t
        return None

    def run(kind: str, target: str | None, hold: float) -> float:
        """Run one segment; return the time its caption should begin."""
        command = command_for(kind, target)
        if command is None:  # a silent tail
            start = now()
            pump(hold)
            return start
        send(command)
        enter_at = now()
        os.write(fd, b"\r")
        pump(hold)
        return first_output_after(enter_at, marker_for(kind)) or enter_at

    pump(INTRO_HOLD)
    starts: list[float] = [run(kind, target, hold) for kind, target, hold, _c in SEGMENTS]

    # A final visible change (a fresh prompt) so the renderer does not trim the trailing
    # hold — the closing caption must survive to the last frame.
    os.write(fd, b"\r")
    pump(0.5)
    total = now()
    events.append([round(total, 6), "o", "\u001b[0m"])

    header = {
        "version": 2,
        "width": COLS,
        "height": ROWS,
        "timestamp": int(time.time()),
        "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"},
    }
    with cast_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(header) + "\n")
        for ev in events:
            fh.write(json.dumps(ev) + "\n")

    write_captions(captions_path, starts, total)
    print(f"cast: {cast_path} ({len(events)} events, {total:.1f}s)")
    print(f"captions: {captions_path}")


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


def write_captions(path: Path, starts: list[float], total: float) -> None:
    """Write the caption track, timing each line to the segment it narrates."""
    width, height = 1946, 1240  # the rendered frame agg + the pad produce (see render-demo.sh)
    lines = [ASS_HEAD.format(w=width, h=height)]
    captions = [INTRO] + [c for *_x, c in SEGMENTS]
    bounds_start = [0.3] + starts
    bounds_end = starts + [total]
    for text, start, end in zip(captions, bounds_start, bounds_end, strict=True):
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
