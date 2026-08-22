# Score Table Seam — Refactor Spec

Addendum to `scorecard-generator-spec.md` (§12.2) and `i18n-feature-spec.md`.

**This is a pure refactor. The ABYC card must render byte-identically before and
after.** No new formats, no template engine, no config schema. The only deliverable is
that every assumption about attempt columns lives in one function instead of being
spread through the card layout and the validation.

---

## 1. Why now

Adding a second competition format later is either a new branch in one function or a
rewrite of the card renderer, and which one it is gets decided by this refactor. Doing it
while there is exactly one format is cheap; doing it after there are two is not.

Non-goal: supporting any format other than the current one. Every other capture mode
throws "not implemented" and stays that way until a real competition needs it.

---

## 2. The seam

One function. It renders a score table for a **category**, not for a participant.

```js
renderScoreTable({
  rows,            // [{ id, label, sublabel? }]
  capture,         // 'fixed-columns' | 'tally' | 'attempts-to' | 'none'
  attemptColumns,  // int >= 1; only valid when capture === 'fixed-columns'
  zones,           // 0 | 1 | 2
  rowScoreColumn,  // bool  — per-row score cells
  totalsRow,       // bool  — TOTALE SCORE footer
  variant,         // 'standard' | 'large-print'
  rowHeight,       // { min, max } in mm
  lang             // card language: 'nl' | 'fr' | 'en'
})  →  HTML string
```

Options object, not positional arguments, so adding a parameter never breaks a caller.

### 2.1 ABYC values

| Parameter | Value | Source |
|---|---|---|
| `rows` | boulder numbers for the category, in mapping order | validated boulder mapping |
| `capture` | `'fixed-columns'` | format constant |
| `attemptColumns` | `settings.maxAttempts` (5) | competition settings |
| `zones` | `1` | format constant |
| `rowScoreColumn` | `true` | format constant |
| `totalsRow` | `true` | format constant |
| `variant` | `'standard'` | print options |
| `rowHeight` | `{ min: 8, max: 14 }` | base spec §6.4 |
| `lang` | `settings.cardLanguage` | competition settings |

With `attemptColumns: 5` and `zones: 1` this produces the 13 columns of the Word
template: 1 + (5 × 2) + 2.

### 2.2 Deliberately not a parameter

**No `format` parameter.** `capture`, `attemptColumns` and `zones` already fully
describe the table. A format name on top would be a second source of truth that can
disagree with them. The mapping from a format to these parameters belongs in the
competition settings layer, not here.

**No participant data.** No name, no start number, no QR, no category label. If this
function ever needs one of those, the seam is in the wrong place.

**No colour or paper size.** Both are card-level concerns (base spec §6.1, §6.5).

---

## 3. Validation at the seam

`renderScoreTable` throws — never warns, never renders a degraded table — on:

1. `rows` empty or not an array.
2. `capture` not one of the four known modes.
3. `capture === 'fixed-columns'` with `attemptColumns` missing or below 1.
4. `attemptColumns` supplied for any other capture mode.
5. `zones` not in {0, 1, 2}.
6. `rows.length × rowHeight.min` exceeding the body height budget (§4).

Rule 3 is the important one. A fixed-column grid paired with a format that allows
unlimited attempts silently caps the attempt count and corrupts the result — the card
looks correct and the data is wrong. That must be impossible to express.

Rule 6 duplicates a check that belongs upstream in the validation engine (base spec §5),
which should have blocked rendering long before this point. It stays here as a backstop:
if a user ever sees it, the bug is that validation was bypassed, not that the card is
too full. Word the message to say so.

Defaults must be resolved **before** validation runs, or omitting an optional parameter
raises an error about that parameter instead of the real problem.

---

## 4. The body height budget

The row-height logic depends on one constant: the vertical space available to the table
body, in mm. It is the card height (148.5mm) minus inner padding, minus the header
block, minus the two table header rows.

**Measure it; do not calculate it from the spec.** Render a card, measure the body area
in the browser at print scale, and set the constant. A wrong value either rejects cards
that fit or lets a 16-row card overflow onto a second page, which is a broken card.

Row height is then `clamp(budget / rows.length, min, max)`:

- 10 rows → about 9.6mm
- 12 rows → floors at 8mm
- 4 rows → caps at 14mm, so a finals card has no void at the bottom

Re-measure whenever the header block changes — notably when the QR toggle moves the
header layout (base spec §7).

---

## 5. Language: the one behavioural trap

The function takes `lang` because the **card language is independent of the UI
language** (i18n spec §2). A Dutch interface printing French cards is a supported and
expected configuration.

This means `renderScoreTable` must not call the ambient `t()`, which resolves against
`uiLanguage`. Doing so produces a card in the wrong language while every visible test in
a Dutch interface passes.

Fix one of two ways, consistently:

- extend the lookup to `t(key, params, lang)` with `lang` defaulting to `uiLanguage`; or
- build a bound lookup at the top of the function: `const tc = (k, p) => t(k, p, lang)`
  and use `tc` everywhere inside.

Every string inside the score table — `BOULDER`, `POGING n`, `SCORE`, `TOTALE SCORE`,
and the Z/T markers if they ever become translatable — goes through it.

Also emit `lang="{lang}"` on the table element, so hyphenation and any future
locale-dependent typography behave.

---

## 6. The JS/CSS boundary

JS computes the row height and emits structure. CSS owns everything visual.

- Row height passes as a custom property on the table element: `style="--row-h:9.60mm"`,
  consumed by a single CSS rule. No inline styles on individual cells.
- Class names are the contract: `score-table`, `score-table--{variant}`, `col-item`,
  `col-marker`, `cell-item`, `cell-sub`, `cell-tick`, `cell-total-label`, `cell-total`.
- `data-cols="{n}"` on the table, so CSS and the layout test can key off column count
  without counting DOM nodes.
- The `large-print` variant is a CSS concern only. It must not require a different
  branch in JS — if it does, the density decisions have leaked into the wrong layer.

---

## 7. Work items

1. Extract the current inline table-building code into `renderScoreTable` unchanged.
2. Resolve defaults into a single config object, then validate it.
3. Replace every ambient `t()` call inside the table with the card-language lookup (§5).
4. Move row-height computation in from the card renderer; delete the old copy.
5. Measure and set the body-height constant (§4).
6. Move the cell/column class names into CSS; remove any inline per-cell styling.
7. Add the three throwing stubs for `tally`, `attempts-to` and `none`.
8. Grep the card renderer and the validation engine for remaining references to
   `maxAttempts`, attempt counts, or column arithmetic. Anything left outside this
   function and the settings layer is a leak — fix it now or the refactor bought nothing.

Step 8 is the one that determines whether this was worth doing.

---

## 8. Acceptance criteria

1. A 77-participant ABYC competition renders HTML **identical** to the pre-refactor
   output. Capture a card's markup before starting and diff against it.
2. `attemptColumns: 5`, `zones: 1` yields 13 columns, 12 tick cells per body row, and a
   footer label spanning 11 columns with 2 totals cells.
3. `rows: 4, attemptColumns: 4` yields 11 columns and rows at the 14mm cap.
4. 12 rows floor at 8mm; a row count that cannot fit at 8mm throws.
5. `capture: 'tally'` throws "not implemented", naming the mode.
6. `capture: 'tally'` with `attemptColumns: 5` throws before any rendering.
7. UI language Dutch with card language French produces `BLOC`, `ESSAI n`,
   `SCORE TOTAL` in the table, with the interface still Dutch.
8. Omitting `variant`, `rowHeight`, `rowScoreColumn` and `totalsRow` renders the ABYC
   default without error.
9. No reference to attempt columns or attempt counts remains in the card renderer or
   the validation engine.

---

## 9. Adjacent items from the same discussion

Small, independent of the refactor, and worth doing while this area is open. Each is a
few lines, not a subsystem.

### 9.1 Finalist selection

Printing a finals card is a rerun with new data, not a new feature — no round object is
needed. The one manual step worth removing: the results export carries the `Ranking`
column the parser currently discards. Add "take the top N per category by ranking" as a
filter on the loaded participant list, so a finalist list does not have to be hand-built
in Excel at 21:00.

Keep `Ranking` ignored everywhere else.

### 9.2 Round-scoped persistence

`localStorage` is keyed by `competitionId`, so a finals rerun overwrites the
qualification state. Use a distinct id per round — `abyc2026-m4-final`. This is a naming
convention documented in the UI help text, not code.

Note that the QR payload changes with it, which is the desired behaviour: a finals card
should not scan as a qualification card.

### 9.3 Single-card reprint

A climber loses their card mid-competition and the desk needs card 47, not all 77. Add a
start-number field on the print step that renders exactly one card.

Independent of rounds and of this refactor, but it is the operational gap most likely to
be hit at an actual competition, and a rerun workflow that has already overwritten its
state cannot serve it.
