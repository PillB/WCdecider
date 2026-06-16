#!/usr/bin/env python3
"""Apply bilingual EN/ES fixes to wc_june16_2026_report.html."""

from pathlib import Path

REPORT = Path(__file__).parent.parent / "wc_june16_2026_report.html"

REPLACEMENTS = [
    # Header subtitle + badges
    (
        '<p class="text-slate-400 mt-1">Backtested • Finetuned • Subagent-validated • HTML report with real-time data</p>',
        '<p class="text-slate-400 mt-1"><span class="en">Backtested • Finetuned • Subagent-validated • HTML report with real-time data</span><span class="es">Backtesteado • Ajustado • Validado por subagentes • Reporte HTML con datos en tiempo real</span></p>',
    ),
    (
        '<span class="font-medium">All numbers from executed wc_model_v3.py + subagents</span>',
        '<span class="font-medium"><span class="en">All numbers from executed wc_model_v3.py + subagents</span><span class="es">Todos los números del modelo ejecutado wc_model_v3.py + subagentes</span></span>',
    ),
    (
        '<div>AGENT.md v3.1 + Rules 21-23 • Model v3.1+finetunes</div>',
        '<div><span class="en">AGENT.md v3.1 + Rules 21-23 • Model v3.1+finetunes</span><span class="es">AGENT.md v3.1 + Reglas 21-23 • Modelo v3.1+ajustes</span></div>',
    ),
    (
        '<div>Lima, Peru • 2026-06-15</div>',
        '<div><span class="en">Lima, Peru • 2026-06-15</span><span class="es">Lima, Perú • 2026-06-15</span></div>',
    ),
    # Executive summary fragments
    (
        'boost if HALT drilldown passes (+33% raw but high joint variance).',
        '<span class="en">boost if HALT drilldown passes (+33% raw but high joint variance).</span><span class="es">boost si el drilldown HALT pasa (+33% raw pero alta varianza conjunta).</span>',
    ),
    (
        '(+12% SPEC), cleared',
        '<span class="en">(+12% SPEC), cleared</span><span class="es">(+12% SPEC), despejado</span>',
    ),
    (
        'joint low).',
        '<span class="en">joint low).</span><span class="es">conjunta baja).</span>',
    ),
    # Diagram section
    (
        '<span class="font-semibold text-lg">Analytical Framework &amp; Modeling Workflow Visualization</span>',
        '<span class="font-semibold text-lg"><span class="en">Analytical Framework &amp; Modeling Workflow Visualization</span><span class="es">Marco Analítico y Visualización del Flujo de Modelado</span></span>',
    ),
    (
        '<span class="text-xs ml-2 px-2 py-0.5 bg-indigo-900 text-indigo-300 rounded">RIGOR • ELEGANCE • SOPHISTICATION</span>',
        '<span class="text-xs ml-2 px-2 py-0.5 bg-indigo-900 text-indigo-300 rounded"><span class="en">RIGOR • ELEGANCE • SOPHISTICATION</span><span class="es">RIGOR • ELEGANCIA • SOFISTICACIÓN</span></span>',
    ),
    (
        '<p class="text-sm text-slate-300 mb-4">This interactive diagram showcases the full end-to-end analytical framework. It demonstrates the rigorous, multi-layered stack of models, data flows, finetunes (Rules 21-23), ensemble weighting, sensitivities, and output pipeline. Designed for stakeholders to appreciate the validity, elegance, and sophistication of the approach (inspired by best-in-class implementations from TensorBoard graphs, Sankey flow diagrams for ensembles, layered ML architecture visuals from papers like "Visualizing Dataflow Graphs of Deep Learning Models", MLflow dashboards, and stacked ensemble diagrams in sports prediction literature).</p>',
        '<p class="text-sm text-slate-300 mb-4"><span class="en">This interactive diagram showcases the full end-to-end analytical framework. It demonstrates the rigorous, multi-layered stack of models, data flows, finetunes (Rules 21-23), ensemble weighting, sensitivities, and output pipeline. Designed for stakeholders to appreciate the validity, elegance, and sophistication of the approach (inspired by best-in-class implementations from TensorBoard graphs, Sankey flow diagrams for ensembles, layered ML architecture visuals from papers like "Visualizing Dataflow Graphs of Deep Learning Models", MLflow dashboards, and stacked ensemble diagrams in sports prediction literature).</span><span class="es">Este diagrama interactivo muestra el marco analítico completo de extremo a extremo. Demuestra la pila rigurosa y multicapa de modelos, flujos de datos, ajustes finos (Reglas 21-23), ponderación de ensemble, sensibilidades y pipeline de salida. Diseñado para que los stakeholders aprecien la validez, elegancia y sofisticación del enfoque (inspirado en implementaciones de clase mundial: gráficos TensorBoard, diagramas Sankey para ensembles, visuales de arquitectura ML en capas de papers como "Visualizing Dataflow Graphs of Deep Learning Models", dashboards MLflow y diagramas de ensemble apilado en literatura de predicción deportiva).</span></p>',
    ),
    (
        '<div class="mt-3 text-xs text-slate-400 text-center">Hover nodes in the live report (or view source) for expanded details. Weights are dynamic per v3.1 Rules 20-23 and backtest calibration. This visualization proves the multi-model rigor while remaining transparent and actionable.</div>',
        '<div class="mt-3 text-xs text-slate-400 text-center"><span class="en">Hover nodes in the live report (or view source) for expanded details. Weights are dynamic per v3.1 Rules 20-23 and backtest calibration. This visualization proves the multi-model rigor while remaining transparent and actionable.</span><span class="es">Pasa el cursor sobre los nodos en el reporte en vivo (o ver fuente) para detalles ampliados. Los pesos son dinámicos según Reglas 20-23 v3.1 y calibración de backtest. Esta visualización demuestra el rigor multi-modelo manteniéndose transparente y accionable.</span></div>',
    ),
    # Replicability header
    (
        '<span class="font-semibold text-emerald-300">Replicability &amp; Pipeline Validation (wc_replicable_pipeline.py + CSV + TXT)</span>',
        '<span class="font-semibold text-emerald-300"><span class="en">Replicability &amp; Pipeline Validation (wc_replicable_pipeline.py + CSV + TXT)</span><span class="es">Replicabilidad y Validación del Pipeline (wc_replicable_pipeline.py + CSV + TXT)</span></span>',
    ),
    (
        '<span class="font-mono"> France win 66.2% (raw 54.0%), Iraq DC 35.6% (raw p_win 13.9% / pD 27.0%), Argentina win 74.0% (raw 64.9%), Austria draw 23.2% (raw pD 30.5%).</span>',
        '<span class="font-mono"><span class="en"> France win 66.2% (raw 54.0%), Iraq DC 35.6% (raw p_win 13.9% / pD 27.0%), Argentina win 74.0% (raw 64.9%), Austria draw 23.2% (raw pD 30.5%).</span><span class="es"> Victoria Francia 66,2% (raw 54,0%), Iraq DC 35,6% (raw p_win 13,9% / pD 27,0%), Victoria Argentina 74,0% (raw 64,9%), Empate Austria 23,2% (raw pD 30,5%).</span></span>',
    ),
    # Subagents stub
    (
        '<span class="font-mono text-xs">Executable stub in wc_model_v3.py (bradley_terry_davidson_1x2).</span>',
        '<span class="font-mono text-xs"><span class="en">Executable stub in wc_model_v3.py (bradley_terry_davidson_1x2).</span><span class="es">Stub ejecutable en wc_model_v3.py (bradley_terry_davidson_1x2).</span></span>',
    ),
    # Sure bets table cells
    (
        '<td>Low (suppressed λ)</td>',
        '<td><span class="en">Low (suppressed λ)</span><span class="es">Baja (λ suprimido)</span></td>',
    ),
    (
        '<td class="font-semibold">Highest</td>',
        '<td class="font-semibold"><span class="en">Highest</span><span class="es">Más alto</span></td>',
    ),
    (
        '<td>Med-High</td>',
        '<td><span class="en">Med-High</span><span class="es">Med-Alta</span></td>',
    ),
    (
        '<td>Medium</td>',
        '<td><span class="en">Medium</span><span class="es">Media</span></td>',
    ),
    (
        '<td>High (tails)</td>',
        '<td><span class="en">High (tails)</span><span class="es">Alta (colas)</span></td>',
    ),
    (
        '<td>Med (if HALT cleared)</td>',
        '<td><span class="en">Med (if HALT cleared)</span><span class="es">Med (si HALT despejado)</span></td>',
    ),
    (
        '<td>MOD (ROBUST)</td>',
        '<td><span class="en">MOD (ROBUST)</span><span class="es">MOD (ROBUSTO)</span></td>',
    ),
    (
        '<span class="ml-2 text-xs bg-sky-900 text-sky-300 px-2 py-0.5 rounded">FRESH DATA PULLED</span>',
        '<span class="ml-2 text-xs bg-sky-900 text-sky-300 px-2 py-0.5 rounded"><span class="en">FRESH DATA PULLED</span><span class="es">DATOS FRESCOS OBTENIDOS</span></span>',
    ),
    (
        '<span class="text-xs ml-2 px-2 py-0.5 bg-emerald-900 text-emerald-400 rounded">VERIFIED</span>',
        '<span class="text-xs ml-2 px-2 py-0.5 bg-emerald-900 text-emerald-400 rounded"><span class="en">VERIFIED</span><span class="es">VERIFICADO</span></span>',
    ),
    # France match card labels
    (
        '<span class="text-xs ml-2 px-2 py-px bg-slate-800 rounded">Group I • MetLife • ~14:00 ET</span>',
        '<span class="text-xs ml-2 px-2 py-px bg-slate-800 rounded"><span class="en">Group I • MetLife • ~14:00 ET</span><span class="es">Grupo I • MetLife • ~14:00 ET</span></span>',
    ),
    (
        '<div class="text-[10px]">FRA win</div>',
        '<div class="text-[10px]"><span class="en">FRA win</span><span class="es">Victoria FRA</span></div>',
    ),
    (
        '<div class="text-[10px]">Draw</div>',
        '<div class="text-[10px]"><span class="en">Draw</span><span class="es">Empate</span></div>',
    ),
    (
        '<div class="text-[10px]">SEN win</div>',
        '<div class="text-[10px]"><span class="en">SEN win</span><span class="es">Victoria SEN</span></div>',
    ),
    # Classifications partial lines
    (
        '<div><span class="font-semibold"><span class="en">MODERATE (if cleared)</span><span class="es">MODERADO (si se despeja)</span></span>: FRA win + O3.5 boost (DC joint high EV; HALT drilldown + Pinnacle blend first per Rules 13/18).</div>',
        '<div><span class="font-semibold"><span class="en">MODERATE (if cleared)</span><span class="es">MODERADO (si se despeja)</span></span>: <span class="en">FRA win + O3.5 boost (DC joint high EV; HALT drilldown + Pinnacle blend first per Rules 13/18).</span><span class="es">Victoria FRA + O3.5 boost (EV conjunta DC alta; drilldown HALT + mezcla Pinnacle primero según Reglas 13/18).</span></div>',
    ),
    (
        '<div><span class="font-semibold text-amber-400"><span class="en">SPECULATIVE</span><span class="es">ESPECULATIVO</span></span>: AUT Draw @5.05 (+12% base, SENSITIVE); IRQ DC (high raw after uplift, cap); BEL win / Doku boost (marginal + high var).</div>',
        '<div><span class="font-semibold text-amber-400"><span class="en">SPECULATIVE</span><span class="es">ESPECULATIVO</span></span>: <span class="en">AUT Draw @5.05 (+12% base, SENSITIVE); IRQ DC (high raw after uplift, cap); BEL win / Doku boost (marginal + high var).</span><span class="es">Empate AUT @5,05 (+12% base, SENSIBLE); IRQ DC (raw alto tras uplift, tope); Victoria BEL / boost Doku (marginal + alta var).</span></div>',
    ),
    (
        '<div class="mt-3 text-xs text-slate-400">Confidence ceiling 70% (AGENT.md cap). All numbers executed or multi-sourced.</div>',
        '<div class="mt-3 text-xs text-slate-400"><span class="en">Confidence ceiling 70% (AGENT.md cap). All numbers executed or multi-sourced.</span><span class="es">Tope de confianza 70% (límite AGENT.md). Todos los números ejecutados o multi-fuente.</span></div>',
    ),
    (
        '<div class="text-xs">¼ Kelly default: f* = (p·o − 1) / (o − 1); stake = 0.25 × f* × BR. Caps (v3/Rule 20): MOD ≤ S/15–20, SPEC ≤ S/15, Pass 0. Hard rules: Never &gt;5% total matchday; no martingale/chase; 20% tournament drawdown → halve sizes. Player props/boosts extra-capped (0.5% max regardless of EV). Example on S/200 ref: small SPEC S/8–12, MOD S/15–20 on strongest (KSA Under / cleared FRA combo). <span class="text-xs text-slate-400">(Newbie: "¼ Kelly" is a safe betting size calculator — it tells you to bet only a quarter of the "full" amount the math suggests so one losing streak doesn\'t wipe you out. "Martingale" is the dangerous strategy of doubling your bet after every loss to try to break even — we never do that.)</span></div>',
        '<div class="text-xs"><span class="en">¼ Kelly default: f* = (p·o − 1) / (o − 1); stake = 0.25 × f* × BR. Caps (v3/Rule 20): MOD ≤ S/15–20, SPEC ≤ S/15, Pass 0. Hard rules: Never &gt;5% total matchday; no martingale/chase; 20% tournament drawdown → halve sizes. Player props/boosts extra-capped (0.5% max regardless of EV). Example on S/200 ref: small SPEC S/8–12, MOD S/15–20 on strongest (KSA Under / cleared FRA combo).</span><span class="es">¼ Kelly por defecto: f* = (p·o − 1) / (o − 1); stake = 0,25 × f* × BR. Topes (v3/Regla 20): MOD ≤ S/15–20, SPEC ≤ S/15, Pass 0. Reglas duras: Nunca &gt;5% total en jornada; sin martingala/persecución; drawdown 20% del torneo → reducir tamaños a la mitad. Props de jugador/boosts con tope extra (0,5% máx sin importar EV). Ejemplo en ref S/200: SPEC pequeño S/8–12, MOD S/15–20 en el más fuerte (KSA Under / combo FRA despejado).</span> <span class="text-xs text-slate-400">(<span class="en">Newbie: "¼ Kelly" is a safe betting size calculator — it tells you to bet only a quarter of the "full" amount the math suggests so one losing streak doesn\'t wipe you out. "Martingale" is the dangerous strategy of doubling your bet after every loss to try to break even — we never do that.</span><span class="es">Principiante: "¼ Kelly" es una calculadora segura de tamaño de apuesta — te dice apostar solo un cuarto del monto "completo" que sugiere la matemática para que una racha perdedora no te liquide. "Martingala" es la estrategia peligrosa de duplicar la apuesta tras cada pérdida para intentar recuperar — nunca lo hacemos.</span>)</span></div>',
    ),
    # Sources block
    (
        '''            <div class="columns-2 md:columns-3 text-[10px] leading-snug">
                Elo: eloratings.net (2026-06-15 snapshots), international-football.net/elo-ratings-table.<br>
                Lineups/injuries: ESPN, Sports Mole, RotoWire, Yahoo, Fotmob, WhoScored, L'Équipe, VG/fotball.no, Covers (~Jun 14-15).<br>
                Results (backtest): Al Jazeera, ESPN, USA Today, FOX, Flashscore, Wikipedia, Athletic (live 0-0 Spain-CV, 1-1 BEL-EGY).<br>
                Weather/venue: NWS, venue sites, Climate Central.<br>
                Sharp/model: Opta Analyst proxies, public previews, Pinnacle devigged notes via MD reports.<br>
                Academic: Dixon-Coles 1997, Karlis-Ntzoufras 2003, Snowberg-Wolfers 2010 JPE, arXiv BTD papers, xG hybrid literature.<br>
                Screenshots (odds): Workspace /Screenshots/ (IMG_7345–7392 series, Betano/Betsson, transcribed verbatim in MD4).<br>
                Prior reports/model: MD3_FINAL_REPORT.md, MD4_FINAL_REPORT.md, wc_model_v3.py (executed runs).
            </div>''',
        '''            <div class="columns-2 md:columns-3 text-[10px] leading-snug">
                <span class="en">Elo: eloratings.net (2026-06-15 snapshots), international-football.net/elo-ratings-table.<br>
                Lineups/injuries: ESPN, Sports Mole, RotoWire, Yahoo, Fotmob, WhoScored, L'Équipe, VG/fotball.no, Covers (~Jun 14-15).<br>
                Results (backtest): Al Jazeera, ESPN, USA Today, FOX, Flashscore, Wikipedia, Athletic (live 0-0 Spain-CV, 1-1 BEL-EGY).<br>
                Weather/venue: NWS, venue sites, Climate Central.<br>
                Sharp/model: Opta Analyst proxies, public previews, Pinnacle devigged notes via MD reports.<br>
                Academic: Dixon-Coles 1997, Karlis-Ntzoufras 2003, Snowberg-Wolfers 2010 JPE, arXiv BTD papers, xG hybrid literature.<br>
                Screenshots (odds): Workspace /Screenshots/ (IMG_7345–7392 series, Betano/Betsson, transcribed verbatim in MD4).<br>
                Prior reports/model: MD3_FINAL_REPORT.md, MD4_FINAL_REPORT.md, wc_model_v3.py (executed runs).</span>
                <span class="es">Elo: eloratings.net (instantáneas 2026-06-15), international-football.net/elo-ratings-table.<br>
                Alineaciones/lesiones: ESPN, Sports Mole, RotoWire, Yahoo, Fotmob, WhoScored, L'Équipe, VG/fotball.no, Covers (~14-15 Jun).<br>
                Resultados (backtest): Al Jazeera, ESPN, USA Today, FOX, Flashscore, Wikipedia, Athletic (en vivo 0-0 España-CV, 1-1 BEL-EGY).<br>
                Clima/estadio: NWS, sitios de estadios, Climate Central.<br>
                Sharp/modelo: Proxies Opta Analyst, previews públicos, notas Pinnacle devigged vía reportes MD.<br>
                Académico: Dixon-Coles 1997, Karlis-Ntzoufras 2003, Snowberg-Wolfers 2010 JPE, papers arXiv BTD, literatura híbrido xG.<br>
                Capturas (cuotas): Workspace /Screenshots/ (serie IMG_7345–7392, Betano/Betsson, transcritas literal en MD4).<br>
                Reportes/modelo previos: MD3_FINAL_REPORT.md, MD4_FINAL_REPORT.md, wc_model_v3.py (ejecuciones).</span>
            </div>''',
    ),
]

# SVG text -> id mapping for updateDiagramLang
SVG_ID_PATCHES = [
    ('<text x="110" y="95" fill="#64748b" font-size="9" text-anchor="middle">(eloratings.net +</text>',
     '<text id="d-elo-src1" x="110" y="95" fill="#64748b" font-size="9" text-anchor="middle">(eloratings.net +</text>'),
    ('<text x="110" y="107" fill="#64748b" font-size="9" text-anchor="middle">international-football.net)</text>',
     '<text id="d-elo-src2" x="110" y="107" fill="#64748b" font-size="9" text-anchor="middle">international-football.net)</text>'),
    ('<text x="110" y="118" fill="#a5b4fc" font-size="8" text-anchor="middle">Weight: Core Input</text>',
     '<text id="d-elo-w" x="110" y="118" fill="#a5b4fc" font-size="8" text-anchor="middle">Weight: Core Input</text>'),
    ('<text x="265" y="95" fill="#64748b" font-size="9" text-anchor="middle">(FBref club-level for</text>',
     '<text id="d-xg-src1" x="265" y="95" fill="#64748b" font-size="9" text-anchor="middle">(FBref club-level for</text>'),
    ('<text x="265" y="107" fill="#64748b" font-size="9" text-anchor="middle">probable XI + opp profile)</text>',
     '<text id="d-xg-src2" x="265" y="107" fill="#64748b" font-size="9" text-anchor="middle">probable XI + opp profile)</text>'),
    ('<text x="265" y="118" fill="#a5b4fc" font-size="8" text-anchor="middle">Weight: Hybrid Input</text>',
     '<text id="d-xg-w" x="265" y="118" fill="#a5b4fc" font-size="8" text-anchor="middle">Weight: Hybrid Input</text>'),
    ('<text x="420" y="95" fill="#64748b" font-size="9" text-anchor="middle">(Form, H2H, Injuries,</text>',
     '<text id="d-ctx-src1" x="420" y="95" fill="#64748b" font-size="9" text-anchor="middle">(Form, H2H, Injuries,</text>'),
    ('<text x="420" y="107" fill="#64748b" font-size="9" text-anchor="middle">Weather, Travel, Ref)</text>',
     '<text id="d-ctx-src2" x="420" y="107" fill="#64748b" font-size="9" text-anchor="middle">Weather, Travel, Ref)</text>'),
    ('<text x="420" y="118" fill="#a5b4fc" font-size="8" text-anchor="middle">Weight: Adjustment Input</text>',
     '<text id="d-ctx-w" x="420" y="118" fill="#a5b4fc" font-size="8" text-anchor="middle">Weight: Adjustment Input</text>'),
    ('<text x="575" y="95" fill="#64748b" font-size="9" text-anchor="middle">(WC openers, Euros,</text>',
     '<text id="d-hist-src1" x="575" y="95" fill="#64748b" font-size="9" text-anchor="middle">(WC openers, Euros,</text>'),
    ('<text x="575" y="107" fill="#64748b" font-size="9" text-anchor="middle">top-5 leagues for μ &amp; var)</text>',
     '<text id="d-hist-src2" x="575" y="107" fill="#64748b" font-size="9" text-anchor="middle">top-5 leagues for μ &amp; var)</text>'),
    ('<text x="575" y="118" fill="#a5b4fc" font-size="8" text-anchor="middle">Weight: Prior Input</text>',
     '<text id="d-hist-w" x="575" y="118" fill="#a5b4fc" font-size="8" text-anchor="middle">Weight: Prior Input</text>'),
    ('<text x="160" y="196" fill="#99f6e4" font-size="9" text-anchor="middle">• Two-way win prob (Elo gap)</text>',
     '<text id="d-elo-c1" x="160" y="196" fill="#99f6e4" font-size="9" text-anchor="middle">• Two-way win prob (Elo gap)</text>'),
    ('<text x="160" y="208" fill="#99f6e4" font-size="9" text-anchor="middle">• 3-way w/ draw share (closeness)</text>',
     '<text id="d-elo-c2" x="160" y="208" fill="#99f6e4" font-size="9" text-anchor="middle">• 3-way w/ draw share (closeness)</text>'),
    ('<text x="160" y="220" fill="#99f6e4" font-size="9" text-anchor="middle">• λ via tanh gap → Poisson</text>',
     '<text id="d-elo-c3" x="160" y="220" fill="#99f6e4" font-size="9" text-anchor="middle">• λ via tanh gap → Poisson</text>'),
    ('<text x="160" y="232" fill="#a5b4fc" font-size="8" text-anchor="middle">Base Weight: 30-35%</text>',
     '<text id="d-elo-cw" x="160" y="232" fill="#a5b4fc" font-size="8" text-anchor="middle">Base Weight: 30-35%</text>'),
    ('<text x="340" y="196" fill="#bfdbfe" font-size="9" text-anchor="middle">• Pairwise rating model (rA - rB)</text>',
     '<text id="d-btd-c1" x="340" y="196" fill="#bfdbfe" font-size="9" text-anchor="middle">• Pairwise rating model (rA - rB)</text>'),
    ('<text x="340" y="208" fill="#bfdbfe" font-size="9" text-anchor="middle">• BTD for explicit draw param (δ)</text>',
     '<text id="d-btd-c2" x="340" y="208" fill="#bfdbfe" font-size="9" text-anchor="middle">• BTD for explicit draw param (δ)</text>'),
    ('<text x="340" y="220" fill="#bfdbfe" font-size="9" text-anchor="middle">• Dynamic EWMA updates</text>',
     '<text id="d-btd-c3" x="340" y="220" fill="#bfdbfe" font-size="9" text-anchor="middle">• Dynamic EWMA updates</text>'),
    ('<text x="340" y="232" fill="#a5b4fc" font-size="8" text-anchor="middle">Ensemble Weight: 25%</text>',
     '<text id="d-btd-cw" x="340" y="232" fill="#a5b4fc" font-size="8" text-anchor="middle">Ensemble Weight: 25%</text>'),
    ('<text x="520" y="196" fill="#ddd6fe" font-size="9" text-anchor="middle">• Club xG/xGA proxies (FBref)</text>',
     '<text id="d-xgh-c1" x="520" y="196" fill="#ddd6fe" font-size="9" text-anchor="middle">• Club xG/xGA proxies (FBref)</text>'),
    ('<text x="520" y="208" fill="#ddd6fe" font-size="9" text-anchor="middle">• Blended w/ Elo share (0.4)</text>',
     '<text id="d-xgh-c2" x="520" y="208" fill="#ddd6fe" font-size="9" text-anchor="middle">• Blended w/ Elo share (0.4)</text>'),
    ('<text x="520" y="220" fill="#ddd6fe" font-size="9" text-anchor="middle">• Better shot-quality capture</text>',
     '<text id="d-xgh-c3" x="520" y="220" fill="#ddd6fe" font-size="9" text-anchor="middle">• Better shot-quality capture</text>'),
    ('<text x="520" y="232" fill="#a5b4fc" font-size="8" text-anchor="middle">Ensemble Weight: 20%</text>',
     '<text id="d-xgh-cw" x="520" y="232" fill="#a5b4fc" font-size="8" text-anchor="middle">Ensemble Weight: 20%</text>'),
    ('<text x="700" y="196" fill="#e2e8f0" font-size="9" text-anchor="middle">• Pinnacle devigged probs</text>',
     '<text id="d-sharp-c1" x="700" y="196" fill="#e2e8f0" font-size="9" text-anchor="middle">• Pinnacle devigged probs</text>'),
    ('<text x="700" y="208" fill="#e2e8f0" font-size="9" text-anchor="middle">• Opta / Stats Perform sims</text>',
     '<text id="d-sharp-c2" x="700" y="208" fill="#e2e8f0" font-size="9" text-anchor="middle">• Opta / Stats Perform sims</text>'),
    ('<text x="700" y="220" fill="#e2e8f0" font-size="9" text-anchor="middle">• Public sharp proxies</text>',
     '<text id="d-sharp-c3" x="700" y="220" fill="#e2e8f0" font-size="9" text-anchor="middle">• Public sharp proxies</text>'),
    ('<text x="700" y="232" fill="#a5b4fc" font-size="8" text-anchor="middle">Ensemble Weight: 45% (MOD)</text>',
     '<text id="d-sharp-cw" x="700" y="232" fill="#a5b4fc" font-size="8" text-anchor="middle">Ensemble Weight: 45% (MOD)</text>'),
    ('<text x="910" y="312" fill="#fdba74" font-size="8" text-anchor="middle">Core 30-35%</text>',
     '<text id="d-blend-c1" x="910" y="312" fill="#fdba74" font-size="8" text-anchor="middle">Core 30-35%</text>'),
    ('<text x="910" y="323" fill="#fdba74" font-size="8" text-anchor="middle">Sharp 40-45%</text>',
     '<text id="d-blend-c2" x="910" y="323" fill="#fdba74" font-size="8" text-anchor="middle">Sharp 40-45%</text>'),
    ('<text x="910" y="334" fill="#fdba74" font-size="8" text-anchor="middle">Soft 20-25%</text>',
     '<text id="d-blend-c3" x="910" y="334" fill="#fdba74" font-size="8" text-anchor="middle">Soft 20-25%</text>'),
    ('<text x="280" y="398" fill="#86efac" font-size="8" text-anchor="middle">ROBUST check</text>',
     '<text id="d-sens-sub" x="280" y="398" fill="#86efac" font-size="8" text-anchor="middle">ROBUST check</text>'),
    ('<text x="460" y="398" fill="#86efac" font-size="8" text-anchor="middle">Fair odds, Kelly, HALT flags</text>',
     '<text id="d-dc-sub" x="460" y="398" fill="#86efac" font-size="8" text-anchor="middle">Fair odds, Kelly, HALT flags</text>'),
    ('<text x="640" y="398" fill="#86efac" font-size="8" text-anchor="middle">MOD / SPEC / PASS tiers</text>',
     '<text id="d-class-sub" x="640" y="398" fill="#86efac" font-size="8" text-anchor="middle">MOD / SPEC / PASS tiers</text>'),
    ('<text x="820" y="398" fill="#86efac" font-size="8" text-anchor="middle">Novice execution guides</text>',
     '<text id="d-eli5-sub" x="820" y="398" fill="#86efac" font-size="8" text-anchor="middle">Novice execution guides</text>'),
]

# Fix SVG legend - replace invalid span-in-text with id-based texts
LEGEND_OLD = '''                        <rect x="935" y="82" width="12" height="12" fill="#1e2937" stroke="#0ea5e9"/><text x="952" y="92" fill="#94a3b8" font-size="8"><span class="en">Inputs (Data Layer)</span><span class="es">Entradas (Capa de Datos)</span></text>
                        <rect x="935" y="98" width="12" height="12" fill="#134e4b" stroke="#14b8a6"/><text x="952" y="108" fill="#94a3b8" font-size="8"><span class="en">Base Models</span><span class="es">Modelos Base</span></text>
                        <rect x="935" y="114" width="12" height="12" fill="#451a03" stroke="#f59e0b"/><text x="952" y="124" fill="#94a3b8" font-size="8"><span class="en">Finetunes / Rules</span><span class="es">Ajustes Finos / Reglas</span></text>
                        <rect x="935" y="130" width="12" height="12" fill="#78350f" stroke="#f59e0b"/><text x="952" y="140" fill="#94a3b8" font-size="8"><span class="en">Ensemble Blend</span><span class="es">Mezcla Ensemble</span></text>
                        <rect x="935" y="146" width="12" height="12" fill="#052e16" stroke="#22c55e"/><text x="952" y="156" fill="#94a3b8" font-size="8"><span class="en">Outputs &amp; Validation</span><span class="es">Salidas y Validación</span></text>'''

LEGEND_NEW = '''                        <rect x="935" y="82" width="12" height="12" fill="#1e2937" stroke="#0ea5e9"/><text id="d-leg-inputs" x="952" y="92" fill="#94a3b8" font-size="8">Inputs (Data Layer)</text>
                        <rect x="935" y="98" width="12" height="12" fill="#134e4b" stroke="#14b8a6"/><text id="d-leg-base" x="952" y="108" fill="#94a3b8" font-size="8">Base Models</text>
                        <rect x="935" y="114" width="12" height="12" fill="#451a03" stroke="#f59e0b"/><text id="d-leg-finetune" x="952" y="124" fill="#94a3b8" font-size="8">Finetunes / Rules</text>
                        <rect x="935" y="130" width="12" height="12" fill="#78350f" stroke="#f59e0b"/><text id="d-leg-blend" x="952" y="140" fill="#94a3b8" font-size="8">Ensemble Blend</text>
                        <rect x="935" y="146" width="12" height="12" fill="#052e16" stroke="#22c55e"/><text id="d-leg-outputs" x="952" y="156" fill="#94a3b8" font-size="8">Outputs &amp; Validation</text>'''

DIAGRAM_MAP_EN = """
                    'elo-src1': '(eloratings.net +',
                    'elo-src2': 'international-football.net)',
                    'elo-w': 'Weight: Core Input',
                    'xg-src1': '(FBref club-level for',
                    'xg-src2': 'probable XI + opp profile)',
                    'xg-w': 'Weight: Hybrid Input',
                    'ctx-src1': '(Form, H2H, Injuries,',
                    'ctx-src2': 'Weather, Travel, Ref)',
                    'ctx-w': 'Weight: Adjustment Input',
                    'hist-src1': '(WC openers, Euros,',
                    'hist-src2': 'top-5 leagues for μ & var)',
                    'hist-w': 'Weight: Prior Input',
                    'elo-c1': '• Two-way win prob (Elo gap)',
                    'elo-c2': '• 3-way w/ draw share (closeness)',
                    'elo-c3': '• λ via tanh gap → Poisson',
                    'elo-cw': 'Base Weight: 30-35%',
                    'btd-c1': '• Pairwise rating model (rA - rB)',
                    'btd-c2': '• BTD for explicit draw param (δ)',
                    'btd-c3': '• Dynamic EWMA updates',
                    'btd-cw': 'Ensemble Weight: 25%',
                    'xgh-c1': '• Club xG/xGA proxies (FBref)',
                    'xgh-c2': '• Blended w/ Elo share (0.4)',
                    'xgh-c3': '• Better shot-quality capture',
                    'xgh-cw': 'Ensemble Weight: 20%',
                    'sharp-c1': '• Pinnacle devigged probs',
                    'sharp-c2': '• Opta / Stats Perform sims',
                    'sharp-c3': '• Public sharp proxies',
                    'sharp-cw': 'Ensemble Weight: 45% (MOD)',
                    'blend-c1': 'Core 30-35%',
                    'blend-c2': 'Sharp 40-45%',
                    'blend-c3': 'Soft 20-25%',
                    'sens-sub': 'ROBUST check',
                    'dc-sub': 'Fair odds, Kelly, HALT flags',
                    'class-sub': 'MOD / SPEC / PASS tiers',
                    'eli5-sub': 'Novice execution guides',
                    'leg-inputs': 'Inputs (Data Layer)',
                    'leg-base': 'Base Models',
                    'leg-finetune': 'Finetunes / Rules',
                    'leg-blend': 'Ensemble Blend',
                    'leg-outputs': 'Outputs & Validation',
"""

DIAGRAM_MAP_ES = """
                    'elo-src1': '(eloratings.net +',
                    'elo-src2': 'international-football.net)',
                    'elo-w': 'Peso: Entrada Principal',
                    'xg-src1': '(FBref nivel club para',
                    'xg-src2': 'XI probable + perfil rival)',
                    'xg-w': 'Peso: Entrada Híbrida',
                    'ctx-src1': '(Forma, H2H, Lesiones,',
                    'ctx-src2': 'Clima, Viaje, Árbitro)',
                    'ctx-w': 'Peso: Entrada de Ajuste',
                    'hist-src1': '(Aperturas WC, Euro,',
                    'hist-src2': 'ligas top-5 para μ y var)',
                    'hist-w': 'Peso: Entrada Previa',
                    'elo-c1': '• Prob victoria bidireccional (brecha Elo)',
                    'elo-c2': '• 3 vías c/ participación empate',
                    'elo-c3': '• λ vía brecha tanh → Poisson',
                    'elo-cw': 'Peso Base: 30-35%',
                    'btd-c1': '• Modelo de rating por pares (rA - rB)',
                    'btd-c2': '• BTD para parámetro empate (δ)',
                    'btd-c3': '• Actualizaciones EWMA dinámicas',
                    'btd-cw': 'Peso Ensemble: 25%',
                    'xgh-c1': '• Proxies xG/xGA de club (FBref)',
                    'xgh-c2': '• Mezclado c/ participación Elo (0.4)',
                    'xgh-c3': '• Mejor captura de calidad de tiro',
                    'xgh-cw': 'Peso Ensemble: 20%',
                    'sharp-c1': '• Probs Pinnacle devigged',
                    'sharp-c2': '• Sims Opta / Stats Perform',
                    'sharp-c3': '• Proxies sharp públicos',
                    'sharp-cw': 'Peso Ensemble: 45% (MOD)',
                    'blend-c1': 'Núcleo 30-35%',
                    'blend-c2': 'Sharp 40-45%',
                    'blend-c3': 'Suave 20-25%',
                    'sens-sub': 'Verificación ROBUSTO',
                    'dc-sub': 'Cuotas justas, Kelly, flags HALT',
                    'class-sub': 'Niveles MOD / SPEC / PASS',
                    'eli5-sub': 'Guías de ejecución para novatos',
                    'leg-inputs': 'Entradas (Capa de Datos)',
                    'leg-base': 'Modelos Base',
                    'leg-finetune': 'Ajustes Finos / Reglas',
                    'leg-blend': 'Mezcla Ensemble',
                    'leg-outputs': 'Salidas y Validación',
"""

EXTRA_IDS = [
    'elo-src1','elo-src2','elo-w','xg-src1','xg-src2','xg-w','ctx-src1','ctx-src2','ctx-w',
    'hist-src1','hist-src2','hist-w','elo-c1','elo-c2','elo-c3','elo-cw',
    'btd-c1','btd-c2','btd-c3','btd-cw','xgh-c1','xgh-c2','xgh-c3','xgh-cw',
    'sharp-c1','sharp-c2','sharp-c3','sharp-cw','blend-c1','blend-c2','blend-c3',
    'sens-sub','dc-sub','class-sub','eli5-sub','leg-inputs','leg-base','leg-finetune','leg-blend','leg-outputs',
]


def main():
    html = REPORT.read_text(encoding='utf-8')
    changed = 0

    for old, new in REPLACEMENTS:
        if old in html:
            html = html.replace(old, new)
            changed += 1
        else:
            print(f"WARN: replacement not found ({old[:60]}...)")

    for old, new in SVG_ID_PATCHES:
        if old in html:
            html = html.replace(old, new)
            changed += 1

    if LEGEND_OLD in html:
        html = html.replace(LEGEND_OLD, LEGEND_NEW)
        changed += 1

    # Inject extended diagram map into updateDiagramLang
    marker_en = "'legend-title': 'LEGEND & WEIGHTS'"
    if marker_en in html and "'elo-src1':" not in html:
        html = html.replace(
            marker_en + "\n                },",
            marker_en + ",\n" + DIAGRAM_MAP_EN + "                },",
        )
        html = html.replace(
            "'legend-title': 'LEYENDA Y PESOS'\n                }",
            "'legend-title': 'LEYENDA Y PESOS',\n" + DIAGRAM_MAP_ES + "                }",
        )
        old_ids = "const ids = ['layer1','layer2','layer3','layer4','elo','xg','ctx','hist','elo-core','btd','xg-hybrid','sharp','finetunes','r21','r14','r22','r20','blend','sens','dc-ev','class','eli5-out','legend-title'];"
        new_ids = "const ids = ['layer1','layer2','layer3','layer4','elo','xg','ctx','hist','elo-core','btd','xg-hybrid','sharp','finetunes','r21','r14','r22','r20','blend','sens','dc-ev','class','eli5-out','legend-title','" + "','".join(EXTRA_IDS) + "'];"
        html = html.replace(old_ids, new_ids)
        changed += 1

    REPORT.write_text(html, encoding='utf-8')
    print(f"Applied {changed} patch groups to {REPORT}")


if __name__ == '__main__':
    main()