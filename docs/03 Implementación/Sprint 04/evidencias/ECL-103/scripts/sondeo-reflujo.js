const { chromium } = require('playwright'); const { login } = require('./lib');
const SPACING=`*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}p{margin-bottom:2em!important}`;
async function medir(p, nombre, out){
  const r={};
  const m = ()=>p.evaluate(()=>{window.__c=[];const ov=document.documentElement.scrollWidth-window.innerWidth;
    let clip=0; for(const e of document.querySelectorAll('main *')){const s=getComputedStyle(e); if((s.overflow==='hidden'||s.overflowX==='hidden'||s.overflowY==='hidden') && e.closest('.leaflet-container')===null && e.offsetParent && (e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1) && e.innerText && e.innerText.trim() && e.clientWidth>2 && e.clientHeight>2) {clip++; (window.__c=window.__c||[]).push(e.tagName+'.'+e.className+':'+e.innerText.slice(0,30));}}
    return {desborde_px:ov, recortes:clip, ej:(window.__c||[]).slice(0,3)};});
  const vp=p.viewportSize();
  await p.setViewportSize({width:320,height:800}); const tag=await p.addStyleTag({content:SPACING}); await p.waitForTimeout(400);
  r.espaciado_320=await m(); await tag.evaluate(t=>t.remove());
  await p.setViewportSize({width:1280,height:900}); await p.evaluate(()=>document.documentElement.style.fontSize='200%'); await p.waitForTimeout(400);
  r.fuente200_1280=await m(); await p.evaluate(()=>document.documentElement.style.fontSize='');
  await p.setViewportSize({width:900,height:360}); await p.waitForTimeout(400);
  r.horizontal_900x360=await m();
  await p.setViewportSize(vp); out[nombre]=r;
}
(async()=>{ const b=await chromium.launch(); const out={};
 const p=await b.newPage({viewport:{width:1366,height:900}});
 await login(p,'operador.demo@ecologistica.example',process.env.SEED_DEMO_PASSWORD_OPERADOR);
 await p.getByRole('link',{name:/rutas y alertas/i}).first().click(); await p.locator('#route-date').fill('2026-11-12'); await p.getByRole('button',{name:/actualizar optimizaciones/i}).click(); await p.getByRole('button',{name:/^Ruta /}).first().waitFor(); await p.waitForTimeout(800);
 await p.getByRole('button',{name:/^Ruta /}).first().click(); await p.waitForTimeout(800);
 await medir(p,'rutas-mapa',out);
 await p.getByRole('link',{name:'Inicio'}).first().click();
 await p.getByRole('link',{name:/indicadores de sostenibilidad/i}).first().click(); await p.getByText(/Rutas cerradas/).first().waitFor();
 await medir(p,'dashboard',out);
 await p.getByRole('link',{name:'Inicio'}).first().click();
 await p.getByRole('link',{name:/incidencias/i}).first().click(); await p.waitForTimeout(1200);
 await medir(p,'incidencias-operador',out);
 const c=await (await b.newContext({viewport:{width:390,height:844}})).newPage();
 await login(c,'conductor.demo@ecologistica.example',process.env.SEED_DEMO_PASSWORD_CONDUCTOR);
 await c.getByRole('link',{name:/itinerario/i}).first().click(); await c.waitForTimeout(1500);
 await medir(c,'itinerario-movil',out);
 console.log(JSON.stringify(out)); await b.close(); })();
