#!/usr/bin/env python3
"""Generate the batch-independent bilingual WCdecider report shell."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "index.html"
AUDIT = ROOT / "wc_june22_27_datapoint_audit.csv"

HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="Replicable World Cup 2026 probability and betting-market analysis for June 22–27.">
  <meta name="wcdecider-build" content="__BUILD_SHA__">
  <meta name="wcdecider-audit-sha256" content="__AUDIT_SHA__">
  <title>WCdecider • June 22–27, 2026</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .lang-es .en,.lang-en .es{display:none!important}
    .tip{position:relative;border-bottom:1px dotted #94a3b8;cursor:help}
    .tip>span{display:none;position:fixed;z-index:100;left:0;top:0;
      width:min(24rem,calc(100vw - 1rem));max-height:min(22rem,calc(100vh - 1rem));
      overflow:auto;padding:.65rem;border:1px solid #475569;
      border-radius:.75rem;background:#020617;color:#e2e8f0;font-size:.75rem;line-height:1.25rem;
      white-space:normal;box-shadow:0 12px 30px #0008;pointer-events:none}
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
        <span id="status" class="text-xs text-amber-300" aria-live="polite"><span class="en">Loading verified JSON…</span><span class="es">Cargando JSON verificado…</span></span>
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
          <div id="model-evidence" class="mt-4 rounded-2xl border border-slate-700 bg-slate-950/70 p-4 text-sm text-slate-300"></div>
        </div>
        <svg viewBox="0 0 640 430" role="img" aria-labelledby="flow-title flow-desc" class="w-full">
          <title id="flow-title"><tspan class="en">WCdecider model workflow</tspan><tspan class="es">Flujo del modelo WCdecider</tspan></title>
          <desc id="flow-desc"><tspan class="en">Sources flow through immutable provenance, chronological model championship, score-distribution markets, market shrinkage, risk ranking, four-role audit, JSON, and a defensive mobile report shell.</tspan><tspan class="es">Las fuentes pasan por procedencia inmutable, campeonato cronológico de modelos, mercados por distribución de marcadores, ajuste hacia mercado, ranking de riesgo, auditoría de cuatro roles, JSON y una página móvil defensiva.</tspan></desc>
          <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#34d399"/></marker></defs>
          <g fill="#0f172a" stroke="#334155" stroke-width="2">
            <rect x="18" y="22" width="142" height="58" rx="14"/><rect x="18" y="100" width="142" height="58" rx="14"/>
            <rect x="18" y="178" width="142" height="58" rx="14"/><rect x="18" y="256" width="142" height="58" rx="14"/>
            <rect x="205" y="35" width="150" height="74" rx="16"/><rect x="205" y="132" width="150" height="74" rx="16"/>
            <rect x="205" y="229" width="150" height="74" rx="16"/><rect x="400" y="35" width="150" height="74" rx="16"/>
            <rect x="400" y="132" width="150" height="74" rx="16"/><rect x="400" y="229" width="150" height="74" rx="16"/>
            <rect x="205" y="335" width="345" height="58" rx="16"/>
          </g>
          <g fill="#e2e8f0" font-family="system-ui" font-size="13" text-anchor="middle">
            <text x="89" y="47"><tspan class="en">Dataset A/B</tspan><tspan class="es">Dataset A/B</tspan></text><text x="89" y="65"><tspan class="en">253 results</tspan><tspan class="es">253 resultados</tspan></text>
            <text x="89" y="125"><tspan class="en">Elapsed WC</tspan><tspan class="es">Mundial jugado</tspan></text><text x="89" y="143"><tspan class="en">40 results</tspan><tspan class="es">40 resultados</tspan></text>
            <text x="89" y="203"><tspan class="en">Screenshots</tspan><tspan class="es">Capturas</tspan></text><text x="89" y="221">Betano + Betsson</text>
            <text x="89" y="281"><tspan class="en">Historical odds</tspan><tspan class="es">Cuotas históricas</tspan></text><text x="89" y="299"><tspan class="en">proxy gated</tspan><tspan class="es">proxy limitado</tspan></text>
            <text x="280" y="60"><tspan class="en">Provenance</tspan><tspan class="es">Procedencia</tspan></text><text x="280" y="80"><tspan class="en">hashes + source IDs</tspan><tspan class="es">hashes + fuentes</tspan></text>
            <text x="280" y="157"><tspan class="en">Model championship</tspan><tspan class="es">Campeonato modelos</tspan></text><text x="280" y="177"><tspan class="en">nested chronology</tspan><tspan class="es">cronología anidada</tspan></text>
            <text x="280" y="254"><tspan class="en">Score distribution</tspan><tspan class="es">Distribución goles</tspan></text><text x="280" y="274"><tspan class="en">Poisson + DC shadow</tspan><tspan class="es">Poisson + DC sombra</tspan></text>
            <text x="475" y="60"><tspan class="en">Market shrinkage</tspan><tspan class="es">Ajuste a mercado</tspan></text><text x="475" y="80"><tspan class="en">vig removed</tspan><tspan class="es">sin margen</tspan></text>
            <text x="475" y="157">BEST AVAILABLE</text><text x="475" y="177"><tspan class="en">utility ranking</tspan><tspan class="es">ranking utilidad</tspan></text>
            <text x="475" y="254">JSON + audit</text><text x="475" y="274"><tspan class="en">31,319 PASS fields</tspan><tspan class="es">31.319 campos PASS</tspan></text>
            <text x="378" y="360"><tspan class="en">Defensive report shell</tspan><tspan class="es">Página defensiva</tspan></text><text x="378" y="379"><tspan class="en">loading state · mobile safe · footer version</tspan><tspan class="es">carga · móvil seguro · versión en pie</tspan></text>
          </g>
          <g stroke="#34d399" stroke-width="3" fill="none" marker-end="url(#arrow)">
            <path d="M160 51 H205"/><path d="M160 129 C184 129 181 72 205 72"/><path d="M160 207 C184 207 181 72 205 72"/><path d="M160 285 C184 285 181 72 205 72"/>
            <path d="M280 109 V132"/><path d="M280 206 V229"/><path d="M355 169 H400"/><path d="M355 266 C380 266 375 72 400 72"/>
            <path d="M475 109 V132"/><path d="M475 206 V229"/><path d="M475 303 C475 330 475 338 550 364"/><path d="M280 303 C280 330 280 338 205 364"/>
          </g>
        </svg>
      </div>
    </section>

    <section class="mb-8 grid lg:grid-cols-[1fr_1fr] gap-5">
      <div class="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <h2 class="text-xl font-bold text-white"><span class="en">How to read this analysis</span><span class="es">Cómo leer este análisis</span></h2>
        <ol class="mt-3 space-y-2 text-sm text-slate-300 list-decimal pl-5">
          <li><span class="en">Every match has up to four distinct sourced recommendations; rank one remains the best available. None is a guarantee.</span><span class="es">Cada partido tiene hasta cuatro recomendaciones distintas con fuente; el rango uno sigue siendo la mejor disponible. Ninguna es garantía.</span></li>
          <li><span class="en">PASS means the comparison is within investigation limits; HALT means all model edges were suspicious, so the safest market-consensus fallback is shown.</span><span class="es">PASS significa que la comparación está dentro de límites de investigación; HALT significa que todas las ventajas del modelo fueron sospechosas y se muestra la alternativa más segura según el consenso del mercado.</span></li>
          <li><span class="en">Conditional forecasts must be rerun after intervening matches and new lineups/odds.</span><span class="es">Los pronósticos condicionales deben recalcularse después de partidos intermedios y nuevas alineaciones/cuotas.</span></li>
          <li><span class="en">Displayed prices are source evidence, not instructions to place a bet.</span><span class="es">Las cuotas mostradas son evidencia de fuente, no instrucciones para apostar.</span></li>
        </ol>
      </div>
      <div class="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <h2 class="text-xl font-bold text-white"><span class="en">Newbie glossary</span><span class="es">Glosario para principiantes</span></h2>
        <div class="mt-3 text-sm text-slate-300 space-y-2">
          <p><span class="tip" tabindex="0">1X2<span><span class="en">1 = first team wins, X = draw, 2 = second team wins.</span><span class="es">1 = gana el primer equipo, X = empate, 2 = gana el segundo.</span></span></span>: <span class="en">the three full-time result choices.</span><span class="es">las tres opciones de resultado final.</span></p>
          <p><span class="tip" tabindex="0">EV<span><span class="en">Expected value is the estimated average return over many similar bets, not certainty in one match.</span><span class="es">Valor esperado es el retorno promedio estimado en muchas apuestas similares, no certeza en un partido.</span></span></span>: <span class="en">positive does not mean guaranteed.</span><span class="es">positivo no significa garantizado.</span></p>
          <p><span class="tip" tabindex="0">HALT<span><span class="en">The apparent edge is too extreme or disagrees too much with the market, so extra verification is required.</span><span class="es">La ventaja aparente es extrema o discrepa demasiado del mercado, por lo que requiere verificación extra.</span></span></span>: <span class="en">do not treat it as actionable.</span><span class="es">no lo trates como accionable.</span></p>
          <p><span class="tip" tabindex="0">BEST AVAILABLE<span><span class="en">The highest-ranked sourced choice after stress, market disagreement and family-risk penalties. It can still lose and may have negative stressed EV.</span><span class="es">La opción con mejor ranking después de estrés, desacuerdo con el mercado y penalizaciones de riesgo. Puede perder y tener EV estresado negativo.</span></span></span>: <span class="en">a recommendation, not certainty.</span><span class="es">una recomendación, no certeza.</span></p>
          <p><span class="tip" tabindex="0"><span class="en">Stress EV</span><span class="es">EV estresado</span><span><span class="en">EV after reducing the selected outcome probability by three percentage points; this is a simple robustness check, not a confidence interval.</span><span class="es">EV después de reducir tres puntos porcentuales la probabilidad seleccionada; es una prueba simple de robustez, no un intervalo de confianza.</span></span></span></p>
          <p><span class="tip" tabindex="0">BTTS<span><span class="en">Both teams to score: Yes wins only if each team scores at least once.</span><span class="es">Ambos equipos marcan: Sí gana solo si cada equipo anota al menos una vez.</span></span></span>: <span class="en">both teams to score.</span><span class="es">ambos equipos marcan.</span></p>
          <p><span class="tip" tabindex="0"><span class="en">Asian handicap</span><span class="es">Hándicap asiático</span><span><span class="en">A virtual goal adjustment. Quarter lines split the stake across two neighboring half-lines and can create half wins or half losses.</span><span class="es">Un ajuste virtual de goles. Las líneas de cuarto dividen la apuesta entre dos medias líneas y pueden producir media ganancia o media pérdida.</span></span></span>: <span class="en">modeled with win, push and loss settlement.</span><span class="es">modelado con liquidación de victoria, nulo y derrota.</span></p>
          <p><span class="tip" tabindex="0"><span class="en">Fair odds</span><span class="es">Cuota justa</span><span><span class="en">The model's break-even decimal price before bookmaker margin. It is not a guarantee or a quoted app price.</span><span class="es">La cuota decimal de equilibrio del modelo antes del margen de la casa. No es garantía ni cuota mostrada por una app.</span></span></span>: <span class="en">model price, not sportsbook price.</span><span class="es">precio del modelo, no de la casa.</span></p>
          <p><span class="tip" tabindex="0">Brier<span><span class="en">A probability error score; lower is better. It checks the whole probability forecast, not only whether the favorite won.</span><span class="es">Una medida de error probabilístico; menor es mejor. Evalúa todo el pronóstico, no solo si ganó el favorito.</span></span></span> / <span class="tip" tabindex="0">NLL<span><span class="en">Negative log likelihood penalizes confident wrong score predictions heavily; lower is better.</span><span class="es">La log-verosimilitud negativa penaliza mucho los marcadores erróneos con alta confianza; menor es mejor.</span></span></span></p>
          <p><span class="tip" tabindex="0"><span class="en">Decision EV</span><span class="es">EV de decisión</span><span><span class="en">Expected value after shrinking the model toward the de-vigged market. It is still an estimate, not proven profit.</span><span class="es">Valor esperado después de acercar el modelo al mercado sin margen. Sigue siendo una estimación, no beneficio probado.</span></span></span> · <span class="tip" tabindex="0"><span class="en">Win equivalent</span><span class="es">Victoria equivalente</span><span><span class="en">Asian lines can split a stake into full/half wins, pushes, or losses; this is the probability-weighted winning share.</span><span class="es">Las líneas asiáticas pueden dividir la apuesta en ganancias completas/medias, nulos o pérdidas; es la proporción ganadora ponderada.</span></span></span></p>
        </div>
      </div>
    </section>

    <section class="mb-6 flex flex-wrap items-center gap-3">
      <label class="text-sm"><span class="en">Date</span><span class="es">Fecha</span>
        <select id="date-filter" disabled class="ml-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 disabled:opacity-50"><option value="">All / Todos</option></select>
      </label>
      <label class="text-sm"><span class="en">Strength</span><span class="es">Fuerza</span>
        <select id="strength-filter" disabled class="ml-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 disabled:opacity-50">
          <option value="">All / Todos</option><option>PASS</option><option>HALT</option>
        </select>
      </label>
    </section>

    <section id="loading-shell" class="mb-8 rounded-3xl border border-slate-800 bg-slate-900 p-5 text-slate-300" aria-live="polite">
      <div class="animate-pulse">
        <div class="h-4 w-48 rounded bg-slate-700"></div>
        <div class="mt-4 grid gap-4 lg:grid-cols-2">
          <div class="h-36 rounded-2xl bg-slate-800"></div>
          <div class="h-36 rounded-2xl bg-slate-800"></div>
        </div>
      </div>
      <p class="mt-4 text-sm"><span class="en">Loading the verified JSON bundle before rendering match cards. If this stays visible, refresh or check your connection.</span><span class="es">Cargando el paquete JSON verificado antes de mostrar tarjetas. Si esto permanece visible, actualiza o revisa tu conexión.</span></p>
    </section>
    <section id="bankroll-plan" class="mb-8 grid lg:grid-cols-2 gap-5"></section>
    <section id="error" class="hidden rounded-3xl border border-red-800 bg-red-950 p-6 mb-8"></section>
    <section id="cards" class="grid lg:grid-cols-2 gap-6"></section>

    <section class="mt-10 grid lg:grid-cols-2 gap-5">
      <div class="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <h2 class="text-xl font-bold text-white"><span class="en">ELI5: find the market in Betano</span><span class="es">ELI5: encuentra el mercado en Betano</span></h2>
        <ol class="mt-3 list-decimal pl-5 space-y-2 text-sm text-slate-300">
          <li><span class="en">Open Football → World Cup and search for the exact teams and kickoff date.</span><span class="es">Abre Fútbol → Mundial y busca los equipos y la fecha exacta.</span></li>
          <li><span class="en">Open the match, then choose Result, Total Goals, Both Teams Score, or Asian Handicap shown on the card.</span><span class="es">Abre el partido y elige Resultado, Total de goles, Ambos marcan o Hándicap asiático indicado en la tarjeta.</span></li>
          <li><span class="en">Match the selection and line exactly; +1, +1.25, Over 0.5, and Draw are different bets.</span><span class="es">Haz coincidir exactamente selección y línea; +1, +1,25, Más de 0,5 y Empate son apuestas diferentes.</span></li>
          <li><span class="en">Compare the current price with the screenshot price and fair odds. If it moved materially, the displayed EV is stale.</span><span class="es">Compara la cuota actual con la captura y la cuota justa. Si cambió mucho, el EV mostrado está desactualizado.</span></li>
          <li><span class="en">Confirm full-time settlement and do not assume the recommendation is guaranteed or historically profitable.</span><span class="es">Confirma que liquida al tiempo reglamentario y no supongas que la recomendación está garantizada o es históricamente rentable.</span></li>
        </ol>
      </div>
      <div class="rounded-3xl border border-slate-800 bg-slate-900 p-5">
        <h2 class="text-xl font-bold text-white"><span class="en">ELI5: find the market in Betsson</span><span class="es">ELI5: encuentra el mercado en Betsson</span></h2>
        <ol class="mt-3 list-decimal pl-5 space-y-2 text-sm text-slate-300">
          <li><span class="en">Open Sports → Football → World Cup and select the exact fixture.</span><span class="es">Abre Deportes → Fútbol → Mundial y selecciona el partido exacto.</span></li>
          <li><span class="en">Expand Match Result, Total Goals, Both Teams to Score, Asian Handicap, or Handicap + Total as named.</span><span class="es">Despliega Resultado, Total de goles, Ambos marcan, Hándicap asiático o Hándicap + Total según el nombre.</span></li>
          <li><span class="en">Verify team side, sign, line, and Over/Under leg before comparing the decimal price.</span><span class="es">Verifica equipo, signo, línea y parte Más/Menos antes de comparar la cuota decimal.</span></li>
          <li><span class="en">Use the card's source filename to audit the old screenshot. Never substitute a similar-looking line.</span><span class="es">Usa el nombre de la captura de la tarjeta para auditar la evidencia. Nunca sustituyas una línea parecida.</span></li>
          <li><span class="en">Re-check team news and price near kickoff; if either changed, rerun the model rather than relying on this snapshot.</span><span class="es">Revisa noticias y cuota cerca del inicio; si cambiaron, vuelve a ejecutar el modelo en vez de confiar en esta instantánea.</span></li>
        </ol>
      </div>
    </section>

    <section class="mt-10 rounded-3xl border border-amber-800/60 bg-amber-950/30 p-5 text-sm text-amber-100">
      <p class="en">Betting carries real risk of financial loss. This is analysis only, not financial advice or a guarantee of outcomes. Past form and model edges do not predict individual match results. If gambling is no longer recreational, contact Peru's Línea 0800-1-3232 (MINCETUR) or Jugadores Anónimos Perú.</p>
      <p class="es">Apostar conlleva riesgo real de pérdida financiera. Esto es solo análisis, no consejo financiero ni garantía de resultados. El rendimiento pasado y las ventajas del modelo no predicen partidos individuales. Si apostar deja de ser recreativo, contacta la Línea 0800-1-3232 (MINCETUR) o Jugadores Anónimos Perú.</p>
    </section>
  </main>
  <footer class="border-t border-slate-800 bg-slate-950">
    <div class="mx-auto max-w-7xl px-4 py-5 text-xs text-slate-400 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
      <div>
        <span class="font-semibold text-slate-300">WCdecider</span> ·
        <span class="en">last updated</span><span class="es">última actualización</span>
        <span id="last-updated">loading…</span>
      </div>
      <div>
        <span class="en">Version</span><span class="es">Versión</span>
        <span id="site-version">loading…</span> ·
        <span class="en">Build</span><span class="es">Build</span>
        <code id="build-sha" class="text-slate-300">__BUILD_SHA__</code>
      </div>
    </div>
  </footer>

<script>
const $=s=>document.querySelector(s);
const escapeHtml=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let DATA=null,METRICS=null,AUDIT_COUNT=0,APP_READY=false;
const setText=(selector,value)=>{const el=$(selector);if(el)el.textContent=value};
const setHtml=(selector,value)=>{const el=$(selector);if(el)el.innerHTML=value};
const showError=message=>{
 const err=$('#error'); if(err){err.classList.remove('hidden'); err.innerHTML=`<span class="en">Report data failed to load: ${escapeHtml(message)}</span><span class="es">No se pudieron cargar los datos del informe: ${escapeHtml(message)}</span>`;}
 const loading=$('#loading-shell'); if(loading)loading.classList.add('hidden');
 setHtml('#status','<span class="en">DATA ERROR</span><span class="es">ERROR DE DATOS</span>');
};
 const strengthColor=s=>({HALT:'text-red-300 border-red-700',PASS:'text-slate-300 border-slate-700'}[s]||'text-slate-300 border-slate-700');
function explanationTip(help){
 if(!help)return '';
 return `<span class="tip inline-flex ml-1 h-5 w-5 items-center justify-center rounded-full border border-slate-600 text-[11px] text-cyan-300" tabindex="0" aria-label="${escapeHtml(help.en.title)} help">?
  <span class="text-left">
   <span class="en"><b class="text-white">${escapeHtml(help.en.title)}</b><br><b>What it is:</b> ${escapeHtml(help.en.category_meaning)}<br><b>What this number means:</b> ${escapeHtml(help.en.number_meaning)}<br><b>What you can do:</b> ${escapeHtml(help.en.what_you_can_do)}</span>
   <span class="es"><b class="text-white">${escapeHtml(help.es.title)}</b><br><b>Qué es:</b> ${escapeHtml(help.es.category_meaning)}<br><b>Qué significa este número:</b> ${escapeHtml(help.es.number_meaning)}<br><b>Qué puedes hacer:</b> ${escapeHtml(help.es.what_you_can_do)}</span>
  </span>
 </span>`;
}
function metric(label,value,help=null){return `<div class="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div class="text-xs text-slate-500 flex items-center justify-center">${label}${explanationTip(help)}</div><div class="text-lg font-black text-white">${value}</div></div>`}
function renderSummary(rows){
 const halted=rows.filter(x=>x.recommendation?.strength==='HALT').length;
 $('#summary').innerHTML=metric('<span class="en">Fixtures</span><span class="es">Partidos</span>',rows.length)+metric('<span class="en">Best available picks</span><span class="es">Mejores opciones</span>',rows.filter(x=>x.recommendation?.decision_status==='BEST_AVAILABLE').length)+metric('<span class="en">Expanded prices</span><span class="es">Cuotas ampliadas</span>',METRICS.expanded_market_policy.priced_fixtures)+metric('<span class="en">Score NLL</span><span class="es">NLL de marcador</span>',Number(METRICS.score_market_calibration.production_holdout.score_nll).toFixed(4));
 $('#model-evidence').innerHTML=`<p class="font-bold text-white"><span class="en">Validation evidence and limitations</span><span class="es">Evidencia de validación y limitaciones</span></p>
 <p class="mt-2"><span class="en">Selection rows: ${METRICS.calibration.selection_rows}; untouched holdout: ${METRICS.calibration.holdout_rows}; Brier: ${Number(METRICS.calibration.holdout_brier).toFixed(4)}; log loss: ${Number(METRICS.calibration.holdout_log_loss).toFixed(4)}. Uniform baselines are 0.6667 Brier and 1.0986 log loss.</span><span class="es">Filas de selección: ${METRICS.calibration.selection_rows}; holdout intacto: ${METRICS.calibration.holdout_rows}; Brier: ${Number(METRICS.calibration.holdout_brier).toFixed(4)}; log loss: ${Number(METRICS.calibration.holdout_log_loss).toFixed(4)}. Las bases uniformes son 0,6667 Brier y 1,0986 log loss.</span></p>
 <p class="mt-2"><span class="en">Score holdout: NLL ${Number(METRICS.score_market_calibration.production_holdout.score_nll).toFixed(4)}, Over 2.5 Brier ${Number(METRICS.score_market_calibration.production_holdout.over_2_5_brier).toFixed(4)}, BTTS Brier ${Number(METRICS.score_market_calibration.production_holdout.btts_brier).toFixed(4)}. Dixon–Coles remains a shadow model because its paired-bootstrap confidence interval crosses zero.</span><span class="es">Holdout de goles: NLL ${Number(METRICS.score_market_calibration.production_holdout.score_nll).toFixed(4)}, Brier Más de 2,5 ${Number(METRICS.score_market_calibration.production_holdout.over_2_5_brier).toFixed(4)}, Brier ambos marcan ${Number(METRICS.score_market_calibration.production_holdout.btts_brier).toFixed(4)}. Dixon–Coles sigue como modelo sombra porque su intervalo bootstrap pareado cruza cero.</span></p>
 <p class="mt-2"><span class="en">Model championship: ${METRICS.model_championship.registered_variants.length} registered variants. Strict nested outer folds selected ${escapeHtml(METRICS.model_championship.champion)}. No structural model or stack beat that market proxy across outer mean log loss, so added complexity is rejected on the available evidence.</span><span class="es">Campeonato de modelos: ${METRICS.model_championship.registered_variants.length} variantes registradas. Los pliegues externos anidados estrictos eligieron ${escapeHtml(METRICS.model_championship.champion)}. Ningún modelo estructural ni combinación superó a ese proxy de mercado en pérdida logarítmica externa promedio, por lo que se rechaza complejidad adicional con la evidencia disponible.</span></p>
 <p class="mt-2"><span class="en">Deep-learning research track: ${escapeHtml(METRICS.model_championship.deep_learning_research?.candidate_families?.map(x=>x.name).join(' · ')||'registered but gated')}. These variants need the published promotion gate before production use: more timestamped fixtures, enough repeated temporal edges per team, nested walk-forward selection, calibration checks, and closing-line profitability validation.</span><span class="es">Línea de investigación deep learning: ${escapeHtml(METRICS.model_championship.deep_learning_research?.candidate_families?.map(x=>x.name).join(' · ')||'registrada pero limitada')}. Estas variantes requieren la puerta de promoción publicada antes de usarse en producción: más partidos con marca de tiempo, suficientes aristas temporales repetidas por equipo, selección walk-forward anidada, calibración y validación de rentabilidad con líneas de cierre.</span></p>
 <p class="mt-2"><span class="en">Historical odds inventory: ${METRICS.historical_closing_odds.events} events and ${METRICS.historical_closing_odds.rows} selection rows retained as timestamp-unknown proxies; primary timestamp-verified validation rows: ${METRICS.historical_closing_odds.primary_validation_rows}.</span><span class="es">Inventario histórico de cuotas: ${METRICS.historical_closing_odds.events} eventos y ${METRICS.historical_closing_odds.rows} filas de selecciones conservadas como proxies sin hora verificable; filas primarias verificadas por tiempo: ${METRICS.historical_closing_odds.primary_validation_rows}.</span></p>
 <p class="mt-2 text-amber-200"><span class="en">The report ranks up to four distinct sourced picks per match. Genuine timestamped historical closes are not yet available, so profitability, CLV, ROI and staking tiers remain unvalidated.</span><span class="es">El informe ordena hasta cuatro opciones distintas con fuente por partido. Aún no hay cierres históricos genuinos con marca de tiempo, por lo que rentabilidad, CLV, ROI y niveles de apuesta siguen sin validarse.</span></p>`;
}
function renderBankrollPlan(){
 const plan=DATA.bankroll_simulation;
 $('#bankroll-plan').innerHTML=['Betano','Betsson'].map(app=>{
  const item=plan.apps[app];
  return `<article class="rounded-3xl border border-cyan-900/70 bg-slate-900 p-5">
   <div class="flex items-start justify-between gap-4">
    <div><h2 class="text-xl font-black text-white">${app} · S/${Number(plan.budget_per_app).toFixed(2)}</h2>
    <p class="mt-1 text-sm text-slate-400"><span class="en">${item.fixture_count} sourced match picks in this app</span><span class="es">${item.fixture_count} selecciones con fuente en esta app</span></p></div>
    <span class="rounded-full border border-amber-700 px-3 py-1 text-xs text-amber-200"><span class="en">Simulation</span><span class="es">Simulación</span></span>
   </div>
   <div class="mt-4 grid grid-cols-3 gap-2 text-center">
    ${metric('<span class="en">Allocated</span><span class="es">Asignado</span>',`S/${Number(item.total_stake).toFixed(2)}`)}
    ${metric('<span class="en">Unvalidated model net</span><span class="es">Neto del modelo no validado</span>',`S/${Number(item.model_estimated_net).toFixed(2)}`)}
    ${metric('<span class="en">All-win gross</span><span class="es">Bruto si todas ganan</span>',`S/${Number(item.gross_return_if_every_pick_fully_wins).toFixed(2)}`)}
   </div>
   <p class="mt-3 text-xs text-amber-200"><span class="en">${escapeHtml(plan.warning.en)}</span><span class="es">${escapeHtml(plan.warning.es)}</span></p>
   <p class="mt-2 text-xs text-slate-400"><span class="en">${escapeHtml(item.risk_note.en)}</span><span class="es">${escapeHtml(item.risk_note.es)}</span></p>
  </article>`;
 }).join('');
}
const pct=p=>`${(Number(p)*100).toFixed(1)}%`;
const odds=o=>Number(o).toFixed(2);
const safePct=p=>Number.isFinite(Number(p))?pct(p):'n/a';
const safeOdds=o=>Number.isFinite(Number(o))?odds(o):'n/a';
function marketLabel(row){
 const labels={
  '1x2':['1X2','1X2'],'total_goals':['Total goals','Total de goles'],
  btts:['BTTS','Ambos marcan'],asian_handicap:['Asian handicap','Hándicap asiático'],
  double_chance:['Double chance','Doble oportunidad'],
  handicap_total_combo:['Handicap + total','Hándicap + total']
 };
 const value=labels[row.market_family]||[row.market_family,row.market_family];
 return `<span class="en">${value[0]}</span><span class="es">${value[1]}</span>`;
}
function safeList(value){return Array.isArray(value)?value:[]}
function safeUrlHost(url){
 try{return new URL(url).hostname}catch(_error){return null}
}
function jsonLeaves(value,pointer=''){
 if(Array.isArray(value))return value.flatMap((item,index)=>jsonLeaves(item,`${pointer}/${index}`));
 if(value&&typeof value==='object')return Object.keys(value).sort().flatMap(key=>jsonLeaves(value[key],`${pointer}/${key.replaceAll('~','~0').replaceAll('/','~1')}`));
 return [pointer||'/'];
}
function placeTip(tip){
 const popup=tip.querySelector(':scope > span');if(!popup)return;
 popup.style.display='block';popup.style.visibility='hidden';
 popup.style.left='8px';popup.style.top='8px';
 const trigger=tip.getBoundingClientRect(),box=popup.getBoundingClientRect(),gap=8,pad=8;
 const left=Math.max(pad,Math.min(window.innerWidth-box.width-pad,trigger.left+trigger.width/2-box.width/2));
 const above=trigger.top-box.height-gap;
 const top=above>=pad?above:Math.min(window.innerHeight-box.height-pad,trigger.bottom+gap);
 popup.style.left=`${Math.round(left)}px`;popup.style.top=`${Math.max(pad,Math.round(top))}px`;
 popup.style.visibility='visible';tip.setAttribute('aria-expanded','true');
}
function hideTip(tip){
 const popup=tip.querySelector(':scope > span');if(!popup)return;
 popup.style.removeProperty('display');popup.style.removeProperty('visibility');
 popup.style.removeProperty('left');popup.style.removeProperty('top');
 tip.setAttribute('aria-expanded','false');
}
function bindTips(){
 document.querySelectorAll('.tip:not([data-tip-bound])').forEach(tip=>{
  tip.dataset.tipBound='true';tip.setAttribute('aria-expanded','false');
  tip.addEventListener('mouseenter',()=>placeTip(tip));
  tip.addEventListener('mouseleave',()=>hideTip(tip));
  tip.addEventListener('focus',()=>placeTip(tip));
  tip.addEventListener('blur',()=>hideTip(tip));
 });
}
function parseCsv(text){
 const rows=[];let row=[],field='',quoted=false;
 for(let i=0;i<text.length;i++){
  const c=text[i],next=text[i+1];
  if(quoted&&c==='"'&&next==='"'){field+='"';i++;continue}
  if(c==='"'){quoted=!quoted;continue}
  if(!quoted&&c===','){row.push(field);field='';continue}
  if(!quoted&&(c==='\n'||c==='\r')){
   if(c==='\r'&&next==='\n')i++;
   row.push(field);field='';if(row.some(x=>x!==''))rows.push(row);row=[];continue
  }
  field+=c;
 }
 if(field||row.length){row.push(field);rows.push(row)}
 const header=rows.shift()||[];
 return rows.map(values=>Object.fromEntries(header.map((key,index)=>[key,values[index]??''])));
}
function card(row,index){
 const r=row.recommendation;
 const topRecommendations=row.top_recommendations||[];
 const ptr=`/predictions/${index}`;
 const help=row.metric_explanations||{};
 const strength=r?.strength||'PASS';
 const rec=r?`${escapeHtml(r.selection_original)} ${r.line?`(${escapeHtml(r.line)})`:''} @ ${Number(r.odds).toFixed(2)}`:'No supported price / Sin cuota compatible';
 const budget=r?.budget_simulation;
 const common=row.common_markets||{};
 const over25=safeList(common.totals).find(x=>x.line===2.5)||{};
 const ah=safeList(common.asian_handicap).find(x=>x.home_line===-0.5)||{};
 const comparisons=safeList(row.market_comparisons).slice(0,8).map((m,i)=>`<tr class="border-t border-slate-800">
   <td class="py-2 pr-2">${i+1}. ${marketLabel(m)}</td>
   <td class="py-2 pr-2">${escapeHtml(m.selection_original)}${m.handicap_line!==null&&m.handicap_line!==undefined?` (${m.handicap_line>0?'+':''}${m.handicap_line})`:''}</td>
   <td class="py-2 pr-2 text-right">${odds(m.odds)}</td><td class="py-2 pr-2 text-right">${pct(m.p_win)}</td>
   <td class="py-2 pr-2 text-right">${odds(m.fair_odds)}</td><td class="py-2 text-right ${m.ev_pct>=0?'text-emerald-300':'text-rose-300'}">${Number(m.ev_pct).toFixed(1)}%</td>
  </tr>`).join('');
 const rankedRecommendations=topRecommendations.map((item,i)=>`<div class="rounded-xl border ${i===0?'border-cyan-700 bg-cyan-950/20':'border-slate-800 bg-slate-950/70'} p-3" data-recommendation-rank="${item.rank}">
   <div class="flex items-start justify-between gap-3"><div><div class="text-xs text-slate-500"><span class="en">Rank</span><span class="es">Rango</span> ${item.rank} • ${escapeHtml(item.app)} • <span class="en">risk</span><span class="es">riesgo</span> ${escapeHtml(item.risk_grade)}</div>
   <div class="mt-1 font-semibold text-white">${escapeHtml(item.selection_original)} ${item.line?`(${escapeHtml(item.line)})`:''} @ ${Number(item.odds).toFixed(2)}</div></div>
   <span class="rounded-full border px-2 py-1 text-[10px] ${strengthColor(item.strength)}">${escapeHtml(item.strength)}</span></div>
   <div class="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
    <div><span class="en">Decision EV</span><span class="es">EV decisión</span> <b>${Number(item.ev_pct).toFixed(1)}%</b></div>
    <div><span class="en">Stress</span><span class="es">Estrés</span> <b>${Number(item.stressed_ev_pct).toFixed(1)}%</b></div>
    <div><span class="en">Probability</span><span class="es">Probabilidad</span> <b>${pct(item.p_win)}</b></div>
    <div><span class="en">Fair threshold</span><span class="es">Umbral justo</span> <b>${odds(item.fair_odds)}</b></div>
   </div>
   <div class="mt-2 text-xs ${item.price_gate_status==='at_or_above_model_fair_price'?'text-emerald-300':'text-amber-200'}"><span class="en">${item.price_gate_status==='at_or_above_model_fair_price'?'Saved price meets the model fair threshold.':'Saved price is below the model fair threshold.'}</span><span class="es">${item.price_gate_status==='at_or_above_model_fair_price'?'La cuota guardada alcanza el umbral justo.':'La cuota guardada está debajo del umbral justo.'}</span></div>
   <div class="mt-2 text-xs text-slate-400">${escapeHtml(item.market_original)} • ${escapeHtml(item.source_image)} • <span class="en">utility</span><span class="es">utilidad</span> ${Number(item.recommendation_utility).toFixed(1)}</div>
   <details class="mt-2 text-xs"><summary class="cursor-pointer text-cyan-300"><span class="en">Why ranked, uncertainty and app steps</span><span class="es">Motivo del rango, incertidumbre y pasos en la app</span></summary>
    <p class="en mt-2">${escapeHtml(item.why_ranked.en)}</p><p class="es mt-2">${escapeHtml(item.why_ranked.es)}</p>
    <ul class="en mt-2 list-disc pl-5">${item.uncertainty.en.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>
    <ul class="es mt-2 list-disc pl-5">${item.uncertainty.es.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>
    <ol class="en mt-2 list-decimal pl-5 space-y-1">${item.steps.en.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ol>
    <ol class="es mt-2 list-decimal pl-5 space-y-1">${item.steps.es.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ol>
   </details>
  </div>`).join('');
 const sources=(row.research?.source_urls||[]).map(u=>{
  const host=safeUrlHost(u);
  return host?`<a class="text-cyan-400 hover:underline break-all" href="${escapeHtml(u)}" target="_blank" rel="noopener">${escapeHtml(host)}</a>`:`<span class="text-amber-200">${escapeHtml(u)}</span>`;
 }).join(' · ');
 const riskEn=safeList(row.risk_notes?.en);
 const riskEs=safeList(row.risk_notes?.es);
 return `<article class="card-anchor bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden" data-fixture-id="${escapeHtml(row.fixture_id)}" data-date="${row.kickoff_lima.slice(0,10)}" data-strength="${strength}">
   <header class="p-5 border-b border-slate-800 flex justify-between gap-4">
    <div><div class="text-xs text-slate-500" data-json-pointer="${ptr}/kickoff_lima">${escapeHtml(row.kickoff_lima.replace('T',' ').slice(0,16))} • <span class="en">Group</span><span class="es">Grupo</span> <span data-json-pointer="${ptr}/group">${escapeHtml(row.group)}</span></div>
    <h2 class="mt-1 text-xl font-black text-white"><span class="en" data-json-pointer="${ptr}/fixture/en">${escapeHtml(row.fixture.en)}</span><span class="es" data-json-pointer="${ptr}/fixture/es">${escapeHtml(row.fixture.es)}</span></h2></div>
    <span class="h-fit rounded-full border px-3 py-1 text-xs font-bold ${strengthColor(strength)}">${strength}</span>
   </header>
   <div class="p-5">
    <div class="grid grid-cols-3 gap-2 text-center">
     <div data-json-pointer="${ptr}/probabilities/team_a_win">${metric('1',`${(row.probabilities.team_a_win*100).toFixed(1)}%`,help.team_a_win)}</div>
     <div data-json-pointer="${ptr}/probabilities/draw">${metric('X',`${(row.probabilities.draw*100).toFixed(1)}%`,help.draw)}</div>
     <div data-json-pointer="${ptr}/probabilities/team_b_win">${metric('2',`${(row.probabilities.team_b_win*100).toFixed(1)}%`,help.team_b_win)}</div>
    </div>
    <div class="mt-3 rounded-xl border ${row.freshness_status==='current_snapshot'?'border-emerald-800 bg-emerald-950/30':'border-amber-800 bg-amber-950/30'} p-3 text-xs">
      ${row.freshness_status==='current_snapshot'
        ?'<span class="en">Current snapshot at the documented cutoff.</span><span class="es">Instantánea vigente al corte documentado.</span>'
        :'<span class="en">Conditional forecast: rerun after intervening matches and before using updated lineups or odds.</span><span class="es">Pronóstico condicional: recalcular después de partidos intermedios y antes de usar alineaciones o cuotas actualizadas.</span>'}
    </div>
    <div class="mt-3 text-xs text-emerald-300"><span class="en">Field-level subagent audit: PASS</span><span class="es">Auditoría de subagentes por campo: PASS</span> • ${AUDIT_COUNT} <span class="en">manifest datapoints</span><span class="es">datos auditados</span></div>
    <div class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2 text-center">
      <div data-json-pointer="${ptr}/expected_goals/team_a">${metric('<span class="en">Expected goals 1</span><span class="es">Goles esperados 1</span>',Number(row.expected_goals.team_a).toFixed(2),help.expected_goals_team_a)}</div>
      <div data-json-pointer="${ptr}/expected_goals/team_b">${metric('<span class="en">Expected goals 2</span><span class="es">Goles esperados 2</span>',Number(row.expected_goals.team_b).toFixed(2),help.expected_goals_team_b)}</div>
      <div data-json-pointer="${ptr}/common_markets/totals/2/over_probability">${metric('<span class="en">Over 2.5</span><span class="es">Más de 2,5</span>',`${safePct(over25.over_probability)} · ${safeOdds(over25.over_fair_odds)}`,help.over_2_5)}</div>
      <div data-json-pointer="${ptr}/common_markets/btts/yes_probability">${metric('BTTS Yes / Sí',`${safePct(common.btts?.yes_probability)} · ${safeOdds(common.btts?.yes_fair_odds)}`,help.btts_yes)}</div>
    </div>
    <div class="mt-3 rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm">
      <div class="font-semibold text-white"><span class="en">Common model markets — probabilities and fair odds</span><span class="es">Mercados comunes del modelo — probabilidades y cuotas justas</span></div>
      <div class="mt-2 grid sm:grid-cols-3 gap-2 text-center">
        ${metric('<span class="en">Under 2.5</span><span class="es">Menos de 2,5</span>',`${safePct(over25.under_probability)} · ${safeOdds(over25.under_fair_odds)}`,help.under_2_5)}
        ${metric('BTTS No',`${safePct(common.btts?.no_probability)} · ${safeOdds(common.btts?.no_fair_odds)}`,help.btts_no)}
        ${metric('<span class="en">Home -0.5 AH</span><span class="es">Local -0,5 HA</span>',`${safePct(ah.home_probability)} · ${safeOdds(ah.home_fair_odds)}`,help.home_minus_0_5)}
      </div>
      <p class="mt-2 text-xs text-amber-200"><span class="en">Model-derived and experimental. A fair odd is not an app quote or betting instruction.</span><span class="es">Derivado del modelo y experimental. Una cuota justa no es una cuota de app ni una instrucción de apuesta.</span></p>
    </div>
    <div class="mt-4 rounded-2xl border border-slate-700 bg-slate-950 p-4">
      <div class="text-xs text-slate-500"><span class="en">Best available recommendation — risk grade ${r?.risk_grade||'D'}</span><span class="es">Mejor recomendación disponible — riesgo ${r?.risk_grade||'D'}</span></div>
      <div class="mt-1 font-bold text-white" data-json-pointer="${ptr}/recommendation/selection_original">${rec}</div>
      ${r?`<div class="mt-2 grid grid-cols-3 gap-2 text-sm"><div data-json-pointer="${ptr}/recommendation/ev_pct"><span class="en">Decision EV</span><span class="es">EV decisión</span> <b>${r.ev_pct.toFixed(1)}%</b></div><div data-json-pointer="${ptr}/recommendation/stressed_ev_pct"><span class="en">Stress</span><span class="es">Estrés</span> <b>${r.stressed_ev_pct.toFixed(1)}%</b></div><div data-json-pointer="${ptr}/recommendation/p_win"><span class="en">Decision probability</span><span class="es">Probabilidad decisión</span> <b>${pct(r.p_win)}</b></div></div>
      <div class="mt-2 text-xs text-slate-400">${escapeHtml(r.app)} • ${escapeHtml(r.market_original)} • ${escapeHtml(r.source_image)} • <span class="en">fair</span><span class="es">justa</span> ${odds(r.fair_odds)}</div>
      <div class="mt-2 text-xs text-amber-200"><span class="en">${r.selection_reason==='all_model_edges_halted_select_highest_market_probability'?'All model edges were HALT; selected the highest market-probability fallback.':'Selected by uncertainty-adjusted expected-profit utility.'} Profitability is not historically validated.</span><span class="es">${r.selection_reason==='all_model_edges_halted_select_highest_market_probability'?'Todas las ventajas fueron HALT; se eligió la alternativa con mayor probabilidad de mercado.':'Elegida por utilidad de beneficio esperado ajustada por incertidumbre.'} La rentabilidad no está validada históricamente.</span></div>`:''}
    </div>
    <details class="mt-4 rounded-2xl border border-cyan-900 p-4" open>
      <summary class="cursor-pointer font-semibold text-cyan-200"><span class="en">Top ranked sourced recommendations</span><span class="es">Recomendaciones con fuente mejor clasificadas</span> (${topRecommendations.length}/4)</summary>
      <div class="mt-3 grid gap-3">${rankedRecommendations}</div>
      ${topRecommendations.length<4?`<p class="mt-3 text-xs text-amber-200"><span class="en">Only ${topRecommendations.length} economically distinct complete sourced events were available. A fourth bet was not invented from duplicate app prices or unsupported markets.</span><span class="es">Solo hubo ${topRecommendations.length} eventos completos, distintos y con fuente. No se inventó una cuarta apuesta usando cuotas duplicadas o mercados no compatibles.</span></p>`:''}
      <p class="mt-3 text-xs text-amber-200"><span class="en">Ranking means best relative utility among available sourced prices, not proven profit. Utility can be negative even when displayed EV is non-negative because it subtracts model-market disagreement, market-family uncertainty, and HALT penalties. Negative EV and HALT alternatives remain visibly labeled.</span><span class="es">El ranking significa mejor utilidad relativa entre cuotas disponibles, no beneficio probado. La utilidad puede ser negativa aunque el EV mostrado no lo sea porque resta desacuerdo modelo-mercado, incertidumbre de la familia y penalizaciones HALT. Alternativas con EV negativo y HALT permanecen claramente marcadas.</span></p>
    </details>
    ${budget?`<details class="mt-4 rounded-2xl border border-cyan-900 bg-cyan-950/20 p-4">
      <summary class="cursor-pointer font-semibold text-cyan-200"><span class="en">S/100 app-budget simulation: stake S/${Number(budget.stake).toFixed(2)} in ${escapeHtml(r.app)}</span><span class="es">Simulación de S/100 en la app: monto S/${Number(budget.stake).toFixed(2)} en ${escapeHtml(r.app)}</span></summary>
      <div class="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-center">
       ${metric('<span class="en">Stake</span><span class="es">Monto</span>',`S/${Number(budget.stake).toFixed(2)}`)}
       ${metric('<span class="en">Saved odd</span><span class="es">Cuota guardada</span>',Number(budget.screenshot_odds).toFixed(2))}
       ${metric('<span class="en">Model fair threshold</span><span class="es">Umbral justo</span>',Number(budget.minimum_model_fair_odds).toFixed(2))}
       ${metric('<span class="en">Full-win gross</span><span class="es">Bruto si gana</span>',`S/${Number(budget.gross_return_if_full_win).toFixed(2)}`)}
      </div>
      <div class="mt-3 rounded-xl border ${budget.price_gate_status==='at_or_above_model_fair_price'?'border-emerald-800 bg-emerald-950/30':'border-red-800 bg-red-950/30'} p-3 text-xs">
       ${budget.price_gate_status==='at_or_above_model_fair_price'
        ?'<span class="en">Saved price is at or above the model fair threshold. Still re-check the live price and news.</span><span class="es">La cuota guardada está en o sobre el umbral justo. Revisa igualmente cuota y noticias actuales.</span>'
        :'<span class="en">Saved price is below the model fair threshold. This stake exists only because the requested simulation forces every match; disciplined real-money use would pause here.</span><span class="es">La cuota guardada está debajo del umbral justo. Este monto existe solo porque la simulación solicitada fuerza todos los partidos; un uso disciplinado con dinero real se detendría aquí.</span>'}
      </div>
      <h3 class="mt-4 font-bold text-white"><span class="en">Step by step in ${escapeHtml(r.app)}</span><span class="es">Paso a paso en ${escapeHtml(r.app)}</span></h3>
      <ol class="en mt-2 list-decimal pl-5 space-y-2 text-sm text-slate-300">${budget.steps.en.map(step=>`<li>${escapeHtml(step)}</li>`).join('')}</ol>
      <ol class="es mt-2 list-decimal pl-5 space-y-2 text-sm text-slate-300">${budget.steps.es.map(step=>`<li>${escapeHtml(step)}</li>`).join('')}</ol>
      <p class="mt-3 text-xs text-amber-200"><span class="en">${escapeHtml(budget.warning.en)}</span><span class="es">${escapeHtml(budget.warning.es)}</span></p>
    </details>`:''}
    <details class="mt-4 rounded-2xl border border-slate-800 p-4">
      <summary class="cursor-pointer font-semibold"><span class="en">Ranked screenshot market comparisons</span><span class="es">Comparaciones de cuotas de capturas ordenadas</span> (${row.market_comparisons.length})</summary>
      ${comparisons?`<div class="overflow-x-auto mt-3"><table class="w-full min-w-[680px] text-xs text-slate-300"><thead><tr class="text-slate-500 text-left"><th class="pb-2"><span class="en">Market</span><span class="es">Mercado</span></th><th class="pb-2"><span class="en">Selection</span><span class="es">Selección</span></th><th class="pb-2 text-right"><span class="en">App odd</span><span class="es">Cuota app</span></th><th class="pb-2 text-right"><span class="en">Win eq.</span><span class="es">Victoria eq.</span></th><th class="pb-2 text-right"><span class="en">Fair</span><span class="es">Justa</span></th><th class="pb-2 text-right">EV</th></tr></thead><tbody>${comparisons}</tbody></table></div>
      <p class="mt-2 text-xs text-amber-200"><span class="en">Ranked for audit inspection only; all rows are experimental and non-actionable.</span><span class="es">Ordenado solo para inspección de auditoría; todas las filas son experimentales y no accionables.</span></p>`
      :`<p class="mt-3 text-sm text-slate-400"><span class="en">No complete expanded screenshot market was available. Model probabilities above remain available without fabricated prices or EV.</span><span class="es">No hubo un mercado ampliado completo en capturas. Las probabilidades del modelo siguen disponibles sin inventar cuotas ni EV.</span></p>`}
    </details>
    <details class="mt-4 rounded-2xl border border-slate-800 p-4">
      <summary class="cursor-pointer font-semibold"><span class="en">Research, risks and ELI5</span><span class="es">Investigación, riesgos y ELI5</span></summary>
      <div class="mt-3 space-y-3 text-sm text-slate-300">
        <div class="en">
          <p><b>Team news:</b> ${escapeHtml(row.research?.team_news||'Unavailable')}</p>
          <p><b>Injuries/suspensions:</b> ${escapeHtml(row.research?.injuries_suspensions||'Unavailable')}</p>
          <p><b>Motivation:</b> ${escapeHtml(row.research?.motivation_group_state||'Unavailable')}</p>
        </div>
        <div class="es"><p><b>Notas OSINT:</b> Las notas originales se conservaron en inglés para no introducir una traducción no verificada. Consulta las fuentes enlazadas y el CSV de investigación para el texto exacto.</p></div>
        <div class="en"><ul class="list-disc pl-5">${(riskEn.length?riskEn:['Risk notes unavailable in this JSON row; verify source files before use.']).map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul></div>
        <div class="es"><ul class="list-disc pl-5">${(riskEs.length?riskEs:['Notas de riesgo no disponibles en esta fila JSON; verifica los archivos fuente antes de usar.']).map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul></div>
        <p><b>ELI5:</b> <span class="en">This is the model's best available choice among the sourced prices, after shrinking toward the market and stress-testing assumptions. It can still lose; re-check the exact price and current team news.</span><span class="es">Esta es la mejor opción disponible del modelo entre las cuotas con fuente, después de acercarse al mercado y probar escenarios de estrés. Puede perder; revisa la cuota exacta y las noticias actuales.</span></p>
        <p class="text-xs">${sources}</p>
      </div>
    </details>
   </div>
 </article>`;
}
function applyFilters(){
 if(!APP_READY)return;
 const d=$('#date-filter').value,s=$('#strength-filter').value;
 document.querySelectorAll('#cards article').forEach(c=>c.classList.toggle('hidden',(d&&c.dataset.date!==d)||(s&&c.dataset.strength!==s)));
}
async function load(){
 try{
  const [response,metricsResponse,auditResponse]=await Promise.all([
    fetch('wc_june22_27_predictions.json',{cache:'no-store'}),
    fetch('wc_june22_27_model_metrics.json',{cache:'no-store'}),
    fetch('wc_june22_27_datapoint_audit.csv',{cache:'no-store'})
  ]);
  if(!response.ok)throw new Error(`predictions.json HTTP ${response.status}`);
  if(!metricsResponse.ok)throw new Error(`metrics.json HTTP ${metricsResponse.status}`);
  if(!auditResponse.ok)throw new Error(`audit.csv HTTP ${auditResponse.status}`);
  DATA=await response.json(); METRICS=await metricsResponse.json();
  if(!DATA||!DATA.batch||!Array.isArray(DATA.predictions))throw new Error('Predictions JSON schema is invalid');
  if(!METRICS||!METRICS.calibration||!METRICS.score_market_calibration)throw new Error('Metrics JSON schema is invalid');
  const auditText=await auditResponse.text();
  const auditRows=parseCsv(auditText);
  if(!auditRows.length||auditRows.some(row=>row.final_status!=='PASS'))throw new Error('Datapoint audit is incomplete or blocked');
  const expectedPaths=new Set([
   ...jsonLeaves(DATA).map(pointer=>`wc_june22_27_predictions.json:${pointer}`),
   ...jsonLeaves(METRICS).map(pointer=>`wc_june22_27_model_metrics.json:${pointer}`)
  ]);
  const auditedPaths=new Set(auditRows.map(row=>`${row.output_artifact}:${row.json_pointer}`));
  if(expectedPaths.size!==auditedPaths.size||[...expectedPaths].some(path=>!auditedPaths.has(path)))throw new Error('Datapoint audit does not exactly cover current JSON leaves');
  AUDIT_COUNT=auditRows.length;
  if(DATA.batch.fixture_count!==32||DATA.predictions.length!==32)throw new Error('Expected exactly 32 predictions');
  const ids=new Set(DATA.predictions.map(x=>x.fixture_id)); if(ids.size!==32)throw new Error('Duplicate fixture IDs');
  setText('#last-updated',DATA.generated_at||'unknown');
  setText('#site-version',DATA.model?.version||METRICS.version||DATA.schema_version||'unknown');
  const build=$('#build-sha'); if(build&&build.textContent.length>12)build.textContent=build.textContent.slice(0,12);
  renderSummary(DATA.predictions);
  renderBankrollPlan();
  setHtml('#cards',DATA.predictions.map(card).join(''));
  bindTips();
  [...new Set(DATA.predictions.map(x=>x.kickoff_lima.slice(0,10)))].forEach(d=>$('#date-filter').insertAdjacentHTML('beforeend',`<option value="${d}">${d}</option>`));
  ['#date-filter','#strength-filter'].forEach(selector=>{const el=$(selector);if(el)el.disabled=false;});
  const loading=$('#loading-shell'); if(loading)loading.classList.add('hidden');
  APP_READY=true;
  setHtml('#status','<span class="en">Verified JSON loaded</span><span class="es">JSON verificado cargado</span>');
 }catch(error){
  showError(error.message);
 }
}
function boot(){
 const lang=$('#lang'); if(lang)lang.addEventListener('click',()=>{const es=document.body.classList.contains('lang-es');document.body.classList.toggle('lang-es',!es);document.body.classList.toggle('lang-en',es);lang.textContent=es?'ES':'EN';document.documentElement.lang=es?'en':'es';});
 const date=$('#date-filter'),strength=$('#strength-filter');
 if(date)date.addEventListener('change',applyFilters); if(strength)strength.addEventListener('change',applyFilters);
 bindTips();
 load();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
window.addEventListener('error',event=>{if(!APP_READY)showError(event.message||'Unexpected startup error')});
</script>
</body></html>
"""


def main() -> None:
    if not AUDIT.exists():
        raise FileNotFoundError(f"Audit manifest not found: {AUDIT}")
    audit_hash = hashlib.sha256(AUDIT.read_bytes()).hexdigest()
    OUT.write_text(HTML.replace("__AUDIT_SHA__", audit_hash), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
