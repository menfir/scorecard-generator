# Score Card Generator

Print-ready score cards for indoor boulder competitions, from a participant export
and a boulder-per-category mapping. Dutch, French and English.

Replaces the manual Word template + mail merge + hand-written boulder numbers workflow.

## Why it is one HTML file

- **Runs offline.** Open `scorecard-generator.html` from a USB stick in a sports hall
  with bad wifi. No build step, no bundler, no CDN, no external fonts.
- **Nothing leaves the device.** Participant lists contain names of minors. All parsing
  and rendering is client-side; there is no server and no network call at runtime.
- **Prints via the browser.** `Ctrl+P` → Save as PDF. No PDF library.

Target browser is Chrome/Edge.

## Languages

Interface and cards are available in **NL / FR / EN**, and the two settings are
independent: a Dutch interface can print French cards for francophone participants.
The control sheet is an organiser document and follows the interface language.

- Interface language: the NL/FR/EN buttons top right. Persists per device.
- Card language: in the competition settings, defaults to "same as interface".
  Persists with the competition, since it belongs to the event.

Dutch is the default and the fallback. There is no auto-detection from the browser
locale — a Flemish organiser on an English Windows install still gets Dutch.

Category names, competition titles, participant names and the QR payload are never
translated. They come from the platform or from the user and must round-trip
byte-identically.

## Usage

1. Open `scorecard-generator.html` in Chrome.
2. Enter the competition settings (title, subtitle, competition ID, max attempts).
3. Load the participant CSV exported from the etto-climbing platform
   (`Category;Starting number;Ranking;Name`, semicolon-delimited, UTF-8).
4. Supply the boulder-per-category mapping — paste JSON, paste the platform's boulder
   table, or fill in the manual grid.
5. Read the validation report and fix anything it blocks on.
6. Print to PDF.

## GitHub Pages

The same local-only application can be published as a static GitHub Pages site.
The repository includes `.github/workflows/deploy-pages.yml`, which deploys the
static application files when `main` is pushed. `index.html` redirects the
project URL to the generator; samples and development helpers are not deployed.

One-time repository setup: in **Settings → Pages**, select **GitHub Actions** as
the publishing source. After the next push to `main` (or a manual run of the
workflow), GitHub will show the published URL; for this repository it will
normally be `https://menfir.github.io/scorecard-generator/`.

Publishing does not add a backend. CSV and JSON files selected by an organiser
are read and processed in that organiser's browser only; participant data is
not uploaded by this application. The settings and boulder mapping stay in that
browser's `localStorage`, and participants remain in memory for the tab session.
Do not add analytics, remote fonts, third-party scripts, or API calls if that
local-only property must be retained. As with any hosted site, GitHub Pages may
process visitor technical data such as IP addresses to operate the service.

Competition settings and the boulder mapping persist to `localStorage` per competition
ID, and can be exported to JSON to seed next season. Participant data is never
persisted — it lives in memory for the session only.

## Files

| File | What it is |
|---|---|
| `scorecard-generator.html` | The application. This is the whole thing. |
| `scan.html` | Score card scanner (in progress, see `scan-feature-spec.md`). Separate single file, vendors js-aruco2 (MIT). |
| `scan-feature-spec.md` | Spec for scannable cards and the scanner, in phases. |
| `scorecard-generator-spec.md` | Development spec: constraints, data formats, layout, validation rules. |
| `i18n-feature-spec.md` | Spec for the NL/FR/EN support. |
| `check_locales.py` | Stdlib-only checker for the translation block. Run before every release. |
| `sample-participants.csv` | Clearly fictitious participant list with awkward names, for testing the parser. |
| `boulders-per-category-sample` | Raw clipboard HTML from the platform's boulder table, for testing the paste parser. |

## Translating

All translatable text lives in one JSON block at the top of
`scorecard-generator.html`, between the `LOCALES` sentinel comments. To add a
language, copy the `nl` block, translate the values and leave every key untouched.

There is no build step, so the translations are checked two ways instead:

```
python3 check_locales.py --report     # release step: exits non-zero on any problem
```

It catches missing or unknown keys, placeholders that do not match Dutch, missing
plural forms, card labels over their character budget, invalid JSON and a stray BOM.
The app runs the same checks itself and raises a banner plus a "Translation
diagnostics" panel if anything is wrong, so a broken translation is visible to whoever
opens the file even if nobody ran the script.

Card labels have a character budget because the card is a fixed-width table — French
runs 15–25% longer than Dutch and would silently overflow. The diagnostics panel also
carries a "longest translation" pseudo-locale for eyeballing the worst case.

## Tests

```
python3 check_locales.py                      # translations
python3 check_locales.py scan.html            # scanner translations
open scorecard-generator.html?selftest        # 98 assertions, in the browser
```

The self-test covers the CSV parser, both paste parsers, validation, layout maths,
storage and the i18n acceptance criteria. It needs a real browser — it measures text
and builds actual print DOM.

## Status

Working. All three languages complete.

Known limit, unchanged by i18n: a card holds 10 boulders at the 8mm minimum row
height. Above that the app warns and the rows compress; it never silently truncates.
The i18n spec's acceptance criterion about a 16-boulder card is not reachable with the
base spec's 82.5mm card body in any language, Dutch included.

## License

MIT — see [LICENSE](LICENSE).
