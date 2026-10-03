# Score Card Scanning - Feature Spec

**Status:** Phase 2 built (branch `feat/scannable-card`). Phase 2 of 6.
**Next action:** Phase 2 STOP: print 3 cards, photograph them, check the overlay. Then: "Implement scan-feature-spec.md, Phase 3 only."

Addendum to `scorecard-generator-spec.md` and `i18n-feature-spec.md`.
Where this spec conflicts with the base spec, this spec wins.

**The card layout itself is unchanged.** The generator already prints one cell per attempt
(`BOULDER | POGING 1..n | TOP | ZONE`), no Z/T subcolumns, with white attempt cells. The
scanner relies on exactly that layout. Only the scan additions in Phase 1 are new.

---

## How to use this spec

1. Do **one phase at a time**, in order.
2. Each phase has a goal, a time estimate, numbered tasks, and a "Done when" checklist.
3. A phase is finished only when every "Done when" item is true.
4. **STOP** markers mean: stop and let Jeroen test on real paper before going on.
5. Formats, rules and thresholds used by several phases are in the **Reference** sections
   at the end. Look them up there; do not copy them into code comments.

---

## The flow (what this is for)

1. Judges score on paper. The card is then marked with two highlighters: zone colour in
   the attempt cell where the zone was reached, top colour where the top was reached.
2. A **scorecounter** photographs one card with a phone.
3. The app shows start number, category (no name) and a table: boulder, top attempts,
   zone attempts.
4. The scorecounter checks it against the card in hand, corrects if needed, and approves.
5. Approved results go into a CSV with one row per starter.

The scanner reads only the QR and the colour per attempt cell. Never handwriting, never
names. Totals are computed, never read from the card.

---

## Rules for every phase

| # | Rule | Why |
|---|---|---|
| S1 | Scanner is a separate single file `scan.html`. No build step, no CDN, no external fonts. Libraries vendored inline. | Same as base C1. Keeps the generator small. |
| S2 | All processing on the device. No upload, no network calls, no cloud AI. | Photos show names of minors. Same as base C2. |
| S3 | Photos in memory only, discarded after Approve or retake. Never stored anywhere. | Photos show names. |
| S4 | **Exception:** approved results (start number, category, attempt values) are saved to `localStorage`, keyed by `competitionId`. No names, no images. | A phone that reloads or dies must not lose an afternoon of scoring. |
| S5 | Photo input via `<input type="file" accept="image/*" capture="environment">`. No `getUserMedia`. | `getUserMedia` fails under `file://`. File input works everywhere at full resolution. |
| S6 | No OpenCV. Plain JS on `<canvas>`, plus `js-aruco2` (MIT) and `jsQR` (Apache-2.0), vendored. | OpenCV.js is ~8 MB. The maths needed is under 100 lines each. |
| S7 | Nothing enters the results list without an explicit Approve. | The machine proposes, the scorecounter decides. |
| S8 | Targets: Chrome on Android, Chrome/Edge desktop. iOS Safari best-effort but tested. | Phones at the score desk. |

`scan.html` may also be hosted as a static page (e.g. GitHub Pages) so phones can open it.
Static hosting serves code only, so S2 still holds.

---

## Phase 1 - Scannable card and scan profile (generator)

**Goal:** cards carry what the scanner needs; the generator exports a scan profile.
**Time:** about 1.5 to 2 hours.

Tasks:

1. **Setting.** Add competition setting `scannable`, default **on**, persisted with the
   competition settings.
   - On: adds markers (task 2) and forces `showQr = on` (toggle disabled with a one-line
     reason; hard validation error if somehow off).
   - **Decided in Phase 1:** there is no ID form field. `competitionId` is always derived
     from title + subtitle (short slug + 6-char hash, e.g. `rcyc-oost-288cd9`). Same title
     and subtitle give the same ID across reloads; another manche (other subtitle) gets
     another ID. No title and no subtitle: warning `scanNoId`, not an error.
   - Off: no markers.
2. **Markers.** Four ArUco markers (ARUCO 4x4, IDs 0-3), 5 mm, 1 mm white quiet zone,
   pure black, `print-color-adjust: exact`.
   - ID 0 top-left, ID 1 top-right, ID 2 bottom-right, ID 3 bottom-left.
   - **Decided in Phase 1 (Jeroen, after a test print):** the markers sit at the outer
     corners of the score table, beside it on the left and right, flush with the table's
     top and bottom edges, 1 mm from the table border. They are anchored to the rendered
     table in CSS, so they follow its real height. The table gets 12 mm narrower, not
     lower, so the row maximum is unchanged (10 at 8 mm for RCYC).
   - Where the attempt region lies relative to the markers is in the profile's
     `geometry` block (R1).
   - Never on the A4 cut line, never in the printer's unprintable page margin.
   - Only the RCYC format (one cell per attempt) is scannable.
3. **Calibration boxes.** Dropped in Phase 1 (Jeroen): they added no value on the card.
   Colour calibration comes from the session calibration and defaults (R3).
4. **Layout check.** Markers cost width, not height: a 16-boulder card warns at the same
   maximum as a non-scannable card (10 at 8 mm).
5. **Scan profile export.** Button **Export scanprofiel** in the Print step, enabled only
   when validation passes and `scannable` is on. Writes `scanprofile-{competitionId}.json`
   (format: Reference R1). Also print its `generatedAt` on the control sheet.
6. **Docs only.** If `scorecard-generator-spec.md` sections 4.3 and 6.2 still describe Z/T
   subcolumns per attempt, update the text to the actual card layout. No code change.

Do not change the existing score table. Do not add a `cardFormat` setting; it stays
reserved for the time-based format (base spec 12.2).

Done when:
- [x] Scannable card shows 4 markers and QR in NL, FR and EN
- [x] `scannable` off gives a card without markers
- [x] 16-boulder scannable card fits, or warns at the derived maximum
- [x] Profile JSON contains no names and category strings are byte-identical
- [x] Control sheet shows the profile timestamp

---

## Phase 2 - Scanner skeleton

**Goal:** a photo goes in, a straightened attempt grid comes out.
**Time:** about 2 hours.

Tasks:

1. Create `scan.html`: own i18n locale block (same approach as the i18n spec), Dutch
   default, mobile-first layout.
2. **Load profile.** Accept the JSON from R1. Refuse an unknown `layoutVersion` or schema
   with a specific message. Show competition title, card count, categories.
3. **Take photo.** One photo per scan (S5). Decode to canvas, downscale to max 3000 px on
   the long side.
4. **Find markers** with `js-aruco2`. Need IDs 0-3. Fewer than 4: "markers niet gevonden,
   opnieuw nemen". Never guess.
5. **Straighten.** Homography from the 4 marker corners to a canonical rectangle
   (10 px per mm). Warp the attempt region. Show the warped
   grid with `maxAttempts` x `boulderCount` lines overlaid (use the first category for
   now, real lookup comes in Phase 3).
   - **Decided in Phase 2:** a category dropdown (default: first category) stands in for
     the QR lookup, because the row count changes the marker geometry and test cards of
     other categories would otherwise never line up. Phase 3 replaces it with the QR.
   - Markers are searched on a copy downscaled to 1500 px (js-aruco2 is tuned for video
     frames); the warp samples the full-resolution photo.

Done when:
- [x] Works from `file://` with networking off
- [x] Sideways (90 degrees) and upside-down photos produce the same straight grid
- [x] Grid overlay lines up with the printed cell borders (synthetic photos: within
      0.4 mm; real paper pending the STOP below)

**STOP.** Jeroen prints 3 cards, photographs them with a phone (one sideways, one at an
angle), and checks the overlay. Do not start Phase 3 before that.

---

## Phase 3 - Reading the card

**Goal:** from a photo to a top/zone value per boulder, with flags.
**Time:** about 4 to 6 hours.

Tasks:

1. **Quality check** before reading. Reject with a retake message on: blur (Laplacian
   variance below threshold), markers smaller than ~25 px (too far away), large
   clipped-white areas in the attempt region (glare).
2. **Identify the card.** Decode the QR with `jsQR` from the area near marker 1. Parse
   `{competitionId}:{startingNumber}`. Block with a specific message if the competition
   ID does not match the profile or the start number is not in it. Look up category and
   boulder list.
3. **White balance** from unmarked cell pixels (high value, low saturation).
4. **Calibrate** with the default colour ranges for now (R3); session calibration comes
   in Phase 6.
5. **Classify cells.** Per attempt cell, sample the inner 70%, count pixels per colour,
   compute coverage, apply thresholds (R3). Then apply the decision rules per boulder row
   (R2). Compute totals (R4).

Write the decision rules and totals as pure functions with table-driven unit tests
covering every row of R2.

Done when:
- [ ] Photo to result in under 3 seconds on a mid-range phone
- [ ] Every row of R2 has a passing test
- [ ] Wrong competition ID and unknown start number are blocked with specific messages
- [ ] A blurry or glare photo gets a retake message instead of a result
- [ ] Yellow highlighter, ballpoint and pencil are ignored

---

## Phase 4 - Result screen and Approve

**Goal:** the scorecounter checks, corrects and approves one card.
**Time:** about 3 hours.

Layout:

```
Startnummer 66            u11 (meisjes/jongens)

Boulder | Top  | Zone
--------+------+-----
   1    |  1   |  1
  15    |  2   |  1
  19    |      |  1
--------+------+-----
Totaal  | 9 tops / 10 pog. | 10 zones / 10 pog.

[ Opnieuw scannen ]                 [ Goedkeuren ]
```

Tasks:

1. **Show** start number (large), category, the boulder / top / zone table in profile
   order, and totals. **Never a name.** Not reached = empty cell.
2. **Flags** on the affected row: icon plus text (not colour alone), with the reason.
3. **Correct.** Tap a top or zone value, pick from: empty, 1 .. `maxAttempts`. Totals
   recompute live. A top without a zone sets zone = top. Zone greater than top is blocked.
   Corrected values are visibly marked.
4. **Buttons.**
   - Goedkeuren: always available. On a flagged card that was not edited, ask one extra
     tap ("Toch goedkeuren").
   - Opnieuw scannen: discard and return to the camera.
   - After Approve: short confirmation ("66 toegevoegd"), discard the photo, go straight
     back to the camera.
5. **Thumbnail** of the warped grid with detected cells outlined, tap to enlarge.
   Optional for the scorecounter to look at.

Done when:
- [ ] No name appears anywhere in the scanner UI
- [ ] Editing a value recomputes totals and marks the value as corrected
- [ ] Nothing reaches the results list without Approve
- [ ] After Approve the app is back at the camera in one step

---

## Phase 5 - Results list and CSV

**Goal:** approved results are kept safely and exported per starter.
**Time:** about 2 hours.

Tasks:

1. **Store** approved results in `localStorage` per `competitionId` (S4). Restore them on
   page load.
2. **Duplicates.** Scanning an already approved start number shows the old and new result
   side by side; the scorecounter picks one. Never overwrite silently.
3. **Progress view.** Scanned / total per category, and the start numbers not yet scanned.
4. **Export CSV** at any time (also mid-competition). The browser cannot append to a file,
   so each export writes the complete list as `results-{competitionId}.csv` (format: R5).
   Optional `results-{competitionId}.json` with the same data plus metadata (R5).
5. **Clear results** for this competition, with confirmation. Also offered when a profile
   with a different `competitionId` is loaded.

Done when:
- [ ] Closing and reopening the page keeps all approved results
- [ ] No photo is ever found in any browser storage
- [ ] CSV opens in Excel with accents intact, one row per approved starter, no names
- [ ] Duplicate start number never overwrites silently

---

## Phase 6 - Fallback calibration, tests, pilot

**Goal:** robust enough for a real competition.
**Time:** about half a day of coding, plus one real competition session.

Tasks:

1. **Session calibration.** Once per session the scorecounter photographs one card and
   taps a known top cell and a known zone cell. Session only, never stored. Used for every
   card while the session lasts (R3). Record per result which calibration was used.
2. **Synthetic test script** (outside the shipped files, like `check_locales.py`): render
   scannable cards, paint highlighter-like strokes (semi-transparent, rotated, bleeding
   over borders), then apply rotation (incl. 90 and 180),
   perspective, a colour cast, a lighting gradient and a shadow band. Assert results.
3. **Extra tests:** no session calibration (defaults, flagged), swapped colours, overlapping hues, CSV
   round-trip with accented categories.
4. **README:** marking instructions for the jury, photo instructions for the scorecounter
   (card flat, whole card in frame, no spotlight or phone shadow, ink dry).
5. **Pilot:** 20 printed cards, real scorecounter, the actual marker models, real gym
   light, one Android and one iPhone. Measure cell error rate, flag rate, retake rate and
   time per card. Tune R3 thresholds from this data, then freeze them as defaults.

Done when:
- [ ] Synthetic fixtures: every cell correct or flagged, zero silent errors
- [ ] Without session calibration, cards use the defaults and are flagged
- [ ] Pilot: zero cells wrong and unflagged
- [ ] Pilot: average under 20 seconds per card from photo to Approve

---

## Reference R1 - Scan profile (generator to scanner)

`scanprofile-{competitionId}.json`:

```json
{
  "schema": "scorecard-scanprofile/1",
  "layoutVersion": 1,
  "competitionId": "abyc2026-m4",
  "title": "ANTWERP BOULDER YOUTH CUP 2026",
  "subtitle": "Manche 4",
  "maxAttempts": 5,
  "generatedAt": "2026-10-03T17:30:00+02:00",
  "geometry": {
    "markers": { "dictionary": "ARUCO_4X4_1000", "ids": [0, 1, 2, 3], "sizeMm": 5, "quietZoneMm": 1,
                 "referenceCorner": ["top-right", "top-left", "bottom-left", "bottom-right"] },
    "referenceWidthMm": 184,
    "regionLeftMm": 21.3,
    "regionWidthMm": 115.29,
    "regionTopMm": 6.3,
    "regionBottomGapMm": 16.3
  },
  "categories": [
    { "category": "u15 (meisjes)", "boulders": [1, 2, 3, 4, 5, 6], "rows": 6, "rowHeightMm": 11.08 }
  ],
  "cards": [
    { "startNumber": 6, "category": "u15 (meisjes)" }
  ]
}
```

- No names. The platform joins results to names via start number.
- User-initiated download only. Never written to `localStorage` by the generator.
- `layoutVersion` comes from constant `CARD_LAYOUT_VERSION` in the generator. Bump it on
  any change to attempt-table geometry or markers.
- `geometry`, in mm. Each marker has one reference corner, the one nearest the table
  corner (`referenceCorner`, per ID). Origin = marker 0's reference corner, x right,
  y down. The top reference corners are `referenceWidthMm` apart; the bottom ones lie
  `regionTopMm + rows * rowHeightMm + regionBottomGapMm` below the top ones. The attempt
  region runs from x `regionLeftMm` to `regionLeftMm + regionWidthMm` and from y
  `regionTopMm` to `regionTopMm + rows * rowHeightMm`.
- Per category, `rows` is the printed row count (it can exceed `boulders` when
  "boulders per category" pads blank rows; those trailing rows have no boulder number and
  are not read). Rows are equal height and attempt columns equal width
  (`regionWidthMm / maxAttempts`).
- `generatedAt` changes only when the profile's content changes, so the control sheet
  printed earlier shows the same value as a profile exported later.
- js-aruco2 also finds false markers inside the QR code (e.g. IDs 85, 376, 930). Keep
  only IDs 0-3.
- QR payload is unchanged: `{competitionId}:{startingNumber}`.

## Reference R2 - Decision rules per boulder row

`G` = attempt columns marked top colour, `P` = attempt columns marked zone colour.
Attempts are 1-based. Not reached = empty (`null` in JSON), never 0.

Normal cases:

| Marks | Top | Zone |
|---|---|---|
| G = {g}, no P | g | g (top implies zone) |
| G = {g}, P = {p}, p <= g | g | p |
| no G, P = {p} | empty | p |
| no G, no P | empty | empty |

Flagged cases:

| Marks | Top | Zone | Flag |
|---|---|---|---|
| G = {g}, P = {p}, p > g | g | g | error: zone after top |
| more than one G | earliest | as above | error: multiple tops |
| more than one P | as above | earliest | error: multiple zones |
| any uncertain cell in the row | as computed | as computed | warning: uncertain cell |

## Reference R3 - Colour classification

Calibration order per card:

The card has no calibration boxes (dropped in Phase 1).

1. **Session calibration** (Phase 6): from the tapped top and zone cells, take the
   saturated pixels and derive a hue range (median +/- spread, minimum width) plus
   saturation/value floors. Ranges must not overlap, otherwise reject it and ask again.
2. **Defaults** (flagged once session calibration exists): top (green) hue 75-165
   degrees, zone (pink/purple) 270-345 degrees, saturation >= 0.35, value >= 0.45.

Pixels outside both hue ranges are ignored. One zone colour per competition.

Coverage per attempt cell (start values, tune in the pilot):

| Coverage | Meaning |
|---|---|
| 20% or more | marked |
| 8% to 20% | uncertain, flag the cell |
| under 8% | not marked |

## Reference R4 - Totals

Per starter, always computed, never read from the card:
`tops`, `zones`, `topAttempts` (sum over boulders with a top), `zoneAttempts` (sum over
boulders with a zone). The scanner does not rank (base spec non-goal).

## Reference R5 - Exports

**CSV** `results-{competitionId}.csv`: semicolon-delimited, UTF-8 with BOM, one row per
approved starter, sorted by category (profile order) then start number.

```
Startnummer;Categorie;Tops;Zones;Pogingen top;Pogingen zone;B1 top;B1 zone;B2 top;B2 zone;...
66;u11 (meisjes/jongens);9;10;10;10;1;1;1;1;...
```

- Per-boulder columns for every boulder number in the competition, ascending. Empty where
  the category does not climb that boulder or it was not reached.
- Header labels via i18n, in the UI language. Category strings byte-identical.

**JSON** `results-{competitionId}.json` (optional): same data, plus `profileGeneratedAt`,
`exportedAt`, and per card `manualCorrections` and `calibration` (`session` /
`default`).

No names and no images in any export.

---

## Open items (Jeroen, not Claude Code)

1. **Where the CSV goes.** Agree an import format with the etto vendor. Until then the CSV
   in R5 is the output. Do not build an etto importer speculatively.
2. **Zone marker colour.** Pink or purple: pick one marker model for the jury kit.
3. **Who highlights.** Jury afterwards, or judges on the wall. README only, no code impact.
4. **Other organisers' cards** (no QR, no markers). Out of scope for v1.
