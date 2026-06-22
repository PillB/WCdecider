#!/usr/bin/env python3
"""Generate the batch-independent bilingual WCdecider report shell."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "index.html"

HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="Replicable World Cup 2026 probability and betting-market analysis for June 22–27.">
  <meta name="wcdecider-build" content="__BUILD_SHA__">
  <title>WCdecider • June 22–27, 2026</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .lang-es .en,.lang-en .es{display:none!important}
    .tip{position:relative;border-bottom:1px dotted #94a3b8;cursor:help}
    .tip>span{display:none;position:absolute;z-index:60;left:50%;bottom:calc(100% + .5rem);
      transform:translateX(-50%);width:min(22rem,85vw);padding:.65rem;border:1px solid #475569;
      border-radius:.75rem;background:#020617;color:#e2e8f0;font-size:.75rem;line-height:1.25rem;
      white-space:normal;box-shadow:0 12px 30px #0008}
    .tip:hover>span,.tip:focus>span{display:block}
    .card-anchor{scroll-margin-top:6rem}
  </style>
</head>
<body class="lang-en bg-slate-950 text-slate-200 min-h-screen">
  <nav class="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/95 backdrop-blur">
    <div class="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between gap-3">
      <div>
        <div class="font-black tracking-tight text-white">WCdecider</div>
        <div class="text-xs text-slate-400">
          <span class="en">June 22–27 • reproducible probabilities</span>
          <span class="es">22–27 de junio • probabilidades reproducibles</span>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span id="status" class="text-xs text-amber-300"><span class="en">Loading verified JSON…</span><span class="es">Cargando JSON verificado…</span></span>
        <button id="lang" class="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold" type="button">ES</button>
      </div>
    </div>
  </nav>

  <main class="mx-auto max-w-7xl px-4 py-8">
    <section class="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6 md:p-8 mb-8">
      <div class="grid lg:grid-cols-[1.25fr_.75fr] gap-8 items-center">
        <div>
          <p class="text-emerald-400 text-sm font-bold uppercase tracking-widest">
            <span class="en">Integrity-first update</span><span class="es">Actualización con integridad primero</span>
          </p>
          <h1 class="text-3xl md:text-5xl font-black text-white mt-2">
            <span class="en">32 matches. One auditable pipeline.</span>
            <span class="es">32 partidos. Un pipeline auditable.</span>
          </h1>
          <p class="mt-4 text-slate-300 leading-7">
            <span class="en">Every displayed odd comes from a Betano or Betsson screenshot. Probabilities are generated before market comparison, then tested for expected value, sensitivity and model-market disagreement.</span>
            <span class="es">Cada cuota mostrada proviene de una captura de Betano o Betsson. Las probabilidades se generan antes de comparar el mercado y luego se prueban por valor esperado, sensibilidad y desacuerdo modelo-mercado.</span>
          </p>
          <div id="summary" class="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3"></div>
        </div>
        <svg viewBox="0 0 520 360" role="img" aria-labelledby="flow-title" class="w-full">
          <title id="flow-title">WCdecider model workflow</title>
          <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#34d399"/></marker></defs>
          <g fill="#0f172a" stroke="#334155" stroke-width="2">
            <rect x="20" y="25" width="145" height="64" rx="14"/><rect x="20" y="113" width="145" height="64" rx="14"/>
            <rect x="20" y="201" width="145" height="64" rx="14"/><rect x="205" y="78" width="145" height="124" rx="18"/>
            <rect x="390" y="25" width="110" height="64" rx="14"/><rect x="390" y="113" width="110" height="64" rx="14"/>
            <rect x="390" y="201" width="110" height="64" rx="14"/>
          </g>
          <g fill="#e2e8f0" font-family="system-ui" font-size="14" text-anchor="middle">
            <text x="92" y="52"><tspan class="en">Dataset A/B</tspan><tspan class="es">Dataset A/B</tspan></text><text x="92" y="72"><tspan class="en">temporal history</tspan><tspan class="es">historia temporal</tspan></text>
            <text x="92" y="140"><tspan class="en">Elapsed WC</tspan><tspan class="es">Mundial jugado</tspan></text><text x="92" y="160">40 results</text>
            <text x="92" y="228"><tspan class="en">Screenshots</tspan><tspan class="es">Capturas</tspan></text><text x="92" y="248">Betano + Betsson</text>
            <text x="277" y="110">Elo + Poisson</text><text x="277" y="134"><tspan class="en">chronological calibration</tspan><tspan class="es">calibración cronológica</tspan></text>
            <text x="277" y="158"><tspan class="en">score-grid settlement</tspan><tspan class="es">liquidación por marcadores</tspan></text><text x="277" y="182">stress tests</text>
            <text x="445" y="52"><tspan class="en">Probabilities</tspan><tspan class="es">Probabilidades</tspan></text><text x="445" y="72">1X2 + goals</text>
            <text x="445" y="140">EV + HALT</text><text x="445" y="160"><tspan class="en">risk classes</tspan><tspan class="es">clases de riesgo</tspan></text>
            <text x="445" y="228">JSON</text><text x="445" y="248"><tspan class="en">32 cards</tspan><tspan class="es">32 tarjetas</tspan></text>
          </g>
          <g stroke="#34d399" stroke-width="3" fill="none" marker-end="url(#arrow)">
            <path d="M165 57 C190 57 185 105 205 112"/><path d="M165 145 H205"/><path d="M165 233 C190 233 185 180 205 172"/>
            <path d="M350 112 C370 100 370 65 390 57"/><path d="M350 140 H390"/><path d="M350 172 C370 185 370 225 390 233"/>
          </g>
        </svg>
      </div>
    </section>

    <section class="mb-8 grid lg:grid-cols-[1fr_1fr] gap-5">
      <div class="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <h2 class="text-xl font-bold text-white"><span class="en">How to read a recommendation</span><span class="es">Cómo leer una recomendación</span></h2>
        <ol class="mt-3 space-y-2 text-sm text-slate-300 list-decimal pl-5">
          <li><span class="en">Find the exact match, app, market and selection shown.</span><span class="es">Busca el partido, app, mercado y selección exactos.</span></li>
          <li><span class="en">Confirm the current decimal odd still matches the captured price.</span><span class="es">Confirma que la cuota decimal actual aún coincide con la captura.</span></li>
          <li><span class="en">If the price moved, treat the displayed EV as stale and stop.</span><span class="es">Si la cuota cambió, considera el EV desactualizado y detente.</span></li>
          <li><span class="en">Read risks and confidence. Analysis is not a guarantee or instruction to bet.</span><span class="es">Lee riesgos y confianza. El análisis no es garantía ni instrucción para apostar.</span></li>
        </ol>
      </div>
      <div class="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <h2 class="text-xl font-bold text-white"><span class="en">Newbie glossary</span><span class="es">Glosario para principiantes</span></h2>
        <div class="mt-3 text-sm text-slate-300 space-y-2">
          <p><span class="tip" tabindex="0">1X2<span><span class="en">1 = first team wins, X = draw, 2 = second team wins.</span><span class="es">1 = gana el primer equipo, X = empate, 2 = gana el segundo.</span></span></span>: <span class="en">the three full-time result choices.</span><span class="es">las tres opciones de resultado final.</span></p>
          <p><span class="tip" tabindex="0">EV<span><span class="en">Expected value is the estimated average return over many similar bets, not certainty in one match.</span><span class="es">Valor esperado es el retorno promedio estimado en muchas apuestas similares, no certeza en un partido.</span></span></span>: <span class="en">positive does not mean guaranteed.</span><span class="es">positivo no significa garantizado.</span></p>
          <p><span class="tip" tabindex="0">HALT<span><span class="en">The apparent edge is too extreme or disagrees too much with the market, so extra verification is required.</span><span class="es">La ventaja aparente es extrema o discrepa demasiado del mercado, por lo que requiere verificación extra.</span></span></span>: <span class="en">do not treat it as actionable.</span><span class="es">no lo trates como accionable.</span></p>
        </div>
      </div>
    </section>

    <section class="mb-6 flex flex-wrap items-center gap-3">
      <label class="text-sm"><span class="en">Date</span><span class="es">Fecha</span>
        <select id="date-filter" class="ml-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2"><option value="">All / Todos</option></select>
      </label>
      <label class="text-sm"><span class="en">Strength</span><span class="es">Fuerza</span>
        <select id="strength-filter" class="ml-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2">
          <option value="">All / Todos</option><option>PASS</option><option>HALT</option>
        </select>
      </label>
    </section>

    <section id="error" class="hidden rounded-3xl border border-red-800 bg-red-950 p-6 mb-8"></section>
    <section id="cards" class="grid lg:grid-cols-2 gap-6"></section>

    <section class="mt-10 rounded-3xl border border-amber-800/60 bg-amber-950/30 p-5 text-sm text-amber-100">
      <p class="en">Betting carries real risk of financial loss. This is analysis only, not financial advice or a guarantee of outcomes. Past form and model edges do not predict individual match results. If gambling is no longer recreational, contact Peru's Línea 0800-1-3232 (MINCETUR) or Jugadores Anónimos Perú.</p>
      <p class="es">Apostar conlleva riesgo real de pérdida financiera. Esto es solo análisis, no consejo financiero ni garantía de resultados. El rendimiento pasado y las ventajas del modelo no predicen partidos individuales. Si apostar deja de ser recreativo, contacta la Línea 0800-1-3232 (MINCETUR) o Jugadores Anónimos Perú.</p>
    </section>
  </main>

<script>
const $=s=>document.querySelector(s);
const escapeHtml=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let DATA=null;
 const strengthColor=s=>({HALT:'text-red-300 border-red-700',PASS:'text-slate-300 border-slate-700'}[s]||'text-slate-300 border-slate-700');
function metric(label,value){return `<div class="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div class="text-xs text-slate-500">${label}</div><div class="text-lg font-black text-white">${value}</div></div>`}
function renderSummary(rows){
 const recs=[];
 const halted=rows.filter(x=>x.recommendation?.strength==='HALT').length;
 $('#summary').innerHTML=metric('Fixtures / Partidos',rows.length)+metric('Candidates / Candidatas',recs.length)+metric('HALT',halted)+metric('Model hash',DATA.model.pipeline_sha256.slice(0,8));
}
function card(row){
 const r=row.recommendation;
 const strength=r?.strength||'PASS';
 const rec=r?`${escapeHtml(r.selection_original)} ${r.line?`(${escapeHtml(r.line)})`:''} @ ${Number(r.odds).toFixed(2)}`:'No supported price / Sin cuota compatible';
 const sources=(row.research?.source_urls||[]).map(u=>`<a class="text-cyan-400 hover:underline break-all" href="${escapeHtml(u)}" target="_blank" rel="noopener">${escapeHtml(new URL(u).hostname)}</a>`).join(' · ');
 return `<article class="card-anchor bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden" data-fixture-id="${escapeHtml(row.fixture_id)}" data-date="${row.kickoff_lima.slice(0,10)}" data-strength="${strength}">
   <header class="p-5 border-b border-slate-800 flex justify-between gap-4">
    <div><div class="text-xs text-slate-500">${escapeHtml(row.kickoff_lima.replace('T',' ').slice(0,16))} • Group ${escapeHtml(row.group)}</div>
    <h2 class="mt-1 text-xl font-black text-white"><span class="en">${escapeHtml(row.fixture.en)}</span><span class="es">${escapeHtml(row.fixture.es)}</span></h2></div>
    <span class="h-fit rounded-full border px-3 py-1 text-xs font-bold ${strengthColor(strength)}">${strength}</span>
   </header>
   <div class="p-5">
    <div class="grid grid-cols-3 gap-2 text-center">
     ${metric('1',`${(row.probabilities.team_a_win*100).toFixed(1)}%`)}
     ${metric('X',`${(row.probabilities.draw*100).toFixed(1)}%`)}
     ${metric('2',`${(row.probabilities.team_b_win*100).toFixed(1)}%`)}
    </div>
    <div class="mt-4 rounded-2xl border border-slate-700 bg-slate-950 p-4">
      <div class="text-xs text-slate-500"><span class="en">Best supported screenshot candidate</span><span class="es">Mejor candidata compatible de capturas</span></div>
      <div class="mt-1 font-bold text-white">${rec}</div>
      ${r?`<div class="mt-2 grid grid-cols-3 gap-2 text-sm"><div>EV <b>${r.ev_pct.toFixed(1)}%</b></div><div><span class="en">Stress</span><span class="es">Estrés</span> <b>${r.stressed_ev_pct.toFixed(1)}%</b></div><div><span class="en">Confidence</span><span class="es">Confianza</span> <b>${r.confidence}%</b></div></div>
      <div class="mt-2 text-xs text-slate-400">${escapeHtml(r.app)} • ${escapeHtml(r.market_original)} • ${escapeHtml(r.source_image)}</div>`:''}
    </div>
    <details class="mt-4 rounded-2xl border border-slate-800 p-4">
      <summary class="cursor-pointer font-semibold"><span class="en">Research, risks and ELI5</span><span class="es">Investigación, riesgos y ELI5</span></summary>
      <div class="mt-3 space-y-3 text-sm text-slate-300">
        <p><b><span class="en">Team news:</span><span class="es">Noticias:</span></b> ${escapeHtml(row.research?.team_news||'Unavailable')}</p>
        <p><b><span class="en">Injuries/suspensions:</span><span class="es">Lesiones/sanciones:</span></b> ${escapeHtml(row.research?.injuries_suspensions||'Unavailable')}</p>
        <p><b><span class="en">Motivation:</span><span class="es">Motivación:</span></b> ${escapeHtml(row.research?.motivation_group_state||'Unavailable')}</p>
        <ul class="list-disc pl-5"><span class="en">${row.risk_notes.en.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</span><span class="es">${row.risk_notes.es.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</span></ul>
        <p><b>ELI5:</b> <span class="en">Open the named app, search World Cup, open this exact fixture, find the market shown above, and compare the current price with the captured price. If any label or price differs, stop because the displayed EV is no longer valid. You decide whether to act.</span><span class="es">Abre la app indicada, busca Copa del Mundo, abre este partido exacto, encuentra el mercado mostrado y compara la cuota actual con la capturada. Si cambia una etiqueta o cuota, detente porque el EV ya no es válido. Tú decides si actuar.</span></p>
        <p class="text-xs">${sources}</p>
      </div>
    </details>
   </div>
 </article>`;
}
function applyFilters(){
 const d=$('#date-filter').value,s=$('#strength-filter').value;
 document.querySelectorAll('#cards article').forEach(c=>c.classList.toggle('hidden',(d&&c.dataset.date!==d)||(s&&c.dataset.strength!==s)));
}
async function load(){
 try{
  const response=await fetch('wc_june22_27_predictions.json',{cache:'no-store'});
  if(!response.ok)throw new Error(`predictions.json HTTP ${response.status}`);
  DATA=await response.json();
  if(DATA.batch.fixture_count!==32||DATA.predictions.length!==32)throw new Error('Expected exactly 32 predictions');
  const ids=new Set(DATA.predictions.map(x=>x.fixture_id)); if(ids.size!==32)throw new Error('Duplicate fixture IDs');
  renderSummary(DATA.predictions);
  $('#cards').innerHTML=DATA.predictions.map(card).join('');
  [...new Set(DATA.predictions.map(x=>x.kickoff_lima.slice(0,10)))].forEach(d=>$('#date-filter').insertAdjacentHTML('beforeend',`<option value="${d}">${d}</option>`));
  $('#status').innerHTML='<span class="en">Verified JSON loaded</span><span class="es">JSON verificado cargado</span>';
 }catch(error){
  $('#error').classList.remove('hidden'); $('#error').textContent=`Report data failed to load: ${error.message}`;
  $('#status').textContent='DATA ERROR';
 }
}
$('#lang').addEventListener('click',()=>{const es=document.body.classList.contains('lang-es');document.body.classList.toggle('lang-es',!es);document.body.classList.toggle('lang-en',es);$('#lang').textContent=es?'ES':'EN';document.documentElement.lang=es?'en':'es';});
$('#date-filter').addEventListener('change',applyFilters);$('#strength-filter').addEventListener('change',applyFilters);
load();
</script>
</body></html>
"""


def main() -> None:
    OUT.write_text(HTML, encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
