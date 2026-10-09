# SATS dual-transcription verification (D-10)

- **Generated:** 2026-10-09T12:17:46Z (UTC)
- **Method:** two independent transcriptions normalised to a common form
  and diffed band-by-band, parameter-by-parameter and discriminator-by-discriminator.
- **Script:** `scripts/transcribe_diff.py`

## Inputs (provenance)

| Transcription | File | sha256 |
| --- | --- | --- |
| A | `data/sats_tews.yaml` | `4427b048192b6774b9806517f6b86bad005680405de5dfc7a90298524b9889b8` |
| A | `data/sats_discriminators.yaml` | `8747a40b7ba9e1b9324ea987e5d2f553d3e282f22baecc96d29480d6c7da12ba` |
| B | `evidence/sats_transcription_b.yaml` | `e49149b4f929a5fe67212062a7c031a18463a970cade1911257c0f726dc56e72` |

## Compared

- **TEWS parameters:** 7 (bands, inclusive edges, points, units)
- **TEWS→colour thresholds:** 4
- **Target times / destinations:** 5
- **Out-of-scope predicate:** adult age/height + missing-age behaviour
- **Discriminator categories:** 41 ids → category

## Result

**VERIFICATION PASSED** — the two independent transcriptions agree on every band, threshold, target time, out-of-scope predicate and discriminator category.

## Resolved ambiguities

- **Issue:** The temperature row shows a blank in the 1-point column (docs/SATS.md §4).
  **Resolution:** There is no 1-point temperature band — the band is genuinely empty. Both transcriptions encode only the 0-point and 2-point temperature bands, so a temperature in the 0-point range scores 0 and any other in-range temperature scores 2. Encoded as data; never guessed.
- **Issue:** The manual's strict inequalities are written two ways (e.g. '< 9' vs an inclusive 'max: 8').
  **Resolution:** Normalised to a common inclusive form at each parameter's resolution (1 for integer scales, 0.1 for temperature): '< 9' == '<= 8', '> 38.4' == '>= 38.5'. The diff is resolution-aware, so both routes agree without either restating the other's convention.

## Residual uncertainty

- The published manual (Figures 2/5/12-14) was not available in this build window; verification is a dual transcription of docs/SATS.md, not a read of the original manual. The blank 1-point temperature column is treated as 'no 1-point band' and this residual uncertainty is flagged here and in docs/SATS.md.
- Target times and destinations are functional metadata transcribed from docs/SATS.md Table 3; they do not affect the TEWS score and are compared in the same diff for completeness.

## Scoping note (SC1)

`docs/SATS.md` is the **human-readable transcription reference** derived from the same SATS manual; it is **never imported at runtime**. `data/*.yaml` is the machine authority, and the SC1 'single source of truth' gate is scoped to **code + runtime**. `evidence/sats_transcription_b.yaml` is a verification artefact, not a runtime authority.

> `docs/SATS.md` remains the human-readable reference and links to the
> YAML as the machine source; it is not a second authority for the thresholds.
