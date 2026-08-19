# Internationalisation — Feature Spec

Addendum to `scorecard-generator-spec.md`. Adds Dutch, French and English support.
Dutch remains the default.

---

## 0. Where the strings live

Constraint C1 in the base spec stands unchanged: **one file, no build step, no
dependencies.** `fetch()` of a sibling `.json` file fails under `file://` in Chrome, so
runtime loading of separate locale files is not an option, and a build step is not
wanted. The translations therefore live inside the HTML file, in one clearly delimited
block.

**Format: a JSON script block, not a JS object literal.**

```html
<head>
  <meta charset="utf-8">

  <!-- ============================================================
       LOCALES — everything translatable lives here and nowhere else.
       Valid JSON. Do not put logic, comments or trailing commas in it.
       Adding a language: copy the "nl" block, translate the values,
       leave every key exactly as it is.
       ============================================================ -->
  <script type="application/json" id="locales">
  {
    "nl": { "card.label.name": "NAAM", ... },
    "fr": { "card.label.name": "NOM",  ... },
    "en": { "card.label.name": "NAME", ... }
  }
  </script>
  <!-- ===================== END LOCALES ========================== -->
```

Why this rather than a `const LOCALES = {…}` in the main script:

- It is real JSON, so a translator cannot break the app with a trailing comma without it
  failing loudly and immediately at `JSON.parse`.
- The browser does not execute it, so a malformed block cannot corrupt program state.
- It is trivially extractable by an external checking script (§6) with no JS parser.

**Placement matters.** The block goes immediately after `<meta charset>`, at the very
top of the file — not at the bottom, and not inside the main script. A translator
should be editing line 12, not hunting through three thousand lines. Load it with:

```js
const LOCALES = JSON.parse(document.getElementById('locales').textContent);
```

Accepted trade-off: translators edit inside the HTML file, and two people translating
different languages simultaneously will produce merge conflicts in one file. Given the
maintainer count, portability wins.

Size is a non-issue — three languages at a few hundred keys is well under 100 KB.

---

## 1. Scope

### In scope

- All UI chrome: labels, buttons, section headings, help text
- All validation messages, errors and warnings
- All card labels
- The control sheet
- Number and date formatting
- Print/PDF document title

### Explicitly NOT translated

| Item | Why |
|---|---|
| **Category strings** (`u15 (meisjes)`) | These are data from the platform, not UI. They must round-trip byte-identical or the mapping between participant file and boulder mapping breaks. Never translate, normalise, case-fold or transliterate them. |
| **Competition title and subtitle** | User-entered proper nouns. `ANTWERP BOULDER YOUTH CUP 2026` stays as typed in every language. |
| **Participant names** | Obviously. |
| **`Z` and `T` column markers** | Zone and Top are used untranslated across all three languages in practice. Keep as-is. |
| **QR payload** | Machine-readable, locale-independent. |

---

## 2. Two independent language settings

| Setting | Controls | Default |
|---|---|---|
| `uiLanguage` | Interface, validation messages, control sheet | `nl` |
| `cardLanguage` | Printed card labels only | follows `uiLanguage` until explicitly changed |

They must be separable. A Flemish organiser running an event with francophone
participants needs a Dutch interface and French cards. The control sheet follows
`uiLanguage` — it is an organiser document, not an athlete document.

`uiLanguage` persists to `localStorage`. `cardLanguage` persists with the competition
settings, since it belongs to the event.

On first load with no stored preference, use `nl`. Do **not** auto-detect from
`navigator.language` — a Flemish organiser on an English-locale Windows install should
still get Dutch.

---

## 3. Key structure

Dot-namespaced, hierarchical, grouped by surface:

```
ui.nav.settings
ui.participants.loadButton
ui.participants.rowsLoaded
ui.boulders.tab.paste
ui.print.controlSheetToggle

card.label.name
card.label.startNumber
card.label.category
card.header.boulder
card.header.attempt
card.header.score
card.footer.total

control.title
control.participantsPerCategory
control.generatedAt

validation.error.duplicateStartNumber
validation.error.categoryMissingInMapping
validation.warning.differingBoulderCounts
```

Rules:

- **Never concatenate sentence fragments.** Word order differs between the three
  languages; a string assembled from parts will be wrong in at least one of them. One
  key per complete sentence.
- **Interpolation with named placeholders**, not positional: `{category}`, `{count}`,
  `{number}`. Named placeholders let a translator reorder them.
- Placeholders must be escaped as text when injected into the DOM — never via
  `innerHTML`.

Example:

```json
"validation.error.duplicateStartNumber":
  "Startnummer {number} komt meer dan één keer voor (rijen {rows})."
```

---

## 4. Pluralisation and formatting

- Use `Intl.PluralRules` with the active locale. Do not hand-roll `count === 1 ? … : …`.
  All three languages have two forms, but French treats zero as singular where Dutch and
  English do not — this is exactly the kind of thing that gets it wrong.
- Plural keys use a suffix: `ui.participants.rowsLoaded.one`,
  `ui.participants.rowsLoaded.other`.
- Numbers via `Intl.NumberFormat`, dates via `Intl.DateTimeFormat`.
- Locale tags for formatting are region-specific even though string selection is not:

| String selection | Formatting locale |
|---|---|
| `nl` | `nl-BE` |
| `fr` | `fr-BE` |
| `en` | `en-GB` |

Note the decimal separator differs — a comma in `nl-BE` and `fr-BE`, a point in
`en-GB`. This is invisible today but becomes load-bearing if the tool ever prints
IFSC-style scores with 0.1 deductions.

---

## 5. Lookup and fallback

```
t(key, params) →
  1. locales[uiLanguage][key]
  2. locales['nl'][key]        ← fallback language
  3. the key itself, wrapped:  ⟦ui.foo.bar⟧
```

Never render `undefined`, `null` or an empty string. Step 3 makes a missing string
visibly wrong during testing instead of producing a blank label on a printed card.

---

## 6. Validation without a build step

Dropping the build step removes the gate that would have stopped a broken translation
from shipping. That gate has to be replaced, or the first missing French key will be
found by a francophone organiser at a competition. Two mechanisms, both required.

### 6.1 `check_locales.py` — a test, not a build step

A standalone stdlib-only script that reads `scorecard.html`, extracts the block between
the two sentinel comments, parses it, and exits non-zero on:

1. **Key set mismatch** between any two languages — report missing keys per language.
2. **Placeholder mismatch** — a key whose translations do not use the same set of
   `{placeholders}`.
3. **Missing plural forms** for any key declared as plural.
4. **Character budget exceeded** for any card label key (§7).
5. **Invalid JSON**, or non-UTF-8 bytes anywhere in the file.

It never writes to `scorecard.html`. It only reads and reports, so it does not
compromise the single-file property or introduce a build artifact. `--report` prints
coverage per language.

Run it before distributing a new version. Put that in the README as a release step.

### 6.2 In-app diagnostics panel

Because a script only helps if someone remembers to run it, the app itself carries the
same checks: a **Diagnostics** section, collapsed by default, showing translation
coverage per language and listing any problem from the list above.

If any check fails, show a persistent banner in the UI — not a console warning. Console
warnings are invisible to the person who actually needs to see them.

---

## 7. The layout risk: text expansion

**This is the requirement most likely to be got wrong.** French runs roughly 15–25%
longer than Dutch or English for equivalent UI text, and the card is a fixed-width A5
table with fixed column widths. A French card will overflow silently — the text wraps,
the row grows, and 16 boulders no longer fit.

Requirements:

- Every card label key carries a **maximum character budget**, declared once in a
  `"_budgets"` object inside the locale block. `check_locales.py` and the diagnostics
  panel both fail on any translation that exceeds it. Budgets are derived from the
  column widths in the base spec §6.2.
- The layout must be tested against the **longest** locale, not the default one. Add a
  dev-only "longest string" pseudo-locale that renders the maximum-length translation of
  every key, and verify a 16-boulder card still fits at 8mm rows.
- Card labels that cannot fit in all three languages get a per-language abbreviation
  key rather than a wrapped label. Abbreviating is correct here; wrapping is not.

---

## 8. Starter translations for the card

These are the actual terms used in French climbing, not literal translations. **Have a
francophone competition organiser review them** — a general translator will produce
`problème` for boulder and `numéro de départ` for the bib number, both of which are
wrong in context and will mark the tool as an outsider's product.

| Key | NL (default) | FR | EN |
|---|---|---|---|
| `card.label.name` | NAAM | NOM | NAME |
| `card.label.startNumber` | STARTNUMMER | DOSSARD | START NUMBER |
| `card.label.category` | CATEGORIE | CATÉGORIE | CATEGORY |
| `card.header.boulder` | BOULDER | BLOC | BOULDER |
| `card.header.attempt` | POGING | ESSAI | ATTEMPT |
| `card.header.score` | SCORE | SCORE | SCORE |
| `card.footer.total` | TOTALE SCORE | SCORE TOTAL | TOTAL SCORE |
| `card.marker.zone` | Z | Z | Z |
| `card.marker.top` | T | T | T |

Notes:

- `BLOC` is the standard French term for a boulder problem. `PROBLÈME` is a
  mistranslation in this context.
- `DOSSARD` is the standard term for a competitor's number and is conveniently shorter
  than the Dutch. `NUMÉRO DE DÉPART` is understandable but reads as a translation.
- `CATÉGORIE` carries an accent — see §9.

---

## 9. Encoding

- `<meta charset="utf-8">` as the first element in `<head>`. Under `file://`, Chrome
  will otherwise guess the encoding and mangle accented characters.
- Locale files written and read as UTF-8 without BOM. `build.py` must reject a BOM.
- Verify `CATÉGORIE`, `ESSAI`, `één` render correctly from a USB stick with the browser
  offline — the combination of `file://`, UTF-8 and accents is where this breaks, and it
  will not show up when testing over `http://localhost`.

---

## 10. UI

- Language selector in the top-right of the app, showing `NL / FR / EN`. Not a flag —
  flags map to countries, not languages, and both Dutch and French are Belgian.
- Card language selector lives in the competition settings section, defaulting to
  "same as interface" with an explicit override.
- Switching `uiLanguage` re-renders immediately without losing loaded participant data
  or the boulder mapping.

---

## 11. Acceptance criteria

1. `scorecard.html` is a single file containing all three locales, with no external
   references and no build artifact.
2. Opening it from a USB stick with networking disabled renders correctly in all three
   languages, accents included.
3. Deleting one French key makes `check_locales.py` exit non-zero naming the key, and
   raises the diagnostics banner in the app.
4. Changing `{category}` to `{cat}` in one translation is caught by both.
5. Setting UI to Dutch and card language to French produces a Dutch interface and cards
   labelled `NOM`, `DOSSARD`, `CATÉGORIE`, `BLOC`, `ESSAI`.
6. A 16-boulder card rendered in the longest-string pseudo-locale fits on one A5 card at
   a minimum 8mm row height, with no wrapped labels.
7. Category strings from the participant CSV appear byte-identical on the card in all
   three languages.
8. A missing key renders as `⟦key.name⟧`, never as a blank.
9. Switching language does not clear loaded data.

---

## 12. Build order

1. Locale block, `t()` function, and the fallback chain
2. Extract every existing hardcoded Dutch string into the `nl` block — mechanical, do it
   in one pass, no behaviour change
3. `check_locales.py` and the diagnostics panel
4. Language selector and re-render
5. `en` block
6. Character budgets and the longest-string pseudo-locale
7. `fr` block
8. Separate card language setting

Step 2 is the one that must not be done incrementally. A half-extracted codebase where
some strings are keyed and some are inline is worse than either end state, and the
inline ones will be missed for months.
