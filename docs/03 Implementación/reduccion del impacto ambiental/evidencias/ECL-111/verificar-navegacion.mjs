import assert from 'node:assert/strict';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(resolve('.tmp-ecl108/node_modules/playwright-core/index.mjs')));
process.loadEnvFile('.env');
const output=resolve(process.env.ECL111_NAV_OUTPUT || 'docs/03 Implementación/reduccion del impacto ambiental/evidencias/ECL-111/navegacion');
await mkdir(output);
const base='http://127.0.0.1:5174';
const results={at:new Date().toISOString(),timezone:'America/Lima',api:'http://127.0.0.1:8001',base,checks:[],pageSizes:[],offlineUnvisited:false};
const roles=['ADMINISTRADOR','OPERADOR','CONDUCTOR','ANALISTA','AUDITOR'];
const routes=[
  ['/', 'Inicio',roles],
  ['/vehiculos','Vehículos',['ADMINISTRADOR','OPERADOR','AUDITOR']],
  ['/conductores','Conductores',['ADMINISTRADOR','OPERADOR']],
  ['/usuarios','Usuarios',['ADMINISTRADOR']],
  ['/operacion/incidencias','Incidencias pendientes',['ADMINISTRADOR','OPERADOR']],
  ['/pedidos/nuevo','Registrar pedido',['ADMINISTRADOR','OPERADOR']],
  ['/clientes/preferencias','Preferencias de entrega',['ADMINISTRADOR','OPERADOR']],
  ['/conductor/itinerario','Mi itinerario',['CONDUCTOR']],
  ['/conductor/incidencias/nueva','Reportar incidencia',['CONDUCTOR']],
  ['/cambiar-contrasena','Cambiar contraseña',roles],
  ['/ruta-inexistente','Página no encontrada',roles],
];
let phase='launch';
const browser=await chromium.launch({channel:'chrome',headless:true});
async function signIn(page,role) {
  await page.goto(base+'/login');
  await page.getByLabel('Correo electrónico',{exact:true}).fill(`${role.toLowerCase()}.demo@ecologistica.example`);
  await page.getByLabel('Contraseña',{exact:true}).fill(process.env[`SEED_DEMO_PASSWORD_${role}`]);
  await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();
  await page.getByRole('heading',{name:'Inicio',exact:true}).waitFor();
}
try {
  for(const role of roles) {
    const context=await browser.newContext({viewport:{width:1350,height:940}});
    const page=await context.newPage();
    page.on('request',request=>{
      const url=new URL(request.url());
      if(url.port==='8001'&&['/vehiculos','/conductores','/usuarios','/incidencias'].includes(url.pathname)&&url.searchParams.has('page_size')) {
        assert.equal(url.searchParams.get('page_size'),'12');
        results.pageSizes.push({role,path:url.pathname,page:url.searchParams.get('page'),pageSize:12});
      }
    });
    try {
      phase=`login ${role}`;
      await signIn(page,role);
      for(const [path,heading,allowed] of routes) {
        phase=`${role} ${path}`;
        const expected=allowed.includes(role)?heading:'Acceso denegado';
        await page.evaluate(path=>{history.pushState({},'',path);dispatchEvent(new PopStateEvent('popstate'));},path);
        await page.getByRole('heading',{name:expected,exact:true}).waitFor();
        await page.waitForFunction(expected=>document.title===`${expected} — EcoLogística Lima`,expected);
        results.checks.push({role,path,expected,passed:true});
      }
      console.log('NAVEGACION',role,'11/11');
    } finally {
      await page.evaluate(()=>fetch('http://127.0.0.1:8001/logout',{method:'POST',credentials:'include'})).catch(()=>{});
      await context.close();
    }
  }
  phase='offline unvisited incident chunk';
  const context=await browser.newContext();
  const page=await context.newPage();
  await signIn(page,'CONDUCTOR');
  await page.getByRole('link',{name:'Mi itinerario',exact:true}).click();
  await page.getByRole('heading',{name:'Parada 1',exact:true}).waitFor();
  await page.evaluate(async()=>{
    await navigator.serviceWorker.ready;
    if(!navigator.serviceWorker.controller) await new Promise(r=>navigator.serviceWorker.addEventListener('controllerchange',r,{once:true}));
  });
  const alreadyVisited=await page.evaluate(()=>performance.getEntriesByType('resource').some(r=>r.name.includes('IncidentCreatePage-')));
  assert.equal(alreadyVisited,false,'Incident route must not have been loaded by the page');
  await context.setOffline(true);
  await page.getByRole('link',{name:'Reportar incidencia',exact:true}).click();
  await page.getByRole('heading',{name:'Reportar incidencia',exact:true}).waitFor();
  await page.reload();
  await page.getByRole('heading',{name:'Reportar incidencia',exact:true}).waitFor();
  await page.screenshot({path:resolve(output,'chunk-no-visitado-offline.png')});
  results.offlineUnvisited=true;
  await context.setOffline(false);
  await page.evaluate(()=>fetch('http://127.0.0.1:8001/logout',{method:'POST',credentials:'include'}));
  await context.close();
  results.passed=results.checks.length===55&&results.offlineUnvisited;
  results.shellVersion=JSON.parse(await readFile('frontend/dist/offline-shell.json','utf8')).version;
} catch(error) {results.passed=false;results.failure={phase,errorType:error.name};console.error('FALLO',phase,error.name);process.exitCode=1;}
finally {await browser.close();await writeFile(resolve(output,'results.json'),JSON.stringify(results,null,2),{flag:'wx'});}
