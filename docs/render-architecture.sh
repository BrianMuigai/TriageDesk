#!/usr/bin/env bash
# Render docs/assets/architecture.mmd to docs/assets/architecture.svg and
# docs/assets/architecture.pdf.
#
# The flow story is embedded in the .mmd source, so both assets are regenerated
# from one file (single source of truth).
#
# Requirements:
#   - node + npx on PATH (pulls @mermaid-js/mermaid-cli)
#   - a Chrome/Chromium binary: google-chrome, chromium, or chromium-browser
#     (override with CHROME_BIN=/path/to/chrome)
#
# Usage:
#   ./docs/render-architecture.sh

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
assets="$here/assets"
src="$assets/architecture.mmd"
puppeteer="$assets/puppeteer-config.json"
out_svg="$assets/architecture.svg"
out_pdf="$assets/architecture.pdf"
work="/tmp/opencode/arch-render"
page_width_in=20

[ -f "$src" ] || { echo "Missing source: $src" >&2; exit 1; }
command -v npx >/dev/null 2>&1 || { echo "npx not found on PATH" >&2; exit 1; }

chrome="${CHROME_BIN:-}"
if [ -z "$chrome" ]; then
  for c in google-chrome chromium chromium-browser; do
    if command -v "$c" >/dev/null 2>&1; then chrome="$(command -v "$c")"; break; fi
  done
fi
[ -n "$chrome" ] || { echo "No Chrome found; set CHROME_BIN" >&2; exit 1; }

mkdir -p "$work"

echo "Rendering Mermaid to SVG"
PUPPETEER_SKIP_DOWNLOAD=1 npx -y @mermaid-js/mermaid-cli@11 \
  -i "$src" -o "$work/arch.svg" -p "$puppeteer" -b white

echo "Building print HTML"
viewbox="$(grep -o 'viewBox="[^"]*"' "$work/arch.svg" | head -1 | sed 's/viewBox="//; s/"//')"
w="$(echo "$viewbox" | awk '{print $3}')"
h="$(echo "$viewbox" | awk '{print $4}')"
page_h_in="$(awk "BEGIN{printf \"%.2f\", $page_width_in*$h/$w}")"

{
  printf '<!doctype html><html><head><meta charset="utf-8"><style>'
  printf '@page{size:%sin %sin;margin:0}' "$page_width_in" "$page_h_in"
  printf 'html,body{margin:0;padding:0;background:#fff}'
  printf 'svg{width:100%% !important;height:auto !important;display:block;max-width:none !important}'
  printf '</style></head><body>'
  cat "$work/arch.svg"
  printf '</body></html>'
} > "$work/arch.html"

echo "Printing PDF (${page_width_in}in x ${page_h_in}in)"
"$chrome" --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$out_pdf" "file://$work/arch.html" >/dev/null 2>&1 || true

[ -s "$out_pdf" ] || { echo "PDF was not produced" >&2; exit 1; }
cp "$work/arch.svg" "$out_svg"

echo "Wrote $out_svg"
echo "Wrote $out_pdf"
