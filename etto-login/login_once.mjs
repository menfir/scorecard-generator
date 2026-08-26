// ponytail: eenmalig handmatig inloggen, geen wachtwoord in code of chat.
// Playwright's firefox is al gedownload voor dit project (zie scorecard-generator repo).
import { firefox } from 'playwright';

const STATE_FILE = new URL('./etto_state.json', import.meta.url).pathname;

const browser = await firefox.launch({ headless: false });
const page = await browser.newPage();
await page.goto('https://etto-climbing.com');

console.log('Log handmatig in via de Sign in-knop. Druk hierna Enter in deze terminal...');
await new Promise(resolve => process.stdin.once('data', resolve));

await page.context().storageState({ path: STATE_FILE });
console.log('Sessie opgeslagen in', STATE_FILE);
await browser.close();
