// Haalt de deelnemerslijst van een etto-wedstrijd op als CSV, klaar voor
// import in de scorecard-generator (kolommen Category, Starting number, Name).
//
// Werkwijze: de "EXPORT"-pagina van etto (jury/export) roept bij het laden
// een server action aan die de URL van een gekoppeld Google Spreadsheet
// teruggeeft. Dat sheet staat publiek open voor CSV-export (geen Google-
// login nodig) — geverifieerd met curl. Wij laden dus alleen de export-
// pagina met een ingelogde sessie om die sheet-URL te onderscheppen, en
// downloaden de CSV daarna rechtstreeks.
//
// ponytail: leest de sheet-URL uit het netwerkverkeer i.p.v. de interne
// Next.js server-action-aanroep na te bouwen (fragiel: action-ID en
// argumentvorm kunnen bij een deploy wijzigen; de pagina zelf is stabieler).
import { firefox } from 'playwright';
import { writeFile } from 'node:fs/promises';

const slug = process.argv[2];
const out = process.argv[3] || `${slug}-participants.csv`;
if (!slug){
  console.error('Gebruik: node fetch_participants.mjs <competition-slug> [output.csv]');
  process.exit(1);
}

const STATE_FILE = new URL('./etto_state.json', import.meta.url).pathname;
const exportUrl = `https://www.etto-climbing.com/app/events/competitions/${slug}/jury/export`;

const browser = await firefox.launch({ headless: true });
const context = await browser.newContext({ storageState: STATE_FILE });
const page = await context.newPage();

const sheetUrl = await new Promise((resolve, reject) => {
  page.on('response', async r => {
    if (r.request().method() !== 'POST' || !r.url().startsWith(exportUrl)) return;
    const body = await r.text().catch(() => '');
    const m = body.match(/https:\/\/docs\.google\.com\/spreadsheets\/d\/([a-zA-Z0-9_-]+)/);
    if (m) resolve(m[0]);
  });
  page.goto(exportUrl, { waitUntil: 'load', timeout: 20000 }).catch(reject);
  setTimeout(() => reject(new Error('Geen spreadsheet-URL gevonden binnen 15s — sessie verlopen of wedstrijd bestaat niet?')), 15000);
});
await browser.close();

const sheetId = sheetUrl.match(/\/d\/([a-zA-Z0-9_-]+)/)[1];
const csvUrl = `https://docs.google.com/spreadsheets/d/${sheetId}/export?format=csv&gid=0`;
const res = await fetch(csvUrl);
if (!res.ok) throw new Error(`CSV-export mislukt: ${res.status} ${res.statusText}`);
const csv = await res.text();
await writeFile(out, csv, 'utf8');
console.log(`Opgeslagen: ${out} (${csv.split('\n').length - 1} deelnemers)`);
