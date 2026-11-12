const { chromium } = require('playwright'); const { BASE, API, login } = require('./lib'); const fs=require('fs');
const AXE = fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8');
async function run(p, name, out){ await p.addScriptTag({content: AXE});
  const r = await p.evaluate(async()=> await axe.run(document, {runOnly:{type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}}));
  out[name] = {violations: r.violations.map(v=>({id:v.id, impact:v.impact, tags:v.tags.filter(t=>/^wcag\d/.test(t)), nodes:v.nodes.length, help:v.help, sample:v.nodes.slice(0,2).map(n=>n.target.join(' '))})), passes:r.passes.length, incomplete:r.incomplete.map(v=>({id:v.id,nodes:v.nodes.length}))};
  console.log(name, 'violations', r.violations.length, r.violations.map(v=>v.id+'('+v.nodes.length+')').join(','), 'passes', r.passes.length, 'incomplete', r.incomplete.map(v=>v.id).join(',')); }
(async () => { const out={}; const b = await chromium.launch();
 for (const scheme of ['light','dark']) {
  const op = await b.newPage({viewport:{width:1366,height:900}, colorScheme: scheme});
  await op.goto(BASE+'/login'); await op.waitForTimeout(500); await run(op, `login-${scheme}`, out);
  await login(op,'operador.demo@ecologistica.example',process.env.SEED_DEMO_PASSWORD_OPERADOR);
  await op.getByRole('link',{name:/rutas y alertas/i}).first().click(); await op.locator('#route-date').fill('2026-11-12'); await op.getByRole('button',{name:/actualizar optimizaciones/i}).click(); await op.getByRole('button',{name:/^Ruta /}).first().waitFor(); await op.waitForTimeout(1500);
  await run(op, `rutas-mapa-${scheme}`, out);
  await op.getByRole('button',{name:/^Ruta DEMO-005/}).click(); await op.waitForTimeout(500);
  await op.getByRole('button',{name:'Registrar resultado de parada 1', exact:true}).click(); await op.waitForTimeout(400); await run(op, `rutas-registro-parada-${scheme}`, out);
  await op.getByRole('button',{name:'Cancelar registro de parada 1', exact:true}).click();
  await op.getByRole('link',{name:'Inicio'}).first().click();
  await op.getByRole('link',{name:/indicadores de sostenibilidad/i}).first().click(); await op.getByText(/Rutas cerradas/).first().waitFor(); await op.waitForTimeout(500); await run(op, `dashboard-${scheme}`, out);
  await op.getByRole('link',{name:'Inicio'}).first().click();
  await op.getByRole('link',{name:/incidencias pendientes/i}).first().click(); await op.waitForTimeout(1000); await run(op, `incidencias-operador-${scheme}`, out);
  const cctx = await b.newContext({viewport:{width:412,height:900}, colorScheme: scheme}); const cd = await cctx.newPage();
  await login(cd,'conductor.demo@ecologistica.example',process.env.SEED_DEMO_PASSWORD_CONDUCTOR);
  await cd.getByRole('link',{name:/abrir mi itinerario/i}).click(); await cd.getByText('Reportes de la parada 1').waitFor(); await run(cd, `itinerario-movil-${scheme}`, out);
  await cd.goBack(); await cd.getByRole('link',{name:/reportar incidencia/i}).first().click(); await cd.waitForTimeout(600); await run(cd, `incidencia-movil-${scheme}`, out);
  await cctx.close(); await op.close();
 }
 fs.writeFileSync('axe-resultados.json', JSON.stringify({axe:require('axe-core/package.json').version, fecha:new Date().toISOString(), resultados:out}, null, 2));
 await b.close(); })();
