#!/usr/bin/env bash
#
# Render the TriageDesk submission demo video — one unedited screen recording of the
# shipped CLI, under 3 minutes, with the owned tool calls on screen and the measured
# evaluation and the declared failure shown. Deterministic given the shipped CLI output.
#
# Pipeline: record (real pty -> asciinema cast + captions) -> agg (cast -> mp4)
#           -> ffmpeg (pad a caption band, burn the captions) -> duration guard.
#
# Requires on PATH: python3, agg (cargo install --git https://github.com/asciinema/agg),
# ffmpeg, and the project's own `uv`. Produces docs/assets/triagedesk-demo.mp4.
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
export PATH="$HOME/.cargo/bin:$PATH"

FINAL="docs/assets/triagedesk-demo.mp4"
CAPTIONS="docs/assets/demo-captions.ass"
WORK="$(mktemp -d)"
CAST="$WORK/triagedesk-demo.cast"
RAW="$WORK/demo-raw.mp4"
trap 'rm -rf "$WORK"' EXIT

# Frame geometry of the agg render (font-size 16, DejaVu Sans Mono, 200x48 cells).
WIDTH=1946
RAW_HEIGHT=1098
BAND=142                      # the caption band padded below the terminal
HEIGHT=$(( RAW_HEIGHT + BAND ))
TRAILING=1                    # seconds of frozen last frame agg adds

command -v agg >/dev/null || {
  echo "agg not found on PATH (cargo install --git https://github.com/asciinema/agg)" >&2
  exit 1
}

echo "[render-demo] recording the shipped CLI into an asciicast + captions ..."
# The demo writes a runtime span log (gitignored) into the cwd; snapshot it so we only
# remove the one this run creates.
SPANS="spans.jsonl"
_spans_preexisting=0
[ -e "$SPANS" ] && _spans_preexisting=1
python3 scripts/record_demo.py --cast "$CAST" --captions "$CAPTIONS"
[ "$_spans_preexisting" -eq 0 ] && rm -f "$SPANS"

echo "[render-demo] rendering the cast with agg ..."
agg -q --font-family "DejaVu Sans Mono" --font-size 16 --theme dracula \
    --idle-time-limit 60 --last-frame-duration "$TRAILING" "$CAST" "$RAW"

raw_w=$(ffprobe -v error -select_streams v -show_entries stream=width -of csv=p=0 "$RAW")
[ "$raw_w" = "$WIDTH" ] || {
  echo "unexpected render width $raw_w (expected $WIDTH); captions would misalign" >&2
  exit 1
}

echo "[render-demo] burning captions into the bottom band ..."
# `fps=25` FIRST: the agg render is sparse (frames only on change), so the caption
# overlay must be evaluated on a dense timeline or it freezes at the last change.
ffmpeg -v error -y -i "$RAW" \
  -vf "fps=25,pad=${WIDTH}:${HEIGHT}:0:0:color=0x282a36,ass=${CAPTIONS}" \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -preset medium -movflags +faststart "$FINAL"

dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$FINAL")
echo "[render-demo] wrote $FINAL (${dur}s, ${WIDTH}x${HEIGHT})"
python3 - "$dur" <<'PY'
import sys
d = float(sys.argv[1])
if d >= 180:
    raise SystemExit(f"video is {d:.1f}s - over the 3-minute limit")
print(f"[render-demo] under the 3-minute limit ({d:.1f}s)")
PY
