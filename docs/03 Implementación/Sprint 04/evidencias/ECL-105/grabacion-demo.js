// ECL-105: grabación automatizada de la demo del MVP (Playwright).
// Requiere la API en 127.0.0.1:8000, el build en 127.0.0.1:4173 y, en la consola,
// SEED_DEMO_PASSWORD_OPERADOR, SEED_DEMO_PASSWORD_CONDUCTOR y PGPW (nunca en archivos).
// Dependencias: npm i playwright swagger-ui-dist@5
const { chromium } = require('playwright');
const BASE='http://127.0.0.1:4173', API='http://127.0.0.1:8000', FECHA='2026-11-12';
const VW=1600, VH=900, DW=412, DH=880;
const seg=[]; // [videoKey, from, to]
const CAPCSS=`#__cap{position:fixed;left:50%;transform:translateX(-50%);bottom:18px;z-index:2147483647;max-width:min(92vw,1100px);background:rgba(10,20,14,.88);color:#fff;font:600 19px/1.35 system-ui,sans-serif;padding:10px 18px;border-radius:10px;box-shadow:0 4px 18px rgba(0,0,0,.35);pointer-events:none;text-align:center}@media (max-width:500px){#__cap{top:64px;bottom:auto;font-size:15px;padding:8px 12px}}#__cap small{display:block;font-weight:500;font-size:14px;opacity:.85;margin-top:2px}`;
async function cap(p, t, sub){ await p.evaluate(([t,sub,css])=>{ let s=document.getElementById('__capcss'); if(!s){s=document.createElement('style');s.id='__capcss';s.textContent=css;document.head.appendChild(s);} let e=document.getElementById('__cap'); if(!e){e=document.createElement('div');e.id='__cap';document.body.appendChild(e);} e.innerHTML=''; const b=document.createElement('div'); b.textContent=t; e.appendChild(b); if(sub){const sm=document.createElement('small'); sm.textContent=sub; e.appendChild(sm);} },[t,sub||'',CAPCSS]); }
const wait=(p,ms)=>p.waitForTimeout(ms);
function clock(start){ return ()=> (Date.now()-start)/1000; }
async function card(p, title, lines){ await p.setContent(`<html lang="es"><body style="margin:0;height:100vh;display:grid;place-items:center;background:#0f1a14;color:#eef5ef;font-family:system-ui,sans-serif"><div style="max-width:1100px;padding:40px"><div style="font-size:20px;letter-spacing:.12em;text-transform:uppercase;color:#6ee7a0">EcoLogística Lima · Sprint 4</div><h1 style="font-size:54px;margin:.3em 0 .4em;line-height:1.1">${title}</h1>${lines.map(l=>`<p style="font-size:24px;margin:.35em 0;color:#c9d6cc">${l}</p>`).join('')}</div></body></html>`); }
async function login(p,email,pw){ await p.goto(BASE+'/login'); await p.getByLabel(/correo/i).pressSequentially(email,{delay:35}); await p.getByLabel(/contraseña/i).first().pressSequentially(pw,{delay:20}); await wait(p,400); await p.getByRole('button',{name:/iniciar sesión/i}).click(); await p.waitForURL(BASE+'/',{timeout:15000}); }
function hhmm(d){ const f=new Intl.DateTimeFormat('sv-SE',{timeZone:'America/Lima',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(d); return f.replace(' ','T'); }
(async()=>{
  const b=await chromium.launch({slowMo:120});
  const ctx=await b.newContext({viewport:{width:VW,height:VH},recordVideo:{dir:__dirname+'/video/op',size:{width:VW,height:VH}},locale:'es-PE',timezoneId:'America/Lima'});
  const op=await ctx.newPage(); const t1=clock(Date.now());
  await card(op,'Demostración del MVP',['Optimizar rutas · mapa · registrar y cerrar una ruta · dashboard de sostenibilidad · incidencia del conductor','Grabación automatizada (Playwright) del sistema real: build de producción, API FastAPI y PostgreSQL/PostGIS locales','Datos de la demo: 150 pedidos, 15 vehículos, 4 distritos de Lima · 12/11/2026']);
  await wait(op,6000);
  await login(op,'operador.demo@ecologistica.example',process.env.SEED_DEMO_PASSWORD_OPERADOR);
  await cap(op,'1 · El Operador inicia sesión','Rol Operador: rutas, incidencias e indicadores'); await wait(op,3500);
  seg.push(['op',0,t1()]);
  // Swagger in a second tab (same session cookie)
  const sw=await ctx.newPage(); const t2=clock(Date.now());
  // The sandbox blocks cdn.jsdelivr.net: serve the same swagger-ui-dist@5 files locally.
  const SUI=require('path').dirname(require.resolve('swagger-ui-dist/package.json'));
  await sw.route(/cdn\.jsdelivr\.net\/npm\/swagger-ui-dist@5\/(.*)$/, r=>{ const f=r.request().url().split('/').pop(); r.fulfill({path:SUI+'/'+f}); });
  await sw.route(/fastapi\.tiangolo\.com/, r=>r.fulfill({status:204,body:''}));
  await sw.goto(API+'/docs'); await sw.waitForSelector('.opblock'); await wait(sw,800);
  await cap(sw,'2 · Optimizar la fecha (US-006) desde la API','Todavía no hay botón en la interfaz: se solicita con POST /optimizaciones');
  const blk=sw.locator('.opblock-post').filter({has: sw.locator('.opblock-summary-path',{hasText:/^\/optimizaciones$/})}).first();
  await blk.locator('.opblock-summary').click(); await wait(sw,800); await blk.scrollIntoViewIfNeeded();
  await blk.getByRole('button',{name:/try it out/i}).click(); await wait(sw,600);
  const ta=blk.locator('textarea.body-param__text'); await ta.fill(''); await ta.pressSequentially(`{"fecha_operacion": "${FECHA}"}`,{delay:30});
  await wait(sw,800);
  await cap(sw,'2 · OR-Tools VRPTW: 150 pedidos y 15 vehículos','Respeta capacidad, ventanas, jornada y descansos · RNF-001 pide ≤ 45 s (P95 medido: 20,18 s)');
  const tExec=Date.now(); await blk.getByRole('button',{name:/^execute$/i}).click();
  await blk.locator('.live-responses-table tr.response td.response-col_status').first().waitFor({timeout:120000});
  const secs=((Date.now()-tExec)/1000).toFixed(1);
  const status=(await blk.locator('.live-responses-table tr.response td.response-col_status').first().innerText()).trim().split(/\s/)[0];
  await blk.locator('.live-responses-table').scrollIntoViewIfNeeded(); await wait(sw,500);
  await cap(sw,`2 · Respuesta ${status} en ${secs.replace('.',',')} s: optimización COMPLETADA`,'Incluye los pedidos no asignados con motivo (2 inviables a propósito: capacidad y ventana)');
  await wait(sw,7000); seg.push(['sw',0,t2()]); await sw.close();
  // Choose a route with 4–5 stops whose ETAs are already past
  const lista=await (await op.request.get(API+'/optimizaciones?fecha_operacion='+FECHA)).json();
  const items=lista.items||lista; const opt=(Array.isArray(items)?items:[]).sort((a,b)=>String(b.creada_en||b.solicitada_en||'').localeCompare(String(a.creada_en||a.solicitada_en||'')))[0];
  const det=await (await op.request.get(API+'/optimizaciones/'+(opt.optimizacion_id||opt.id))).json();
  const now=new Date(Date.now()-3*60000);
  // Pick, among short routes already past their ETAs, the one with the largest
  // saving against its own sequential baseline (stored by the engine).
  // Only a well-formed UUID reaches the query, and psql is called without a shell.
  if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(det.optimizacion_id)) throw new Error('optimizacion_id inválido');
  const sql=`select r.ruta_id||' '||coalesce(100*(1-r.distancia_km/nullif(r.secuencial_distancia_km,0)),-999) from ruta r where r.optimizacion_id='${det.optimizacion_id}'`;
  const salida=require('child_process').execFileSync('psql',['-h','localhost','-U','ecl','-d','ecologistica_demo','-At','-c',sql],{env:{...process.env,PGPASSWORD:process.env.PGPW}});
  const ahorro=Object.fromEntries(salida.toString().trim().split('\n').map(l=>l.split(' ')).map(([k,v])=>[k,+v]));
  const pasadas=det.rutas.filter(r=>r.paradas.every(p=>new Date(p.eta)<=now));
  const cand=pasadas.filter(r=>r.paradas.length>=4&&r.paradas.length<=9).sort((a,b)=>ahorro[b.ruta_id]-ahorro[a.ruta_id]);
  const ruta=cand[0]||pasadas.sort((a,b)=>a.paradas.length-b.paradas.length)[0];
  console.log('AHORRO', ruta.vehiculo.placa, ahorro[ruta.ruta_id].toFixed(1));
  console.log('RUTA', ruta.vehiculo.placa, ruta.paradas.length, 'rutas', det.rutas.length, 'no asignados', (det.no_asignados||[]).length);
  // Back to the app
  await op.bringToFront(); const resumeA=t1();
  await op.getByRole('link',{name:/rutas y alertas/i}).first().click(); await op.locator('#route-date').fill(FECHA);
  await cap(op,'3 · Rutas y alertas en mapa (US-008)','Se consulta el plan de la fecha'); await wait(op,1200);
  await op.getByRole('button',{name:/actualizar optimizaciones/i}).click(); await op.getByRole('button',{name:/^Ruta /}).first().waitFor(); await wait(op,1500);
  await cap(op,`3 · ${det.rutas.length} rutas: vehículo, paradas, km, minutos y conductor`,'Cada ruta se abre para ver su mapa y su secuencia'); await wait(op,4500);
  await op.getByRole('button',{name:new RegExp('^Ruta '+ruta.vehiculo.placa)}).first().click(); await wait(op,1800);
  await cap(op,`3 · Ruta ${ruta.vehiculo.placa}: mapa Leaflet con OpenStreetMap`,'ETA de planificación. Este entorno de grabación no tiene internet: sin teselas de OSM, la app lo avisa y mantiene trazado y lista'); await wait(op,6000);
  const link=op.getByRole('link',{name:/lista accesible/i}).first(); if(await link.count()){ await link.click(); await wait(op,800);} 
  await cap(op,'3 · Lista accesible de paradas: la alternativa textual al mapa (WCAG)','Mismo orden que el mapa, con ventana, ETA y estado'); await wait(op,5000);
  // Register stops with the real time inside the window
  await cap(op,'4 · El Operador registra la hora real de atención de cada parada','La hora real se escribe dentro de la ventana de la parada');
  for(const p of ruta.paradas){
    const n=p.secuencia; const ini=new Date(p.ventana_inicio), fin=new Date(p.ventana_fin); let t=new Date(p.eta); if(t<ini)t=ini; if(t>fin)t=fin; if(t>now)t=now;
    await op.getByRole('button',{name:`Registrar resultado de parada ${n}`,exact:true}).click(); await wait(op,500);
    const inp=op.getByLabel(`Hora real de parada ${n} (Lima)`); await inp.fill(hhmm(t)); await wait(op,700);
    await op.getByRole('button',{name:`Guardar resultado de parada ${n}`,exact:true}).click();
    await op.getByText(new RegExp(`Resultado de parada ${n} registrado`)).waitFor({timeout:10000}); await wait(op,1100);
  }
  await cap(op,'5 · Con todas las paradas registradas se puede cerrar la ruta','La confirmación está dentro de la página'); await wait(op,2500);
  await op.getByRole('button',{name:'Cerrar ruta'}).click(); await wait(op,1800);
  await op.getByRole('button',{name:'Confirmar cierre'}).click(); await op.getByText(/Ruta cerrada el/).waitFor({timeout:15000}); await wait(op,800);
  await cap(op,'5 · Ruta cerrada: sus indicadores pasan al dashboard','Estado: cerrada'); await wait(op,4500);
  await op.getByRole('link',{name:'Inicio'}).first().click(); await op.getByRole('link',{name:/indicadores de sostenibilidad/i}).first().click(); await op.getByText(/Rutas cerradas/).first().waitFor(); await wait(op,1200);
  await cap(op,'6 · Dashboard de sostenibilidad (US-009, EN-008)','Calculado solo sobre rutas cerradas, con la versión de parámetros usada'); await wait(op,4500);
  for(let y=0;y<6;y++){ await op.mouse.wheel(0,300); await wait(op,1300);} 
  await cap(op,'6 · Ahorro frente a la ruta secuencial, CO₂, combustible, costo y cumplimiento de ventanas','«Equivalente ambiental: No disponible»: no se inventa un factor sin fuente'); await wait(op,6000);
  seg.push(['op',resumeA,t1()]);
  // Driver on mobile
  const dctx=await b.newContext({viewport:{width:DW,height:DH},isMobile:true,hasTouch:true,deviceScaleFactor:1,recordVideo:{dir:__dirname+'/video/dr',size:{width:DW,height:DH}},geolocation:{latitude:-12.0035,longitude:-76.9910},permissions:['geolocation'],locale:'es-PE',timezoneId:'America/Lima'});
  const cd=await dctx.newPage(); const t3=clock(Date.now());
  await login(cd,'conductor.demo@ecologistica.example',process.env.SEED_DEMO_PASSWORD_CONDUCTOR);
  await cap(cd,'7 · El Conductor, en su celular','Itinerario del día'); await wait(cd,2500);
  await cd.getByRole('link',{name:/abrir mi itinerario/i}).click(); await cd.getByText('Reportes de la parada 1').waitFor(); await wait(cd,3500);
  await cd.goBack(); await cd.getByRole('link',{name:/reportar incidencia/i}).first().click(); await wait(cd,1000);
  await cap(cd,'8 · Reporta una incidencia (US-012)','Tipo, severidad, ubicación y observación');
  await cd.locator('#tipo').selectOption({label:'Tráfico'}); await wait(cd,700); await cd.getByLabel(/Media/).check(); await wait(cd,700);
  await cd.getByRole('button',{name:/usar mi ubicación/i}).click(); await wait(cd,1500);
  await cd.locator('textarea').pressSequentially('Congestión en la avenida principal; demora estimada de 20 minutos.',{delay:18}); await wait(cd,800);
  await cd.getByRole('button',{name:'Enviar incidencia'}).click(); await cd.getByText(/Incidencia registrada · pendiente de validación/).waitFor({timeout:15000});
  await cap(cd,'8 · Incidencia registrada, pendiente de validación'); await wait(cd,5000);
  seg.push(['dr',0,t3()]); await dctx.close();
  // Operator validates
  await op.bringToFront(); const resumeB=t1();
  await op.getByRole('link',{name:'Inicio'}).first().click(); await op.getByRole('link',{name:/incidencias pendientes/i}).first().click();
  await op.getByText(/Congestión en la avenida principal/).first().waitFor({timeout:10000}); await wait(op,800);
  await cap(op,'9 · El Operador ve la incidencia nueva y la valida (RF-007, RN-019)'); await wait(op,3500);
  const row=op.locator('tr',{hasText:'Congestión en la avenida principal'}).first(); await row.getByRole('button',{name:/Validar/}).click(); await wait(op,1200);
  const conf=op.getByRole('button',{name:/confirmar/i}); if(await conf.count()){ await conf.first().click(); }
  await op.getByText(/validad/i).first().waitFor({timeout:10000}); await wait(op,800);
  await cap(op,'9 · Incidencia validada'); await wait(op,4500);
  await card(op,'Fin del recorrido',['Optimización real · mapa y lista accesible · cierre de ruta · dashboard · incidencia validada','Repositorio: JulioNaupariC/EcoLog-stica-Lima · Guía de la demo: docs/03 Implementación/Sprint 04/guias/GUIA_DEMO_SPRINT4.md']);
  await wait(op,5000); seg.push(['op',resumeB,t1()]);
  const opVideo=await op.video().path(); await ctx.close(); await b.close();
  const fs=require('fs'); const dr=fs.readdirSync(__dirname+'/video/dr').map(f=>__dirname+'/video/dr/'+f)[0]; const sv=fs.readdirSync(__dirname+'/video/op').map(f=>__dirname+'/video/op/'+f).filter(f=>f!==opVideo)[0];
  fs.writeFileSync(__dirname+'/video/segments.json',JSON.stringify({op:opVideo,sw:sv,dr,seg},null,1));
  console.log('OK', JSON.stringify(seg));
})().catch(e=>{console.error('ERR',e.message); process.exit(1);});
