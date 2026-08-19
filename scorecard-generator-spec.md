# Score Card Generator — Development Spec

## 1. Purpose

A tool that turns a participant export and a boulder-per-category mapping into
print-ready score cards for indoor boulder competitions.

It replaces a manual process: a Word template + mail merge + print to PDF, with the
boulder numbers written on the cards by hand.

## 2. Hard constraints

These are non-negotiable and drive most of the design.

| # | Constraint | Reason |
|---|---|---|
| C1 | Single self-contained HTML file. No build step, no bundler, no CDN references, no external fonts. | Must run offline from a USB stick in a sports hall with bad wifi. |
| C2 | All processing client-side. No server, no upload, no network calls at runtime. | Participant data includes names of minors. Nothing leaves the device — this removes the tool from GDPR processing scope almost entirely. |
| C3 | Output is produced via the browser print dialog (`Ctrl+P` → Save as PDF). No PDF library. | Simpler, and matches the existing "print to PDF" workflow. |
| C4 | Target browser is Chrome/Edge. Do not spend effort on cross-browser print quirks. | Internal tool, controlled environment. |
| C5 | Must be greyscale-safe. Colour may be used, but no information may be conveyed by colour alone. | Colour toner cost is prohibitive at volume. |
| C6 | Never render cards when validation produces a hard error. | 77 wrong cards is a reprint plus a delayed competition. |

## 3. Users

- A competition organiser preparing cards the evening before, on a laptop.
- Not a developer. Comfortable with Excel and a browser, nothing more.
- Under time pressure. Errors must be caught by the tool, not by the user.

## 4. Data inputs

### 4.1 Participant list (required)

Exported from the etto-climbing platform as CSV.

- **Delimiter:** semicolon (`;`)
- **Encoding:** UTF-8, may contain a BOM — strip it
- **Header row present**
- **Columns:** `Category;Starting number;Ranking;Name`

Example rows:

```
Category;Starting number;Ranking;Name
u11 (meisjes/jongens);80;8;Jansen Sophie
u19 (jongens);69;5;De Smet Lucas
u15 (meisjes);6;2;Peeters Emma
```

Field handling:

- `Category` — free-text string, e.g. `u15 (meisjes)`. Treat as an **opaque key**. Do
  not parse, normalise, or infer age/gender from it. Match exactly against the boulder
  mapping (after trimming surrounding whitespace only).
- `Starting number` — integer, unique across the whole competition. Not contiguous
  within a category.
- `Ranking` — present in the export but **ignored**. It is filled in a results export
  and irrelevant before the competition.
- `Name` — single field, format is `Surname Firstname` or similar. Do not split.
  Must handle accented characters, apostrophes, and long double surnames.

The parser must handle RFC-4180 quoting (quoted fields, embedded delimiters,
embedded newlines, doubled quotes). Write ~40 lines of parser rather than vendoring a
library — a dependency conflicts with C1.

Ignore any extra columns present in the file. Do not fail on them.

### 4.2 Boulder-per-category mapping (required)

Which boulder numbers each category climbs. **Differs per competition.**

Three input methods must all be supported, in this priority order:

1. **Paste JSON** — pasted from the etto platform's network response by a jury account
   holder. The app must accept a pasted blob and let the user map fields if the shape
   is unknown. Accept a lenient shape: any JSON that can be reduced to
   `{ category: string, boulders: number[] }[]`.
2. **Paste table** — user selects the boulder overview table on the etto page,
   pastes it in. Accept both orientations: boulders as rows and categories as rows.

   **Verified clipboard behaviour, do not assume clean TSV.** The etto route table was
   copied out of Chrome and inspected. Because its cells contain block-level elements
   and inline SVG, Chrome emits **one tab per row** (after the first cell) and puts the
   remaining cells on their own lines. Worse, the category badges in the `Groups` cell
   are concatenated **without any separator**:

   ```
   10<TAB>
   N/A
   1
   u11 (meisjes/jongens)u13 (jongens)u13 (meisjes)u15 (jongens)u15 (meisjes)u19 (meisjes)
   ```

   A column/delimiter-based parser therefore cannot work. The parser must instead:

   - split the paste into **records**, starting a new record at every line containing a tab;
   - find category names by **substring match against the categories already loaded from
     the participant CSV**, longest first, consuming each match so overlapping names
     cannot double-count;
   - strip the matched category text **before** reading any integers — category names
     contain digits (`u11`, `u13`) and would otherwise be read as boulder numbers;
   - take the boulder number from the record's **first cell** when that cell is an
     integer (boulders as rows), or take all remaining integers when the first cell is a
     known category (categories as rows).

   This rule handles the messy real paste and clean TSV with the same code. It requires
   the participant CSV to be loaded first, because the category names are the anchor.
3. **Manual grid** — categories as columns, boulder numbers as rows, click to toggle.
   The categories come from the loaded participant CSV, so the grid is generated, not
   typed. Fallback only, for when the platform is unavailable.

**Boulder count per category is variable.** It is commonly 10 for a qualification
round but a final may have as few as 4. Do not hard-code any count anywhere.

### 4.3 Competition settings (required, entered in the UI)

- `title` — e.g. `ANTWERP BOULDER YOUTH CUP 2026`
- `subtitle` — optional, e.g. `Manche 4`
- `competitionId` — short slug used in the QR payload, e.g. `abyc2026-m4`
- `maxAttempts` — integer, default 5. Controls the number of attempt column pairs.
- `paperSize` — `A4` (default) or `A5`. See §6.1.
- `showQr` — boolean, default **on**. See §7.

### 4.4 Persistence

- Competition settings and the boulder mapping persist to `localStorage`, keyed by
  `competitionId`, so a reload or a crash does not lose work.
- The mapping can be exported to and imported from a JSON file, so next season's
  manche starts from a copy.
- **Participant data must never be written to `localStorage`.** It lives in memory for
  the session only. This keeps C2 clean.

## 5. Validation

Run all checks before rendering. Present results as a single report listing every
problem found — do not stop at the first one.

### Hard errors (block rendering)

| Check | Message intent |
|---|---|
| A category appears in the participant CSV but not in the boulder mapping | Name the category |
| A category appears in the boulder mapping but has no participants | Name the category |
| A boulder number occurs more than once within a single category | Name the category and the number |
| A category has zero boulders assigned | Name the category |
| Duplicate starting number in the participant CSV | Name the number and both rows |
| Empty or whitespace-only name, category, or starting number | Name the row |
| Starting number is not a positive integer | Name the row |

### Warnings (allow rendering, require explicit acknowledgement)

| Check | Reason |
|---|---|
| Categories have differing boulder counts | Legitimate for a final; usually a mistake in a qualification round |
| A category has more boulders than fit the card at minimum row height (see §6.4) | Layout will be cramped |
| A name exceeds the width that fits the name field | Will be truncated or wrap |

Note: the same boulder number **may** legitimately appear in several categories.
Do not deduplicate across categories.

A contender competes in exactly one category. One card per participant.

## 6. Print layout

### 6.1 Page

Two paper sizes, selectable in the UI. **The card itself is identical in both** —
210mm × 148.5mm, 8mm inner padding. Only the sheet around it changes, so nothing in
§6.2–§6.5 depends on this setting.

| Setting | `@page` | Cards per sheet | Cut line |
|---|---|---|---|
| `A4` (default) | `size: A4 portrait; margin: 0` | 2, stacked vertically | Dashed line at the 148.5mm boundary |
| `A5` | `size: A5 landscape; margin: 0` | 1 | None — the sheet *is* the card |

A5 is for a venue that can feed A5 directly and wants no cutting; A4 stays the default
because it is the cheaper and more widely available stock.

`@page size` cannot be driven by a CSS custom property, so the rule is swapped from
script at render time. Do not attempt a media-query or class-based solution.

- `print-color-adjust: exact` on any element with a background fill, or it will print
  white

On A4, if the total card count is odd, the last sheet has one card and an empty half. Do
not render a partial card.

### 6.2 Card content

Reproduces the existing Word template. Dutch labels, exactly as below.

**Header block**

- Competition title (and subtitle if set), full width
- `NAAM` — value: participant name
- `STARTNUMMER` — value: starting number, large and high-contrast, this is the field
  people read across a room
- `CATEGORIE` — value: category string, rendered large enough to identify the card at
  a glance during check-in distribution (see §6.5)
- QR code — top-right, adjacent to the start number, 20mm × 20mm, with a 2mm quiet
  zone. Must not overlap the cut line and must not sit where a right hand rests while
  writing.

**Score table**

Columns:

```
BOULDER | POGING 1 | POGING 2 | ... | POGING n | SCORE
```

Each `POGING` column and the `SCORE` column split into two subcolumns headed `Z` and
`T` (zone / top). With the default `maxAttempts` of 5 this gives 13 columns:
1 + (5 × 2) + 2.

Body: one row per boulder in that participant's category, with the boulder number
pre-filled in the `BOULDER` column. This pre-filling is the core purpose of the tool —
the number must be clearly legible, larger than the surrounding table text.

Footer row: `TOTALE SCORE`, with `T` and `Z` totals cells.

All tick cells must be empty and large enough to mark with a marker pen.

### 6.3 Sorting

Cards are ordered by **category, then starting number ascending**. Category order is
the order in which categories first appear in the boulder mapping; if the mapping has
no inherent order, sort alphabetically. This turns distribution at check-in into
handing out a stack.

### 6.4 Variable row count

The card height is fixed at 148.5mm. The score table body must flex to the number of
boulders in the category.

- Minimum row height: 8mm. Below this the cells are too small to mark reliably.
- With 4 boulders, distribute the extra vertical space by increasing row height up to
  a maximum of 14mm; do not leave a large blank void at the bottom of the card.
- Compute the maximum boulder count that fits at 8mm rows and raise a warning above it
  (§5). Do not silently overflow onto a second page — a card that spans two pages is
  a broken card.

### 6.5 Greyscale-safe category identification

Do not rely on colour. Use a large category label in a fixed position, in a heavy
weight, plus optionally a black fill band whose position varies per category (a
position-coded marker readable when cards are stacked and viewed edge-on).

Provide an optional colour toggle, default **off**, that adds a coloured header band
for organisers who do have colour printing available.

### 6.6 Control sheet

An optional first page, default **on**, printed before the cards:

- The full category × boulder matrix
- Participant count per category, and the total
- Competition title, subtitle, and generation timestamp

Purpose: the jury chief verifies one page against the platform before committing to a
70+ card print run.

The matrix orientation follows the paper size, because neither orientation fits both:

- **A4 portrait** — boulders as rows, categories as columns. Fits roughly 50 boulders.
- **A5 landscape** — transposed: categories as rows, boulders as columns. Fits roughly
  30 boulders.

Above those counts the matrix runs off the sheet. Acceptable for now; the control sheet
is a verification aid, not a card.

## 7. QR code

Optional, toggled in the UI, default **on**. With the QR off the header's left column
takes the freed 24mm, so the name field is wider and the "name too long" check (§5) must
widen with it — the threshold is derived from the field width, not hard-coded twice.

- **Payload:** `{competitionId}:{startingNumber}` — e.g. `abyc2026-m4:69`
- Plain text, not a URL. No personal data in the payload: no name, no category.
- Error correction level M. Quiet zone 2mm minimum.
- Library: `qrcode-generator` or `qrious`, **vendored inline** into the HTML file
  (C1). Both are small and MIT-licensed.

**Known limitation, do not design around it:** the QR identifies the card so a results
desk can pull up the right athlete quickly. It does **not** make the handwritten ticks
machine-readable. Automated result capture would require a redesign into an OMR bubble
sheet with registration marks, which is out of scope.

**Open item for the platform vendor:** the participant export currently contains no
persistent athlete ID, only a per-competition starting number. If an athlete ID column
is added to the export, the QR payload should become
`{competitionId}:{startingNumber}:{athleteId}`. Structure the payload builder so this
is a one-line change.

## 8. UI

Single page, linear top-to-bottom flow:

1. **Competition settings** — title, subtitle, competition ID, max attempts
2. **Participants** — file picker for the CSV; on load, show row count and the list of
   detected categories with participant counts
3. **Boulders** — three tabs for the three input methods (§4.2); after input, show a
   compact category × boulder summary
4. **Validation** — the full report; hard errors block the next step, warnings require
   a checkbox to proceed
5. **Print** — options (paper size A4/A5, QR on/off, control sheet on/off, colour
   on/off), then a preview of the first sheet and a print button

Requirements:

- Errors must be specific and actionable: name the category, the row, the number.
  "Invalid input" is useless to a stressed organiser at 22:00.
- The preview must be the actual print DOM, not a separate rendering. What is
  previewed is what prints.
- No modal dialogs for validation output — the report stays visible while the user
  fixes the source data.
- Interface language: Dutch (the users are Dutch-speaking and the card itself is
  Dutch).

## 9. Non-goals

- No scoring, ranking, or results calculation. The platform does that.
- No live/network integration with the platform. Paste and file import only.
- No user accounts, no multi-user state, no server.
- No OMR / automated reading of completed cards.
- No editing of participant data in the tool. Fix the source and re-export.

## 10. Acceptance criteria

1. Opening the HTML file from a USB stick with networking disabled produces cards
   end to end.
2. A 77-participant, 9-category, 10-boulder competition renders 77 cards on 39 sheets,
   sorted by category then starting number, in under 5 seconds.
3. A category with 4 boulders renders a card with 4 usable rows and no large blank
   void.
4. Removing one category from the boulder mapping produces a hard error naming that
   category, and no cards are rendered.
5. Introducing a duplicate boulder number within a category produces a hard error
   naming the category and the number.
6. A participant CSV with a BOM, accented characters, and a quoted field containing a
   semicolon parses correctly.
7. Printed at 100% scale with no printer scaling, a card measures 210mm × 148.5mm and
   the cut line falls at the sheet midpoint.
8. Every QR code scans on a standard phone camera and returns
   `{competitionId}:{startingNumber}`.
9. Printing in greyscale loses no information.
10. Switching to A5 produces one card per page, no cut line, and the same 210mm ×
    148.5mm card; switching back to A4 restores two-up.
11. Turning the QR off removes it from every card and widens the name field, and no card
    layout shifts otherwise.
12. Pasting the etto route table (in the messy real clipboard form of §4.2) reproduces
    the same mapping as entering it by hand in the grid.
13. Reloading the page restores the settings and the boulder mapping of the last
    competition, and never restores participant data.

## 11. Build order

1. CSV parser + participant load + category summary
2. Manual grid input (simplest boulder input, unblocks everything downstream)
3. Validation engine + report
4. Card rendering + print CSS + variable row height
5. QR codes
6. Control sheet
7. Paste-table and paste-JSON boulder input
8. localStorage persistence + mapping export/import

Ship after step 6 if time is short — steps 7 and 8 are convenience, not correctness.

All eight steps are implemented, plus the A4/A5 and QR toggles of §4.3.

## 12. Later, deliberately not now

Agreed as future work. Nothing below may complicate the code that exists today; each is
additive.

### 12.1 Alternative boulder input instead of the paint grid

Depends on what can be agreed with the etto platform vendor — ideally an export or a
stable endpoint rather than scraping a rendered table. Until that conversation happens,
the three input methods of §4.2 stand. Do not build speculative importers for shapes
nobody has produced yet.

### 12.2 Competition format

Today the card is fixed to the attempt-grid format: `maxAttempts` column pairs, judge
ticks Z and T per attempt.

A second popular format is **time-based**: the climber gets a fixed time per boulder and
the judge writes, once, the **number of attempts to zone** and the **number of attempts
to top**. That is a different score table — two wide write-in cells per boulder instead
of n tick pairs — not a variation in column count.

Implication for the current code: the score table must stay behind a single
`scoreTableHTML()` call so a `format` setting can pick a different table builder. Do not
spread attempt-column assumptions through the card layout or the validation.

### 12.3 Boulder count as a competition setting

A single "boulders in this competition" number, driving the grid's row range and
validated against the mapping, instead of the current "highest boulder number" input.
Cheap once someone decides what it should do when a category climbs a subset.
