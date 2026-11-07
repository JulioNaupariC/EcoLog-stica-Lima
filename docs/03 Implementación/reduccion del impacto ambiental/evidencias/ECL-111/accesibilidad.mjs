import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const {default:puppeteer}=await import(pathToFileURL(resolve('.tmp-ecl108/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js')));
const {default:lighthouse,desktopConfig}=await import(pathToFileURL(resolve('.tmp-ecl108/node_modules/lighthouse/core/index.js')));
process.loadEnvFile('.env');
const output=resolve(process.env.ECL111_A11Y_OUTPUT || 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/ECL-111/accesibilidad');
await mkdir(output);
const results={at:new Date().toISOString(),baselineCommit:'e09dcd80e32431018d4020bb02c89ffae7505705',mode:'production preview for both phases; supplementary accessibility baseline, not historical performance',pages:[]};
const browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:false,args:['--disable-extensions']});
let phase='launch';
try {
  for(const [label,origin] of [['antes','http://127.0.0.1:5175'],['despues','http://127.0.0.1:5174']]) {
    for(const [name,path] of [['login','/login'],['conductor','/conductor/itinerario']]) {
      const context=await browser.createBrowserContext();
      const page=await context.newPage();
      const record={phase:label,page:path,scores:[]};
      results.pages.push(record);
      try {
        await page.goto(origin+'/login',{waitUntil:'networkidle0'});
        if(name==='conductor') {
          await page.locator('#login-email').fill('conductor.demo@ecologistica.example');
          await page.locator('input[type=password]').fill(process.env.SEED_DEMO_PASSWORD_CONDUCTOR);
          await page.locator('button[type=submit]').click();
          await page.waitForFunction(()=>document.querySelector('main h1')?.textContent==='Inicio');
          await page.goto(origin+path,{waitUntil:'networkidle0'});
        }
        const secrets=Object.entries(process.env).filter(([key])=>/PASSWORD|DATABASE_URL/.test(key)).map(([,value])=>value);
        secrets.push(...(await context.cookies()).map(c=>c.value));
        for(let round=1;round<=3;round++) {
          phase=`${label} ${name} ${round}`;
          const client=await page.createCDPSession();
          await client.send('Network.clearBrowserCache');
          await client.detach();
          const result=await lighthouse(origin+path,{onlyCategories:['accessibility'],disableStorageReset:true,logLevel:'error'},desktopConfig,page);
          assert(result&&!result.lhr.runtimeError,'Lighthouse runtime error');
          assert.equal(new URL(result.lhr.finalDisplayedUrl||result.lhr.finalUrl).pathname,path);
          const data=JSON.stringify(result.lhr,null,2);
          assert(secrets.every(secret=>!secret||!data.includes(secret)),'Secret in report');
          await writeFile(resolve(output,`${label}-${name}-${round}.json`),data,{flag:'wx'});
          record.scores.push(result.lhr.categories.accessibility.score*100);
          console.log('ACCESIBILIDAD',phase,record.scores.at(-1));
        }
      } finally {await context.close();}
    }
  }
  for(const path of ['/login','/conductor/itinerario']) {
    const before=results.pages.find(p=>p.phase==='antes'&&p.page===path).scores.sort((a,b)=>a-b)[1];
    const after=results.pages.find(p=>p.phase==='despues'&&p.page===path).scores.sort((a,b)=>a-b)[1];
    assert(after>=before,'Accessibility regression');
  }
  results.passed=true;
} catch(error) {results.passed=false;results.failure={phase,errorType:error.name};console.error('FALLO ACCESIBILIDAD',phase,error.name);process.exitCode=1;}
finally {await browser.close();await writeFile(resolve(output,'results.json'),JSON.stringify(results,null,2),{flag:'wx'});}
