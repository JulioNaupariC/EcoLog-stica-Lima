const { chromium } = require('playwright'); const { login } = require('./lib');
(async()=>{ const b=await chromium.launch(); const out={};
 const p=await b.newPage({viewport:{width:1366,height:900}});
 await login(p,'operador.demo@ecologistica.example',process.env.SEED_DEMO_PASSWORD_OPERADOR);
 await p.getByRole('link',{name:/rutas y alertas/i}).first().click(); await p.locator('#route-date').fill('2026-11-12'); await p.getByRole('button',{name:/actualizar optimizaciones/i}).click(); await p.getByRole('button',{name:/^Ruta /}).first().waitFor(); await p.waitForTimeout(800);
 // keyboard: focus the "Registrar resultado de parada 1" via Tab sequence
 await p.getByRole('button',{name:/^Ruta DEMO-005/}).focus(); await p.keyboard.press('Enter'); await p.waitForTimeout(400);
 const reg=p.getByRole('button',{name:'Registrar resultado de parada 1',exact:true}); await reg.focus(); await p.keyboard.press('Enter'); await p.waitForTimeout(400);
 out.foco_tras_abrir = await p.evaluate(()=>{const a=document.activeElement; return a.tagName+':'+(a.id||'')+':'+(a.getAttribute('aria-label')||a.innerText||'').slice(0,40);});
 out.outline = await p.evaluate(()=>{const a=document.activeElement; const s=getComputedStyle(a); return s.outlineStyle+' '+s.outlineWidth+' '+s.outlineColor+' / box-shadow:'+s.boxShadow.slice(0,60);});
 await p.keyboard.press('Escape'); await p.waitForTimeout(300);
 const cancel=p.getByRole('button',{name:'Cancelar registro de parada 1',exact:true}); if (await cancel.count()) { await cancel.focus(); await p.keyboard.press('Enter'); await p.waitForTimeout(300); }
 out.foco_tras_cancelar = await p.evaluate(()=>{const a=document.activeElement; return a.tagName+':'+(a.getAttribute('aria-label')||a.innerText||'').slice(0,40);});
 // map keyboard
 out.mapa_instr = (await p.locator('main').innerText()).match(/Mapa interactivo[^\n]*/)?.[0];
 // reflow 320px: navigate at desktop width, then resize (the SPA keeps the session)
 await p.setViewportSize({width:320,height:800}); await p.waitForTimeout(600);
 out.reflow_320_rutas = await p.evaluate(()=>document.documentElement.scrollWidth - window.innerWidth);
 await p.setViewportSize({width:1366,height:900}); await p.getByRole('link',{name:'Inicio'}).first().click();
 await p.getByRole('link',{name:/indicadores de sostenibilidad/i}).first().click(); await p.getByText(/Rutas cerradas/).first().waitFor();
 await p.setViewportSize({width:320,height:800}); await p.waitForTimeout(600);
 out.reflow_320_dashboard = await p.evaluate(()=>document.documentElement.scrollWidth - window.innerWidth);
 console.log(JSON.stringify(out,null,1)); await b.close(); })();
