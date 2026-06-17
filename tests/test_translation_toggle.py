#!/usr/bin/env python3
"""
Playwright audit: EN/ES translation toggle on wc_june16_2026_report.html

Ensures all user-facing visible text changes when switching languages.
Run: python3 tests/test_translation_toggle.py
Or:  python3 -m pytest tests/test_translation_toggle.py -v
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
REPORT = ROOT / "wc_june16_2026_report.html"

# Text that legitimately stays the same across languages (brand names, codes, numbers, URLs)
ALLOWLIST_PATTERNS = [
    r"^WCdecider$",
    r"^v3\.1\+finetune$",
    r"^v4\.1 prod$",
    r"^EN$",
    r"^ES$",
    r"^VERIFIED$",
    r"^MOD$",
    r"^SPEC$",
    r"^PASS$",
    r"^ROBUST$",
    r"^SENSITIVE$",
    r"^EV%$",
    r"^o$",
    r"^λ$",
    r"^BTTS$",
    r"^BTD$",
    r"^HALT$",
    r"^DC$",
    r"^1X2$",
    r"^FRA$",
    r"^SEN$",
    r"^IRQ$",
    r"^NOR$",
    r"^ARG$",
    r"^ALG$",
    r"^AUT$",
    r"^JOR$",
    r"^KSA$",
    r"^URU$",
    r"^BEL$",
    r"^EGY$",
    r"^CV$",
    r"^MODERATE$",
    r"^SPECULATIVE$",
    r"^RIGOR • ELEGANCE • SOPHISTICATION$",
    r"^FRESH DATA PULLED$",
    r"^Group [A-Z] •",
    r"^\d",
    r"^[\d.,%+\-–/]+$",
    r"^~",
    r"^p[A-Z]{2,4}",
    r"^Elo:",
    r"^Lima, Peru",
    r"^AGENT\.md",
    r"^wc_",
    r"^python3",
    r"^\.py",
    r"^\.csv",
    r"^\.txt",
    r"^\.html",
    r"^\.md",
    r"^IMG_",
    r"^https?://",
    r"^www\.",
    r"^eloratings",
    r"^international-football",
    r"^ESPN",
    r"^FBref",
    r"^Pinnacle",
    r"^Opta",
    r"^Dixon",
    r"^Karlis",
    r"^Snowberg",
    r"^arXiv",
    r"^Bradley-Terry",
    r"^Poisson",
    r"^xG",
    r"^Tchouaméni",
    r"^Koundé",
    r"^Mbappé",
    r"^Haaland",
    r"^Messi",
    r"^Arnautović",
    r"^Alaba",
    r"^Maignan",
    r"^Mendy",
    r"^Mané",
    r"^Jackson",
    r"^Sellami",
    r"^Baumgartner",
    r"^Faghani",
    r"^Vozinha",
    r"^Ashour",
    r"^Hany",
    r"^Bensebaini",
    r"^Al-Naimat",
    r"^Sørloth",
    r"^Ødegaard",
    r"^Doku",
    r"^Gillette",
    r"^MetLife",
    r"^Arrowhead",
    r"^Levi's",
    r"^Atlanta",
    r"^Seattle",
    r"^Spain 0-0",
    r"^Belgium 1-1",
    r"^France win",
    r"^Iraq DC",
    r"^Argentina win",
    r"^Austria draw",
    r"^KSA-URU",
    r"^AUT Draw",
    r"^FRA\+O3\.5",
    r"^FRA win",
    r"^Draw @",
    r"^Under 2\.5",
    r"^BTTS No",
    r"^Low \(",
    r"^Med",
    r"^High \(",
    r"^Highest$",
    r"^Medium$",
    r"^\+",
    r"^−",
    r"^\−",
    r"^S/",
    r"^PEN",
    r"^1\.",
    r"^2\.",
    r"^3\.",
    r"^66\.2%$",
    r"^21\.7%$",
    r"^12\.1%$",
    r"^74%$",
    r"^19\.8%$",
    r"^6\.2%$",
    r"^60\.1%$",
    r"^23\.2%$",
    r"^16\.7%$",
    r"^46\.9%$",
    r"^48\.2%$",
    r"^61%$",
    r"^23%$",
    r"^0\.258$",
    r"^1\.78$",
    r"^5\.05$",
    r"^5\.15$",
    r"^1\.19",
    r"^1\.41$",
    r"^1\.50",
    r"^4\.45$",
    r"^5\.20$",
    r"^1\.67$",
    r"^4\.05$",
    r"^5\.60$",
    r"^4\.30$",
    r"^4\.31$",
    r"^3\.7",
    r"^L'Équipe",
    r"^RotoWire",
    r"^Sports Mole",
    r"^WhoScored",
    r"^Fotmob",
    r"^Yahoo",
    r"^Covers",
    r"^Flashscore",
    r"^Wikipedia",
    r"^Athletic",
    r"^FOX",
    r"^NWS",
    r"^Climate",
    r"^StatsAndSnakeOil",
    r"^Stats Perform",
    r"^JPE",
    r"^Applied Statistics",
    r"^Knowledge-Based",
    r"^International Journal",
    r"^Journal of",
    r"^Bulletin of",
    r"^executable stub",
    r"^bradley_terry",
    r"^xg_poisson",
    r"^full_1x2",
    r"^apply_finetunes",
    r"^run_full_pipeline",
    r"^MD[0-9]",
    r"^Rule [0-9]",
    r"^Rules [0-9]",
    r"^§",
    r"^¼ Kelly",
    r"^f\*",
    r"^μ",
    r"^ρ",
    r"^π",
    r"^δ",
    r"^λ ",
    r"^P\(",
    r"^DC ",
    r"^EV ",
    r"^Newbie:",
    r"^\(Newbie",
    r"^Glosario",
    r"^Nota principiante",
    r"^Principiante:",
    r"^\(Principiante",
    r"^Data$",
    r"^Data \(",
    r"^Ideas$",
    r"^Top Ideas$",
    r"^Top Recommendation$",
    r"^Recommendations",
    r"^Executed Model$",
    r"^Confidence ceiling",
    r"^¼ Kelly default",
    r"^Example on",
    r"^Hard rules",
    r"^Player props",
    r"^Elo: eloratings",
    r"^Lineups/injuries",
    r"^Results \(backtest\)",
    r"^Weather/venue",
    r"^Sharp/model",
    r"^Academic:",
    r"^Screenshots",
    r"^Prior reports",
    r"^Integration:",
    r"^Both proposed",
    r"^Executable stub",
    r"^NOR full strength",
    r"^ARG strong core",
    r"^AUT:",
    r"^JOR ",
    r"^pIRQ",
    r"^pARG",
    r"^pAUT",
    r"^pD ",
    r"^pNOR",
    r"^pALG",
    r"^pJOR",
    r"^Prior ",
    r"^Fair draw",
    r"^λ 2\.",
    r"^λ 0\.",
    r"^λ ARG",
    r"^P\(O2\.5\)",
    r"^DC FRA",
    r"^DC ARG",
    r"^DC p",
    r"^1\. IRQ",
    r"^2\. ",
    r"^3\. ",
    r"^1\. FRA",
    r"^1\. ARG",
    r"^1\. KSA",
    r"^Draw @5",
    r"^FRA win \+ Over",
    r"^Under 2\.5 /",
    r"^FRA 1X2",
    r"^NOR 1X2",
    r"^ARG win 1X2",
    r"^ARG\+BTTS",
    r"^Over 2\.5 or",
    r"^High totals",
    r"^IRQ or Draw",
    r"^BEL win",
    r"^MODERATE \(ROBUST",
    r"^MODERATE \(if",
    r"^SPECULATIVE",
    r"^PASS",
    r"^All heavy",
    r"^All EV",
    r"^All numbers",
    r"^All sections",
    r"^All prior",
    r"^All constraints",
    r"^Hover nodes",
    r"^Full subagent",
    r"^Additional backtest",
    r"^Base: 78",
    r"^\+ Rule 21",
    r"^\+ Regla 21",
    r"^→ ",
    r"^LAYER ",
    r"^CAPA ",
    r"^Weight:",
    r"^Peso:",
    r"^Core ",
    r"^Sharp ",
    r"^Soft ",
    r"^Ensemble Weight",
    r"^Base Weight",
    r"^WEIGHTED",
    r"^MEZCLA",
    r"^FINETUNES",
    r"^AJUSTES",
    r"^LEGEND",
    r"^LEYENDA",
    r"^ROBUST check",
    r"^Fair odds",
    r"^MOD / SPEC",
    r"^Novice execution",
    r"^Guías de ejecución",
    r"^\• ",
    r"^\(",
    r"^Multi-source",
    r"^No major",
    r"^Benign weather",
    r"^Mild weather",
    r"^Milder Bay",
    r"^~30°C",
    r"^~14:00",
    r"^~17:00",
    r"^~20:00",
    r"^~23:00",
    r"^Group I",
    r"^Group J",
    r"^Group G",
    r"^Group H",
    r"^\(Group",
    r"^\(Grupo",
    r"^FRA Maignan",
    r"^Lineups:",
    r"^Injuries:",
    r"^Form/Notes:",
    r"^Alineaciones:",
    r"^Lesiones:",
    r"^Forma/Notas:",
    r"^2002 ",
    r"^Finisher",
    r"^finisher",
    r"^extreme mismatch",
    r"^extreme\.",
    r"^only 0\.069",
    r"^negative EV",
    r"^neg EV",
    r"^S/10",
    r"^S/15",
    r"^S/20",
    r"^S/8",
    r"^S/12",
    r"^S/25",
    r"^S/200",
    r"^Conf [0-9]",
    r"^Cap S/",
    r"^Risks:",
    r"^Single failure",
    r"^if boost",
    r"^if cleared",
    r"^if o ",
    r"^data-aligned",
    r"^conditions \+",
    r"^positive base",
    r"^positive conservative",
    r"^DC joint",
    r"^high raw",
    r"^marginal \+",
    r"^clinical",
    r"^organized",
    r"^domestic-heavy",
    r"^low-block",
    r"^creator loss",
    r"^debut motivation",
    r"^milder venue",
    r"^quality gap",
    r"^warmups mixed",
    r"^counter-capable",
    r"^muscular monitor",
    r"^expected\)",
    r"^fitness\.",
    r"^fit caveat",
    r"^Wimmer doubts",
    r"^XI Schlager",
    r"^CS streak",
    r"^Alvarez fit",
    r"^Messi confirmed",
    r"^storms",
    r"^low pens",
    r"^pocos penales",
    r"^Clima",
    r"^Área de la",
    r"^Árbitro",
    r"^Ref ",
    r"^France vs",
    r"^Iraq vs",
    r"^Argentina vs",
    r"^Austria vs",
    r"^Francia vs",
    r"^Jordania",
    r"^Noruega",
    r"^Argelia",
    r"^Senegal",
    r"^Jordan$",
    r"^Austria$",
    r"^France$",
    r"^Iraq$",
    r"^Norway$",
    r"^Argentina$",
    r"^Algeria$",
    r"^Spain$",
    r"^Belgium$",
    r"^Egypt$",
    r"^Cape Verde$",
    r"^Uruguay$",
    r"^Saudi",
    r"^Kingdom of Saudi",
    r"^Kingdom",
    r"^This bet refers",
    r"^This is a combo",
    r"^BTTS =",
    r"^BTTS No =",
    r"^Under 2\.5 goals",
    r"^1X2 is",
    r"^PASS =",
    r"^MODERATE =",
    r"^SPECULATIVE =",
    r"^SENSITIVE =",
    r"^HALT means",
    r"^λ \(lambda\)",
    r"^DC p\(IRQ",
    r"^DC ARG\+BTTS",
    r"^Rule 14 is",
    r"^Rule 14/19",
    r"^Regla 14",
    r"^Reglas 14",
    r"^Esta apuesta",
    r"^Es una apuesta",
    r"^Ambos equipos",
    r"^Ganas si",
    r"^solo pierdes",
    r"^Probabilidad de",
    r"^número esperado",
    r"^corrección de sesgo",
    r"^ajuste por sesgo",
    r"^probabilidad del modelo",
    r"^probabilidad real",
    r"^probabilidad conjunta",
    r"^probabilidad extra",
    r"^Correlated probability",
    r"^You win if",
    r"^You only lose",
    r"^At least one team",
    r"^Both teams must",
    r"^France must win",
    r"^Francia debe",
    r"^Iraq or Draw",
    r"^Iraq wins or",
    r"^IRQ DC =",
    r"^the match to draw",
    r"^the away team",
    r"^the home team",
    r"^the betting app",
    r"^the model",
    r"^the total goals",
    r"^the expected",
    r"^the middle",
    r"^the book",
    r"^the game",
    r"^the teams",
    r"^the stake",
    r"^the odd",
    r"^the slip",
    r"^the boost",
    r"^the number",
    r"^the money",
    r"^the app",
    r"^the match",
    r"^the event",
    r"^the chance",
    r"^the price",
    r"^the result",
    r"^the full",
    r"^the exact",
    r"^the precise",
    r"^the published",
    r"^the transparent",
    r"^the raw",
    r"^the documented",
    r"^the verified",
    r"^the realistic",
    r"^the historical",
    r"^the live",
    r"^the prior",
    r"^the current",
    r"^the actual",
    r"^the final",
    r"^the whole",
    r"^the entire",
    r"^the same",
    r"^the higher",
    r"^the lower",
    r"^the harder",
    r"^the easier",
    r"^the bigger",
    r"^the smaller",
    r"^the stronger",
    r"^the weaker",
    r"^the sharper",
    r"^the softer",
    r"^the best",
    r"^the worst",
    r"^the only",
    r"^the main",
    r"^the key",
    r"^the top",
    r"^the bottom",
    r"^the middle",
    r"^the left",
    r"^the right",
    r"^the world",
    r"^the pros",
    r"^the professionals",
    r"^the tournament",
    r"^the torneo",
    r"^the partido",
    r"^the equipo",
    r"^the goles",
    r"^the cuota",
    r"^the apuesta",
    r"^the boleto",
    r"^the stake",
    r"^the monto",
    r"^the ganancia",
    r"^the saldo",
    r"^the billetera",
    r"^the wallet",
    r"^the balance",
    r"^the screen",
    r"^the button",
    r"^the tab",
    r"^the section",
    r"^the icon",
    r"^the logo",
    r"^the flame",
    r"^the orange",
    r"^the red",
    r"^the green",
    r"^the gray",
    r"^the grey",
    r"^the error",
    r"^the message",
    r"^the screenshot",
    r"^the captura",
    r"^the confirmation",
    r"^the success",
    r"^the failure",
    r"^the loss",
    r"^the win",
    r"^the draw",
    r"^the empate",
    r"^the victoria",
    r"^the derrota",
    r"^the ganancia",
    r"^the pérdida",
    r"^the profit",
    r"^the return",
    r"^the retorno",
    r"^the total",
    r"^the combined",
    r"^the separate",
    r"^the correlated",
    r"^the correlated",
    r"^Replicability",
    r"^wc_replicable",
    r"^wc_2026",
    r"^France win 66",
    r"^Iraq DC 35",
    r"^Argentina win 74",
    r"^Austria draw 23",
    r"^raw ",
    r"^Raw ",
    r"^Documented",
    r"^Objetivos",
    r"^Ejecuta ",
    r"^Run ",
    r"^inspect ",
    r"^inspecciona ",
    r"^Todos los números",
    r"^All prior HTML",
    r"^Analytical Framework",
    r"^Marco Analítico",
    r"^This interactive",
    r"^Este diagrama",
    r"^Designed for",
    r"^Diseñado para",
    r"^inspired by",
    r"^inspirado en",
    r"^tensorboard",
    r"^TensorBoard",
    r"^Sankey",
    r"^MLflow",
    r"^Visualizing Dataflow",
    r"^sports prediction",
    r"^literatura de predicción",
    r"^Elo Ratings",
    r"^Calificaciones Elo",
    r"^xG / xGA",
    r"^Proxies xG",
    r"^Contextual Data",
    r"^Datos Contextuales",
    r"^Historical Calibration",
    r"^Calibración Histórica",
    r"^Elo \+ Poisson",
    r"^Núcleo Elo",
    r"^Bradley-Terry / BTD",
    r"^xG Poisson Hybrid",
    r"^Híbrido xG",
    r"^Sharp Consensus",
    r"^Consenso Sharp",
    r"^FINETUNES, RULES",
    r"^AJUSTES FINOS",
    r"^Rule 21:",
    r"^Regla 21:",
    r"^Rule 14/19:",
    r"^Reglas 14/19:",
    r"^Rule 22:",
    r"^Regla 22:",
    r"^Rule 20/23:",
    r"^Reglas 20/23:",
    r"^3 SENSITIVITIES",
    r"^3 SENSIBILIDADES",
    r"^DC JOINTS",
    r"^JUNTAS DC",
    r"^CLASSIFICATION",
    r"^CLASIFICACIÓN",
    r"^ELI5 \+",
    r"^Inputs \(Data",
    r"^Entradas \(Capa",
    r"^Base Models$",
    r"^Modelos Base$",
    r"^Finetunes / Rules",
    r"^Ajustes Finos /",
    r"^Ensemble Blend$",
    r"^Mezcla Ensemble$",
    r"^Outputs & Validation",
    r"^Salidas y Validación",
    r"^\(eloratings",
    r"^\(FBref",
    r"^\(Form,",
    r"^\(WC openers",
    r"^\(Group H",
    r"^\(Grupo H",
    r"^\(Grupo G",
    r"^\(Grupo I",
    r"^\(Grupo J",
    r"^Backtested •",
    r"^Backtest •",
    r"^Finetuned •",
    r"^Subagent-validated",
    r"^HTML report",
    r"^reporte HTML",
    r"^real-time data",
    r"^datos en tiempo real",
    r"^All numbers from executed",
    r"^Todos los números del modelo",
    r"^Model executed",
    r"^Modelo ejecutado",
    r"^Print / PDF",
    r"^Imprimir / PDF",
    r"^June 15",
    r"^Copa del Mundo",
    r"^PERFECTED ENSEMBLE",
    r"^ENSEMBLE PERFECCIONADO",
    r"^Screenshots-only",
    r"^Cuotas solo",
    r"^Executive Summary",
    r"^Resumen Ejecutivo",
    r"^Backtest Insights",
    r"^Lecciones del Backtest",
    r"^Surefire / Near",
    r"^Apuestas \"Seguras\"",
    r"^Upcoming \(June",
    r"^Próximos \(16",
    r"^Introspection \+",
    r"^Introspección \+",
    r"^Subagents \+",
    r"^Subagentes \+",
    r"^Risk-Adjusted",
    r"^Atractivo Ajustado",
    r"^Final Classifications",
    r"^Clasificaciones Finales",
    r"^Bankroll &",
    r"^Stakeo",
    r"^Sources \(",
    r"^Fuentes \(",
    r"^Cross-book",
    r"^Nota de mejor",
    r"^ELI5 for the",
    r"^ELI5 para el",
    r"^Subagents ran full protocol on screenshot odds. Key \+EV/SPEC from model: ENG -1 \+17.7% SPEC; CAN -1 \+19.9% MOD; GER -1 \+4.3% SPEC; SUI boost \+19.2% SPEC; TUR O3.5 \+56.9% HALT; most 1X2 shorts PASS. Re-check lineups ~90min pre-KO. ELI5 in subagent logs.",
    r"^Subagentes ejecutaron protocolo completo en cuotas. \+EV/SPEC clave del modelo: ENG -1 \+17,7% SPEC; CAN -1 \+19,9% MOD; GER -1 \+4,3% SPEC; SUI boost \+19,2% SPEC; TUR O3.5 \+56,9% HALT; la mayoría de cortos 1X2 PASS. Re-verificar alineaciones ~90min pre-KO. ELI5 en logs de subagentes.",
    r"^All EV vs screenshot prices. v4.1 calibration holds \(negative on heavy favorites; value in HC & boosts with DC\). HALT on extremes. Report element-by-element validated to model results.",
    r"^Todos los EV vs precios de capturas. Calibración v4.1 se mantiene \(negativo en favoritos pesados; valor en HC y boosts con DC\). HALT en extremos. Reporte validado elemento por elemento a resultados del modelo.",
    r"^What this bet",
    r"^Qué es esta",
    r"^The odd ",
    r"^La cuota ",
    r"^Exact step-by-step",
    r"^Pasos exactos",
    r"^Important notes",
    r"^Notas importantes",
    r"^If something goes",
    r"^Si algo sale",
    r"^After the game",
    r"^Después del partido",
    r"^Explicación simple",
    r"^No genuine near",
    r"^No existen multiplicadores",
    r"^Key Realized",
    r"^Resultados Reales",
    r"^Finetune Impact",
    r"^Impacto de Ajustes",
    r"^Other leagues",
    r"^Calibración de otras",
    r"^Key lesson",
    r"^Selection$",
    r"^Selección$",
    r"^Model P$",
    r"^P Modelo$",
    r"^Var Proxy$",
    r"^Proxy Var$",
    r"^Risk-Adj$",
    r"^Riesgo-Ajust$",
    r"^Class$",
    r"^Clase$",
    r"^Data Snapshot",
    r"^Resumen de Datos",
    r"^Executed Model \(",
    r"^Modelo Ejecutado \(",
    r"^Recommendations \(",
    r"^Recomendaciones \(",
    r"^Top Recommendation$",
    r"^Recomendación Principal$",
    r"^Data \(strong\)$",
    r"^Datos \(fuertes\)$",
    r"^Data \(≥2",
    r"^Datos \(≥2",
    r"^Mild weather",
    r"^Clima templado",
    r"^Haaland/Ødegaard",
    r"^en forma$",
    r"^fit$",
    r"^posibles tormentas$",
    r"^torneo$",
    r"^tournament$",
    r"^out entire",
    r"^fuera todo",
    r"^delantero top",
    r"^top striker",
    r"^creativity loss",
    r"^pérdida de creatividad",
    r"^Wimmer",
    r"^Schlager",
    r"^Laimer",
    r"^Lienhart",
    r"^Mwene",
    r"^Seiwald",
    r"^Sabitzer",
    r"^Schmid",
    r"^Gregoritsch",
    r"^Diatta",
    r"^Koulibaly",
    r"^Niakhaté",
    r"^Jakobs",
    r"^Camara",
    r"^Sarr",
    r"^Ndiaye",
    r"^Saliba",
    r"^Upamecano",
    r"^Digne",
    r"^Rabiot",
    r"^Olise",
    r"^Dembélé",
    r"^Doué",
    r"^Salomon",
    r"^Rasmussen",
    r"^Hjulmand",
    r"^Højlund",
    r"^Gyökeres",
    r"^Isak",
    r"^Kulusevski",
    r"^Dahmen",
    r"^Yıldız",
    r"^Çalhanoğlu",
    r"^Endo",
    r"^Mitoma",
    r"^Kubo",
    r"^Kamada",
    r"^Enciso",
    r"^Davies",
    r"^Amad Diallo",
    r"^Diallo",
    r"^Bellingham",
    r"^Vinícius",
    r"^Rodrygo",
    r"^Neymar",
    r"^Ronaldo",
    r"^Modrić",
    r"^De Bruyne",
    r"^Salah",
    r"^Kane",
    r"^Son Heung",
    r"^Lewandowski",
    r"^Benzema",
    r"^Griezmann",
    r"^Pogba",
    r"^Kanté",
    r"^Varane",
    r"^Hernández",
    r"^Giroud",
    r"^Giroud",
    r"^Giroud",
]

# Compile allowlist - be more targeted: only skip obvious non-translatable
SKIP_TAGS = {"script", "style", "noscript"}
MIN_TEXT_LEN = 4  # ignore very short fragments


def is_allowlisted(text: str) -> bool:
    t = text.strip()
    if len(t) < MIN_TEXT_LEN:
        return True
    # Pure numbers/symbols
    if re.match(r"^[\d\s.,%+\-–/():;•@&]+$", t):
        return True
    # Mostly uppercase codes / abbreviations under 6 chars
    if len(t) <= 6 and t.isupper():
        return True
    return False


def looks_english(text: str) -> bool:
    """Heuristic: text likely needs Spanish translation."""
    t = text.strip()
    if is_allowlisted(t):
        return False
    # Spanish markers
    spanish_markers = [
        "ación", "ción", "mente", "emos", "amos", "ión ", " qué ", " cómo ",
        " para ", " después ", " también ", " según ", " todos los ", " todas las ",
        " principiante", " apuesta", " partido", " goles", " cuota", " empate",
        " victoria", " derrota", " modelo", " datos", " fuentes", " regla",
        " ajuste", " probabilidad", " recomendación", " explicación",
        "capa ", "entrada", "salida", "mezcla", "niveles", "guías", "sugerencias",
        "replicabilidad", "validación", "ejecutado", "backtesteado", "verificado",
        "menos 2.5", "empate aut", "junta dc", "victoria fra", "victoria arg",
        "alineado", "riesgos:", "falla única", "stake pequeño", "captura previa",
        "previo ", "despeja", "despejado", "sensible", "especulativo", "moderado",
    ]
    lower = t.lower()
    if any(m in lower for m in spanish_markers):
        return False
    # Mixed ES/EN technical labels that are intentionally bilingual codes
    if re.match(r"^(MOD|SPEC|PASS|BTTS|1X2|HALT|EV%|λ|DC|FRA|SEN|IRQ|NOR|ARG|ALG|AUT|JOR|KSA|URU)\b", t, re.I):
        return False
    # English common words
    english_words = [
        " the ", " and ", " for ", " with ", " from ", " this ", " that ",
        " are ", " was ", " were ", " have ", " has ", " will ", " should ",
        " model ", " match ", " bet ", " draw ", " win ", " goals ", " team ",
        " data ", " source ", " executed ", " backtest ", " recommendation ",
        " newbie ", " stake ", " odds ", " probability ", " expected ",
        " analysis ", " report ", " workflow ", " framework ", " validation ",
        " classification ", " bankroll ", " confidence ", " injury ", " lineup ",
        " weather ", " venue ", " form ", " risks ", " failure ", " boost ",
        " screenshot ", " fresh ", " prior ", " heavy ", " favorite ", " under ",
        " over ", " both ", " unless ", " after ", " before ", " step ", " tap ",
        " open ", " check ", " verify ", " message ", " stop ", " place ",
        " hover ", " weights ", " layer ", " inputs ", " outputs ", " finetune ",
        " ensemble ", " sensitivity ", " robust ", " speculative ", " moderate ",
        " pass ", " cleared ", " aligned ", " conditions ", " historical ",
        " calibration ", " integration ", " proposed ", " tested ", " additional ",
        " other ", " key ", " top ", " full ", " all ", " no ", " none ",
        " highest ", " lowest ", " medium ", " low ", " high ", " marginal ",
        " negative ", " positive ", " attractive ", " trap ", " variance ",
        " cap ", " example ", " default ", " hard ", " rules ", " never ",
        " player ", " props ", " combo ", " joint ", " correlated ", " naive ",
        " multiplying ", " separately ", " chances ", " choosing ", " event ",
        " refers ", " means ", " must ", " score ", " total ", " combined ",
        " full match ", " final ", " result ", " outright ", " unless ",
        " double ", " chance ", " covers ", " two ", " outcomes ", " covers ",
        " explained ", " simple ", " assistant ", " never ", " placed ",
        " watched ", " football ", " before ", " actually ", " execute ",
        " recommended ", " super ", " jargon ", " left ", " unexplained ",
        " important ", " notes ", " something ", " goes ", " wrong ", " game ",
        " interactive ", " diagram ", " showcases ", " demonstrates ", " designed ",
        " stakeholders ", " appreciate ", " validity ", " elegance ", " sophistication ",
        " approach ", " inspired ", " implementations ", " view ", " source ",
        " expanded ", " details ", " dynamic ", " proves ", " multi-model ",
        " rigor ", " remaining ", " transparent ", " actionable ",
        " replicability ", " pipeline ", " documented ", " targets ", " transparent ",
        " mechanism ", " columns ", " published ", " numbers ", " blend ",
        " audited ", " synced ", " verification ", " output ",
        " backtested ", " finetuned ", " subagent-validated ", " real-time ",
        " numbers from ", " executed ", " subagents ",
    ]
    padded = f" {lower} "
    return any(w in padded for w in english_words) or bool(re.search(r"\b(the|and|for|with|this|that|are|was|have|will|model|match|bet|draw|win|data|team|goals)\b", lower))


AUDIT_JS = """
() => {
  const SKIP = new Set(['SCRIPT','STYLE','NOSCRIPT','SVG','IFRAME']);
  const results = [];

  function isVisible(el) {
    let node = el;
    while (node && node !== document.body) {
      if (SKIP.has(node.tagName)) return false;
      const style = window.getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
      node = node.parentElement;
    }
    return !!el;
  }

  function getVisibleTextNodes(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || SKIP.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
        const t = node.textContent.replace(/\\s+/g, ' ').trim();
        if (!t || t.length < 4) return NodeFilter.FILTER_REJECT;
        if (!isVisible(parent)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    const nodes = [];
    let n;
    while ((n = walker.nextNode())) nodes.push(n);
    return nodes;
  }

  function nodePath(node) {
    const parts = [];
    let el = node.parentElement;
    while (el && el !== document.body && parts.length < 6) {
      let seg = el.tagName.toLowerCase();
      if (el.id) seg += '#' + el.id;
      else if (el.className && typeof el.className === 'string') {
        const cls = el.className.split(/\\s+/).filter(c => c && !c.startsWith('fa-')).slice(0,2).join('.');
        if (cls) seg += '.' + cls;
      }
      parts.unshift(seg);
      el = el.parentElement;
    }
    return parts.join(' > ');
  }

  function hasBilingualParent(node) {
    let el = node.parentElement;
    while (el && el !== document.body) {
      if (el.classList && (el.classList.contains('en') || el.classList.contains('es'))) return true;
      // abbr with en/es label children counts as bilingual
      if (el.classList && el.classList.contains('abbr')) {
        if (el.querySelector('.en') && el.querySelector('.es')) return true;
      }
      // SVG labels managed by updateDiagramLang
      if (el.id && el.id.startsWith('d-')) return true;
      el = el.parentElement;
    }
    return false;
  }

  const lang = document.body.classList.contains('lang-es') ? 'es' : 'en';
  const nodes = getVisibleTextNodes(document.body);
  const seen = new Set();

  for (const node of nodes) {
    const text = node.textContent.replace(/\\s+/g, ' ').trim();
    const key = text + '::' + nodePath(node);
    if (seen.has(key)) continue;
    seen.add(key);

    const bilingual = hasBilingualParent(node);
    results.push({
      lang,
      text,
      path: nodePath(node),
      bilingual,
      tag: node.parentElement ? node.parentElement.tagName : '',
      classes: node.parentElement && node.parentElement.className ? String(node.parentElement.className) : ''
    });
  }
  return results;
}
"""

COMPARE_JS = """
() => {
  const SKIP = new Set(['SCRIPT','STYLE','NOSCRIPT']);
  function isNodeVisible(node) {
    let el = node.parentElement;
    while (el && el !== document.body) {
      if (SKIP.has(el.tagName)) return false;
      const style = window.getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
      el = el.parentElement;
    }
    return true;
  }
  function visibleTextSet() {
    const set = new Set();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!isNodeVisible(node)) return NodeFilter.FILTER_REJECT;
        const t = node.textContent.replace(/\\s+/g, ' ').trim();
        if (t.length >= 8) set.add(t);
        return NodeFilter.FILTER_SKIP;
      }
    });
    while (walker.nextNode()) {}
    return Array.from(set);
  }
  return visibleTextSet();
}
"""

VISIBILITY_CHECK_JS = """
(enMarkers) => {
  const body = document.body;
  const lang = body.classList.contains('lang-es') ? 'es' : 'en';
  const hiddenEn = [];
  const visibleEs = [];
  document.querySelectorAll('.en').forEach(el => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    const shown = style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    if (lang === 'es' && shown) hiddenEn.push(el.textContent.trim().slice(0, 80));
  });
  document.querySelectorAll('.es').forEach(el => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    const shown = style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    if (lang === 'es' && shown) visibleEs.push(el.textContent.trim().slice(0, 80));
  });
  const markerHits = enMarkers.filter(m => document.body.innerText.includes(m));
  return { lang, hiddenEnCount: hiddenEn.length, hiddenEnSamples: hiddenEn.slice(0, 5), visibleEsCount: visibleEs.length, markerHitsInBody: markerHits };
}
"""


def run_audit():
    from playwright.sync_api import sync_playwright

    if not REPORT.exists():
        raise FileNotFoundError(f"Report not found: {REPORT}")

    url = REPORT.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(500)

        # EN mode
        page.click("#btn-en")
        page.wait_for_timeout(300)
        en_texts = set(page.evaluate(COMPARE_JS))

        # ES mode
        page.click("#btn-es")
        page.wait_for_timeout(300)
        es_texts = set(page.evaluate(COMPARE_JS))

        # Untranslated: English-looking text still visible in ES mode
        page.click("#btn-es")
        es_nodes = page.evaluate(AUDIT_JS)

        # Check body class and toggle state
        body_class = page.evaluate("() => document.body.className")
        btn_es_active = page.evaluate("() => document.getElementById('btn-es').classList.contains('active')")

        # Diagram labels in ES
        diagram_es = page.evaluate("""() => {
          const ids = ['d-layer1','d-elo','d-legend-title','d-blend'];
          const out = {};
          for (const id of ids) {
            const el = document.getElementById(id);
            out[id] = el ? el.textContent : null;
          }
          return out;
        }""")

        # SVG legend spans (broken pattern)
        svg_legend_raw = page.evaluate("""() => {
          const svg = document.querySelector('svg');
          if (!svg) return null;
          return svg.innerHTML.includes('class="en"');
        }""")

        browser.close()

    # English text persisting in ES (same visible strings)
    persisted = sorted(en_texts & es_texts, key=len, reverse=True)
    untranslated_es = [
        n for n in es_nodes
        if n["lang"] == "es" and not n["bilingual"] and looks_english(n["text"])
    ]

    return {
        "body_class": body_class,
        "btn_es_active": btn_es_active,
        "en_count": len(en_texts),
        "es_count": len(es_texts),
        "persisted": persisted,
        "untranslated_es": untranslated_es,
        "diagram_es": diagram_es,
        "svg_legend_has_html_spans": svg_legend_raw,
    }


def test_translation_toggle_switches_language():
    """Playwright integration: toggle changes body class and diagram labels."""
    from playwright.sync_api import sync_playwright

    url = REPORT.as_uri()
    en_markers = [
        "Executive Summary • Verified Outputs",
        "Backtested • Finetuned • Subagent-validated",
        "68.6% win / 28.1% draw",
        "Analytical Framework & Modeling Workflow",
        "v4.1 anchor → MOD 70/30 blend (Rule 24)",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="networkidle")
        page.wait_for_function("() => typeof window.switchLang === 'function'", timeout=5000)

        # Use evaluate to reliably trigger switch (onclick may have timing issues in headless)
        page.evaluate("() => window.switchLang('en')")
        page.wait_for_timeout(200)
        assert "lang-en" in page.evaluate("() => document.body.className")

        layer_en = page.text_content("#d-layer1")
        page.evaluate("() => window.switchLang('es')")
        page.wait_for_timeout(200)
        assert "lang-es" in page.evaluate("() => document.body.className")
        layer_es = page.text_content("#d-layer1")

        assert layer_en != layer_es
        assert "CAPA 1" in (layer_es or "")

        vis = page.evaluate(VISIBILITY_CHECK_JS, en_markers)
        assert vis["lang"] == "es"
        assert vis["hiddenEnCount"] == 0, f".en elements still visible in ES mode: {vis['hiddenEnSamples']}"
        assert vis["visibleEsCount"] > 50, "Expected many .es elements visible in ES mode"
        for marker in en_markers:
            assert marker not in page.evaluate("() => document.body.innerText"), (
                f"EN marker still in body text after ES toggle: {marker!r}"
            )
        browser.close()


def test_all_user_facing_text_translates():
    """Audit: no English user-facing text without bilingual wrapper in ES mode."""
    result = run_audit()

    failures = []
    for item in result["untranslated_es"]:
        text = item["text"][:120]
        failures.append(f"  [{item['path']}] {text!r}")

    # Persisted strings that are truly visible in both langs (after ancestor visibility check)
    critical_persisted = [
        t for t in result["persisted"]
        if looks_english(t) and len(t) >= 20
    ]
    for t in critical_persisted[:10]:
        failures.append(f"  [persisted-visible-both-langs] {t[:120]!r}")

    if result["svg_legend_has_html_spans"]:
        failures.append("  [svg-legend] HTML <span class=en/es> inside SVG <text> does not toggle (invalid)")

    if failures:
        msg = (
            f"Translation audit found {len(failures)} issue(s).\\n"
            f"EN visible strings: {result['en_count']}, ES: {result['es_count']}\\n"
            + "\\n".join(failures[:50])
        )
        if len(failures) > 50:
            msg += f"\\n... and {len(failures)-50} more"
        raise AssertionError(msg)


if __name__ == "__main__":
    print("Running translation toggle audit...")
    r = run_audit()
    print(f"Body: {r['body_class']}")
    print(f"EN texts: {r['en_count']}, ES texts: {r['es_count']}")
    print(f"Persisted across toggle: {len(r['persisted'])}")
    print(f"Untranslated in ES (no bilingual parent): {len(r['untranslated_es'])}")
    print(f"Diagram ES sample: {r['diagram_es']}")
    print(f"SVG legend has HTML spans: {r['svg_legend_has_html_spans']}")

    try:
        test_translation_toggle_switches_language()
        print("✓ toggle switches language")
    except Exception as e:
        print(f"✗ toggle test: {e}")
        sys.exit(1)

    try:
        test_all_user_facing_text_translates()
        print("✓ all user-facing text translates")
    except AssertionError as e:
        print(f"✗ translation audit:\\n{e}")
        sys.exit(1)

    print("All translation tests passed.")