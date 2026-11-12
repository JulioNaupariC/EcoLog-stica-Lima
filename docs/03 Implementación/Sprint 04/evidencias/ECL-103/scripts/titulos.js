const { chromium } = require('playwright'); const { login } = require('./lib');
(async()=>{ const b=await chromium.launch(); const out=[];
 const p=await b.newPage({viewport:{width:1366,height:900}});
 await login(p,'operador.demo@ecologistica.example',process.env.SEED_DEMO_PASSWORD_OPERADOR);
 const snap=async n=>out.push([n, await p.title(), await p.evaluate(()=>!!Array.from(document.querySelectorAll('a')).find(a=>/saltar/i.test(a.textContent))), await p.evaluate(()=>document.documentElement.lang)]);
 for (const l of [/rutas y alertas/i,/indicadores de sostenibilidad/i,/incidencias/i]) { await p.getByRole('link',{name:'Inicio'}).first().click().catch(()=>{}); await p.getByRole('link',{name:l}).first().click(); await p.waitForTimeout(900); await snap(String(l)); }
 const c=await (await b.newContext({viewport:{width:390,height:844}})).newPage();
 await login(c,'conductor.demo@ecologistica.example',process.env.SEED_DEMO_PASSWORD_CONDUCTOR);
 await c.getByRole('link',{name:/itinerario/i}).first().click(); await c.waitForTimeout(1200); out.push(['itinerario', await c.title()]);
 await c.getByRole('link',{name:/reportar incidencia/i}).first().click().catch(()=>{}); await c.waitForTimeout(1000); out.push(['incidencia', await c.title()]);
 console.log(JSON.stringify(out)); await b.close(); })();
