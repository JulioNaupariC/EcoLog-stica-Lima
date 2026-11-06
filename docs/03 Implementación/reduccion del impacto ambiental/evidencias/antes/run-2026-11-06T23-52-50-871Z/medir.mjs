// Execute from repository root. Dependencies live outside the application.
import assert from 'node:assert/strict';
import { request } from 'node:http';
import { mkdir, writeFile, copyFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
const modules = resolve(process.env.ECL108_MODULES || '.tmp-ecl108/node_modules');
const { default: puppeteer } = await import(pathToFileURL(resolve(modules, 'puppeteer-core/lib/esm/puppeteer/puppeteer-core.js')));
const { default: lighthouse, desktopConfig, generateReport } = await import(pathToFileURL(resolve(modules, 'lighthouse/core/index.js')));
process.loadEnvFile('.env');
const BASE = 'e09dcd80e32431018d4020bb02c89ffae7505705';
assert.equal(execFileSync('git', ['diff', BASE, '--', 'backend', 'frontend', 'compose.yaml'], {encoding:'utf8'}), '', 'Application must equal baseline');
const stamp = new Date().toISOString().replaceAll(/[:.]/g, '-');
const output = resolve(`docs/03 Implementación/reduccion del impacto ambiental/evidencias/antes/run-${stamp}`);
await mkdir(output); // Never overwrite an evidence run.
await copyFile(fileURLToPath(import.meta.url), resolve(output, 'medir.mjs'));
const secretValues = Object.entries(process.env).filter(([k])=>/PASSWORD|DATABASE_URL/.test(k)).map(([,v])=>v);
const safeWrite = async (name, value) => {
  const data = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  for (const secret of secretValues) assert(!secret || !data.includes(secret), 'Secret detected in artifact');
  await writeFile(resolve(output, name), data, {flag:'wx'});
};
const sleep = ms => new Promise(r=>setTimeout(r,ms));
const metadata = {ticket:'ECL-108', baseline:BASE, documentationHead:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(), startedAt:new Date().toISOString(), timezone:'America/Lima', composeProject:'ecologistica-lima-ecl108', frontend:'Vite development', lighthouse:'12.8.2', api:[], pages:[], errors:[]};
console.log('OUTPUT', output);
function http(path, options = {}) {
  return new Promise((accept,reject)=>{
    const started = performance.now();
    const req = request(`http://127.0.0.1:8000${path}`, {method:options.method || 'GET', headers:{'Accept-Encoding':'identity', ...options.headers}}, res=>{
      const chunks=[];
      res.on('data', c=>chunks.push(c));
      res.on('end',()=>accept({status:res.statusCode, ms:performance.now()-started, body:Buffer.concat(chunks), headers:res.headers}));
    });
    req.on('error', reject);
    req.setTimeout(15000,()=>req.destroy(new Error('API timeout')));
    req.end(options.body);
  });
}
let cookie;
let browser;
try {
  if (!process.env.ECL108_SKIP_API) {
  const login = await http('/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'operador.demo@ecologistica.example',password:process.env.SEED_DEMO_PASSWORD_OPERADOR})});
  assert.equal(login.status,200,'API login failed');
  assert.equal(JSON.parse(login.body).rol,'OPERADOR');
  cookie = login.headers['set-cookie'][0].split(';')[0];
  secretValues.push(cookie, cookie.split('=')[1]);
  for (const [name,path] of [['vehiculos','/vehiculos'],['conductores','/conductores?page=1'],['incidencias','/incidencias?page=1']]) {
    const samples=[];
    for(let i=1;i<=20;i++) {
      const r = await http(path,{headers:{Cookie:cookie}});
      samples.push({sample:i,status:r.status,durationMs:r.ms,bodyBytes:r.body.length,contentEncoding:r.headers['content-encoding'] || 'identity',at:new Date().toISOString()});
    }
    await safeWrite(`api-${name}.csv`, 'sample,status,duration_ms,body_bytes,content_encoding,at_utc\n'+samples.map(s=>[s.sample,s.status,s.durationMs,s.bodyBytes,s.contentEncoding,s.at].join(',')).join('\n')+'\n');
    assert(samples.every(s=>s.status===200),`${name}: non-200 response`);
    metadata.api.push({endpoint:path,count:20,meanMs:samples.reduce((a,s)=>a+s.durationMs,0)/20,meanBytes:samples.reduce((a,s)=>a+s.bodyBytes,0)/20,minBytes:Math.min(...samples.map(s=>s.bodyBytes)),maxBytes:Math.max(...samples.map(s=>s.bodyBytes))});
    console.log('API',name,20,'OK');
  }
  await http('/logout',{method:'POST',headers:{Cookie:cookie}});
  cookie = undefined;
  }
  browser = await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe', headless:false, args:['--disable-extensions','--auto-open-devtools-for-tabs','--window-size=1500,1100']});
  metadata.chrome = await browser.version();
  const definitions = [
    {name:'login',path:'/login',role:null},
    {name:'inicio-operador',path:'/',role:'OPERADOR'},
    {name:'vehiculos-operador',path:'/vehiculos',role:'OPERADOR'},
    {name:'itinerario-conductor',path:'/conductor/itinerario',role:'CONDUCTOR'},
  ];
  for(const definition of definitions.filter(d=>!process.env.ECL108_PAGES || process.env.ECL108_PAGES.split(',').includes(d.name))) {
    const context = await browser.createBrowserContext();
    const page = await context.newPage();
    await page.setViewport({width:1350,height:940,deviceScaleFactor:1});
    const record={...definition, rounds:[], attemptedAt:new Date().toISOString()};
    metadata.pages.push(record);
    try {
      await page.goto('http://127.0.0.1:5173/login',{waitUntil:'networkidle0'});
      if(definition.role) {
        await page.locator('#login-email').fill(`${definition.role.toLowerCase()}.demo@ecologistica.example`);
        await page.locator('input[type="password"]').fill(process.env[`SEED_DEMO_PASSWORD_${definition.role}`]);
        await page.locator('button[type="submit"]').click();
        await page.waitForFunction(()=>location.pathname==='/',{timeout:15000});
        if(definition.path!=='/') {
          await page.evaluate(path=>document.querySelector(`main a[href="${path}"]`).click(),definition.path);
          await page.waitForFunction(path=>location.pathname===path,{},definition.path);
          await sleep(1000);
        }
        await page.screenshot({path:resolve(output,`${definition.name}-antes-recarga.png`)});
      }
      await sleep(1000);
      const target=browser.targets().filter(t=>t.url().startsWith('devtools:')).at(-1);
      assert(target,'DevTools target unavailable');
      const devtools=await target.asPage();
      await devtools.evaluate(async()=>{
        const UI=await import('./ui/legacy/legacy.js');
        await UI.InspectorView.InspectorView.instance().showPanel('network');
        const Common=await import('./core/common/common.js');
        Common.Settings.Settings.instance().moduleSetting('cache-disabled').set(true);
        const UI2=await import('./ui/legacy/legacy.js');
        UI2.DockController.DockController.instance().setDockSide('undocked');
      });
      await sleep(500);
      for(let round=1;round<=3;round++) {
        const prefix=`${definition.name}-${String(round).padStart(2,'0')}`;
        const client=await page.createCDPSession();
        await client.send('Network.enable');
        await client.send('Network.clearBrowserCache');
        await client.send('Network.setCacheDisabled',{cacheDisabled:true});
        await devtools.evaluate(async()=>{
          const Logs=await import('./models/logs/logs.js');
          Logs.NetworkLog.NetworkLog.instance().reset(true);
        });
        const start=performance.now();
        await page.reload({waitUntil:'networkidle0',timeout:30000});
        await sleep(1000);
        const network=await devtools.evaluate(async()=>{
          const Logs=await import('./models/logs/logs.js');
          const requests=Logs.NetworkLog.NetworkLog.instance().requests();
          const Common=await import('./core/common/common.js');
          return {requests:requests.length,transferredBytes:requests.reduce((s,r)=>s+r.transferSize,0),cacheDisabled:Common.Settings.Settings.instance().moduleSetting('cache-disabled').get(), failures:requests.filter(r=>r.failed).length};
        });
        network.observedMs=performance.now()-start;
        network.finalUrl=page.url();
        await safeWrite(`${prefix}.network.json`,network);
        await devtools.screenshot({path:resolve(output,`${prefix}-network.png`)});
        await page.screenshot({path:resolve(output,`${prefix}-pagina.png`)});
        if(new URL(page.url()).pathname!==definition.path) {
          record.status='NO_MEDIBLE';
          record.reason=`Tras recarga completa, ${definition.path} redirige a ${new URL(page.url()).pathname}. Identidad de Operador solo en memoria; no se inyecta identidad ni se modifica código base.`;
          console.log('NO_MEDIBLE',definition.name,record.reason);
          break;
        }
        const result=await lighthouse(`http://127.0.0.1:5173${definition.path}`, {onlyCategories:['performance'],disableStorageReset:true,logLevel:'error'},desktopConfig,page);
        assert(result && !result.lhr.runtimeError, 'Lighthouse runtime error');
        assert.equal(new URL(result.lhr.finalDisplayedUrl || result.lhr.finalUrl).pathname,definition.path,'Lighthouse redirected');
        await safeWrite(`${prefix}.lighthouse.json`,result.lhr);
        await writeFile(resolve('.tmp-ecl108',`${prefix}.html`),generateReport(result.lhr,'html'));
        const audits=result.lhr.audits;
        const sample={round,at:result.lhr.fetchTime,performance:result.lhr.categories.performance.score*100,fcpMs:audits['first-contentful-paint'].numericValue,lcpMs:audits['largest-contentful-paint'].numericValue,tbtMs:audits['total-blocking-time'].numericValue,cls:audits['cumulative-layout-shift'].numericValue,transferredBytes:network.transferredBytes,requests:network.requests,networkObservedMs:network.observedMs};
        record.rounds.push(sample);
        record.settings=result.lhr.configSettings;
        console.log('LIGHTHOUSE',definition.name,round,JSON.stringify(sample));
        await client.detach();
      }
      if(record.rounds.length===3) record.status='MEDIDO';
    } catch(error) {record.status='ERROR';record.reason=error.message;console.log('PAGE_ERROR',definition.name,error.message);}
    finally {await context.close(); await safeWrite(`${definition.name}.resultado.json`,record);}
  }
} catch(error) { metadata.errors.push(error.message); console.log('ERROR',error.message);process.exitCode=1; }
finally {
  if(cookie) await http('/logout',{method:'POST',headers:{Cookie:cookie}}).catch(()=>{});
  if(browser) await browser.close();
  metadata.finishedAt=new Date().toISOString();
  await safeWrite('resultados.json',metadata);
}
