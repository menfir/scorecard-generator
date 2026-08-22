# Timed Format (`attempts-to`) — Feature Spec

Addendum to `scorecard-generator-spec.md` and `score-table-refactor-spec.md`. Implements
the second `capture` mode through the existing seam. This is the test of whether the
refactor bought anything.

---

## 1. The format

Each climber gets a fixed time per boulder with **unlimited attempts** inside that
window. The judge records, per boulder, the attempt number on which zone was reached and
the attempt number on which top was reached.

Ranking is a four-level hierarchy, applied in order:

1. number of tops (descending)
2. number of zones (descending)
3. attempts to top, summed (ascending)
4. attempts to zone, summed (ascending)

Typically 4 boulders. The tool already handles other counts; see §5 for the limit.

**The tool does not compute any of this.** Ranking is the platform's job (base spec §9).
The card exists to capture the four numbers correctly.

---

## 2. What this format needs that ABYC does not

| Need | Consequence |
|---|---|
| Unlimited attempts | No attempt columns. `attemptColumns` must be rejected, not defaulted. |
| Judge tallies attempts by hand | A wide working area per row, not tick cells. |
| Two derived numbers per boulder | Separate numeric cells for zone-attempts and top-attempts. |
| Per-boulder result | A result cell per row. |
| Four-part athlete summary | The totals row is a different shape from ABYC's two cells. |
| Judge writes rather than ticks | A higher minimum row height. |

The last two are the ones that will surface design problems. See §6.

---

## 3. Row layout

Columns, at A5 landscape with 8mm padding (194mm usable):

| Column | Width | Content |
|---|---|---|
| `BOULDER` | 18mm | Boulder number, pre-filled, large |
| `POGINGEN` | 80mm | Open tally area, light guide rules every 5 strokes |
| `ZONE` | 26mm | Achieved tick box (10mm) + attempts number box (16mm) |
| `TOP` | 26mm | Achieved tick box (10mm) + attempts number box (16mm) |
| `RESULTAAT` | 40mm | Per-boulder result, written by the judge |

**Tally area.** Judges count in strokes under time pressure. Print faint vertical guide
rules every five strokes so a count is read at a glance instead of recounted. Do not
pre-print numbered cells — numbering caps the attempt count, which is the exact failure
mode this format exists to avoid.

**Achieved tick plus number, not a number alone.** A blank number cell is ambiguous:
not achieved, or the judge forgot. The tick box removes the ambiguity at a cost of 10mm
per column. If width becomes a problem, drop the tick and adopt an explicit dash
convention printed in the footer — but decide, do not leave it implicit.

**Authority.** The tally is working area; the numeric cells are the record. Style them
accordingly — the tally area lighter, the number boxes boxed and heavier — so it is
obvious at the results desk which one is being transcribed.

---

## 4. Athlete summary

Below the table, a summary block with four labelled boxes, in ranking order:

```
TOPS | ZONES | POGINGEN TOP | POGINGEN ZONE
```

These are written by the judge or the desk, not computed. Sized for two digits each.

Optionally print the ranking rule as a single footer line — tops, then zones, then top
attempts, then zone attempts. This format's hierarchy is not obvious to an occasional
judge, and one line of text removes a class of transcription error. Base spec F5.

---

## 5. Seam parameters

```js
renderScoreTable({
  rows: boulders.map(n => ({ id: n, label: String(n) })),
  capture: 'attempts-to',
  zones: 1,
  rowScoreColumn: true,        // the RESULTAAT cell
  totalsRow: true,             // the four-part summary, see §6
  variant: 'standard',
  rowHeight: { min: 12, max: 20 },
  lang: settings.cardLanguage
});
```

`attemptColumns` is **not passed**. Passing it must throw — that guard already exists in
the seam (refactor spec §3, rule 4) and this is its first real use.

`rowHeight.min` is 12mm, not 8mm. The judge writes in these rows rather than ticking
them, and 8mm is not enough for a legible tally. This is why `rowHeight` is a parameter
rather than a constant.

**Boulder limit.** At a 12mm minimum against the ~96mm body budget, 8 boulders fit.
Above that the seam throws, and the validation engine (base spec §5) should warn first.
Set the warning threshold from the same constant, not a second hard-coded number.

---

## 6. The two things this format breaks

Expect both. They are the point of testing a second format.

### 6.1 `totalsRow` assumes the totals mirror the score columns

ABYC's footer is two cells under the `SCORE` column. This format's summary is four
aggregate fields that correspond to nothing in the table body.

**Do not add a `summary` parameter.** The summary shape is a property of the format, so
derive it inside the `attempts-to` branch and keep `totalsRow` a boolean. Adding a
parameter here would start the drift toward a config schema that the refactor spec
explicitly rejects.

If the summary block sits outside the table element rather than in `<tfoot>`, the
function returns both and the card assembles them — but keep it inside the returned
string, so the caller stays format-agnostic.

### 6.2 `rowScoreColumn` means something different here

In ABYC it is a Z/T pair mirroring the markers. Here it is one wide write-in cell. Same
boolean, different column arithmetic — which is fine, because the arithmetic is
branch-local. If you find yourself wanting to express *how many* score cells at the call
site, stop: that is the format leaking back out through the seam.

---

## 7. New translation keys

Added to the locale block (i18n spec §0). All three languages, character budgets from
the column widths in §3.

| Key | NL | FR | EN |
|---|---|---|---|
| `card.header.attempts` | POGINGEN | ESSAIS | ATTEMPTS |
| `card.header.zone` | ZONE | ZONE | ZONE |
| `card.header.top` | TOP | TOP | TOP |
| `card.header.result` | RESULTAAT | RÉSULTAT | RESULT |
| `card.summary.tops` | TOPS | TOPS | TOPS |
| `card.summary.zones` | ZONES | ZONES | ZONES |
| `card.summary.topAttempts` | POG. TOP | ESS. TOP | ATT. TOP |
| `card.summary.zoneAttempts` | POG. ZONE | ESS. ZONE | ATT. ZONE |
| `card.footer.rankingRule` | *(one line, see §4)* | | |

`POGINGEN TOP` does not fit a summary box at these widths in any language. Abbreviate
per i18n spec §7 — abbreviate, do not wrap.

`card.footer.rankingRule` is a full sentence per language. Never assemble it from
fragments (i18n spec §3).

---

## 8. Acceptance criteria

1. `capture: 'attempts-to'` renders a card with the five columns of §3.
2. Passing `attemptColumns` alongside it throws before any rendering.
3. Four boulders render at the 20mm row cap with no void at the bottom of the card.
4. Nine boulders throw at the seam; the validation engine warns before that point.
5. The summary block shows four labelled boxes in ranking order.
6. Card language French renders `ESSAIS`, `RÉSULTAT`, `ESS. TOP`, with the interface
   still in Dutch.
7. `check_locales.py` passes with the new keys in all three languages, none over budget.
8. Rendering an ABYC card in the same session is unchanged — no shared state, no
   regression.
9. Switching a competition between the two formats changes only the settings-layer
   parameter mapping; no call site outside it changes.

Criterion 9 is the real test. If adding this format required edits to the card renderer,
the print CSS structure, or the validation engine, the seam is in the wrong place and it
is cheaper to find that out now than at the third format.

---

## 9. Open question

**Is the per-boulder `RESULTAAT` cell actually used?** In some running of this format the
judge writes only the zone and top attempt numbers, and the per-boulder result is
derived at the desk. If nobody writes in it, drop the column and give the 40mm to the
tally area — that is the column most likely to run out of room in practice.

Worth confirming with a judge before printing a set.
