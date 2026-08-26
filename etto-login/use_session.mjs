// Voorbeeld: hergebruik de opgeslagen sessie zonder opnieuw in te loggen.
import { firefox } from 'playwright';

const STATE_FILE = new URL('./etto_state.json', import.meta.url).pathname;

const browser = await firefox.launch({ headless: true });
const context = await browser.newContext({ storageState: STATE_FILE });
const page = await context.newPage();
await page.goto('https://etto-climbing.com');
console.log(await page.title());
await browser.close();
