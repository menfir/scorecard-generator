# Score Card Generator

Print-ready score cards for indoor boulder competitions, from a participant export
and a boulder-per-category mapping.

Replaces the manual Word template + mail merge + hand-written boulder numbers workflow.

## Why it is one HTML file

- **Runs offline.** Open `scorecard-generator.html` from a USB stick in a sports hall
  with bad wifi. No build step, no bundler, no CDN, no external fonts.
- **Nothing leaves the device.** Participant lists contain names of minors. All parsing
  and rendering is client-side; there is no server and no network call at runtime.
- **Prints via the browser.** `Ctrl+P` → Save as PDF. No PDF library.

Target browser is Chrome/Edge.

## Usage

1. Open `scorecard-generator.html` in Chrome.
2. Enter the competition settings (title, subtitle, competition ID, max attempts).
3. Load the participant CSV exported from the etto-climbing platform
   (`Category;Starting number;Ranking;Name`, semicolon-delimited, UTF-8).
4. Supply the boulder-per-category mapping — paste JSON, paste the platform's boulder
   table, or fill in the manual grid.
5. Read the validation report and fix anything it blocks on.
6. Print to PDF.

Competition settings and the boulder mapping persist to `localStorage` per competition
ID, and can be exported to JSON to seed next season. Participant data is never
persisted — it lives in memory for the session only.

## Files

| File | What it is |
|---|---|
| `scorecard-generator.html` | The application. This is the whole thing. |
| `scorecard-generator-spec.md` | Development spec: constraints, data formats, layout, validation rules. |
| `i18n-feature-spec.md` | Spec for NL/FR/EN support. Not implemented yet. |
| `sample-participants.csv` | Synthetic participant list with awkward names, for testing the parser. |
| `boulders-per-category-sample` | Raw clipboard HTML from the platform's boulder table, for testing the paste parser. |
| `Competition Results - ....ods` | Sample results export, participant names redacted. |

## Status

The generator works. Interface and cards are Dutch; the i18n spec is written but not
built yet.

## License

MIT — see [LICENSE](LICENSE).
