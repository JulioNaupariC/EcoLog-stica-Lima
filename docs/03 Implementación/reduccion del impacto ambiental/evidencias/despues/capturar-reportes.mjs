import { readdir, readFile, writeFile, access } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const modules=resolve(process.env.ECL115_MODULES || '.tmp-ecl115/node_modules');
const {default:puppeteer}=await import(pathToFileURL(resolve(modules,'puppeteer-core/lib/esm/puppeteer/puppeteer-core.js')));
const {generateReport}=await import(pathToFileURL(resolve(modules,'lighthouse/core/index.js')));
const directory=resolve(process.argv[2]);
const browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-extensions']});
try {
  const page=await browser.newPage();
  await page.setViewport({width:1350,height:1100,deviceScaleFactor:1});
  await page.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'reduce'}]);
  for(const name of (await readdir(directory)).filter(n=>n.endsWith('.lighthouse.json'))) {
    const result=JSON.parse(await readFile(resolve(directory,name),'utf8'));
    const temporary=resolve('.tmp-ecl115',`${name}.html`);
    await writeFile(temporary,generateReport(result,'html'));
    await page.goto(pathToFileURL(temporary).href,{waitUntil:'networkidle0'});
    await new Promise(r=>setTimeout(r,2000));
    const destination=resolve(directory,name.replace('.lighthouse.json','-lighthouse-reporte.png'));
    try {await access(destination); throw new Error('Existing screenshot: use a new run directory');}
    catch(error) {if(error.code!=='ENOENT') throw error;}
    await page.screenshot({path:destination});
    console.log('CAPTURA',name);
  }
} finally {await browser.close();}
