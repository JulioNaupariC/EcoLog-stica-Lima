// Screenshot the report generated from measured JSON; requires Playwright.
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const [directory, playwrightModule] = process.argv.slice(2);
if (!directory || !playwrightModule) {
  throw new Error('Usage: node loadtest/capture.mjs REPORT_DIRECTORY PLAYWRIGHT_INDEX_MJS');
}
const { chromium } = await import(pathToFileURL(resolve(playwrightModule)).href);
const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1400 }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(join(resolve(directory), 'reporte.html')).href);
  await page.screenshot({ path: join(resolve(directory), '01-resultados-disponibilidad.png') });
  await page.getByRole('heading', { name: 'Concurrencia del servidor', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: join(resolve(directory), '02-concurrencia.png') });
  await page.screenshot({ path: join(resolve(directory), '03-reporte-completo.png'), fullPage: true });
  console.log('Capturas creadas desde reporte.html');
} finally {
  await browser.close();
}
