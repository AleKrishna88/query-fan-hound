"""Query Fan Hound: fiuta le query di fan-out di OpenAI e Gemini."""

import csv
import html
import io
import json
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from fanout_core import DEFAULT_MODELS, ENGINE_LABELS, run_prompt

st.set_page_config(page_title="Query Fan Hound", page_icon="🐕", layout="wide")

ENGINE_COLORS = {"openai": "#10A37F", "gemini": "#5B8CFF"}

LOGO = """
<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Query Fan Hound">
  <defs><linearGradient id="qfh" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#FFB547"/><stop offset="1" stop-color="#FF5E62"/></linearGradient></defs>
  <circle cx="32" cy="32" r="31" fill="url(#qfh)"/>
  <path d="M17 23 C21 14 35 12 41 18 L49 23 C53 25 53 31 49 32 L40 33 C38 40 32 46 24 46 C17 46 13 40 13 32 C13 28 14 25 17 23 Z" fill="#FFF6EC"/>
  <path d="M20 21 C13 24 11 36 15 46 C17 51 24 49 24 43 C25 35 26 26 20 21 Z" fill="#6B3E26"/>
  <circle cx="50" cy="26.5" r="2.8" fill="#2B1A12"/>
  <circle cx="35" cy="22" r="1.9" fill="#2B1A12"/>
  <g stroke="#FFF6EC" stroke-width="2.4" stroke-linecap="round">
    <path d="M55 22 L59.5 18"/><path d="M56.5 27 L61.5 27"/><path d="M55 32 L59.5 36"/>
  </g>
</svg>
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="st-"]:not([data-testid="stIconMaterial"]), input, textarea, button { font-family: 'Inter', sans-serif; }
h1, h2, h3, .qfh-title { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -0.02em; }
.block-container { padding-top: 2.2rem; max-width: 1240px; }

.qfh-hero { position: relative; overflow: hidden; border-radius: 22px; padding: 30px 34px; margin-bottom: 22px;
  background: radial-gradient(circle at 92% -10%, rgba(255,94,98,.35), transparent 45%),
              radial-gradient(circle at 0% 120%, rgba(255,181,71,.25), transparent 50%), #171A2B;
  border: 1px solid rgba(255,255,255,.07); }
.qfh-hero-row { display: flex; align-items: center; gap: 20px; }
.qfh-hero svg { width: 78px; height: 78px; flex: none; filter: drop-shadow(0 8px 22px rgba(255,94,98,.35)); }
.qfh-title { font-size: 46px !important; font-weight: 700; line-height: 1.05 !important; margin: 0 !important; padding: 0 0 4px;
  background: linear-gradient(90deg, #FFB547, #FF5E62 60%, #FF8FB1); -webkit-background-clip: text; background-clip: text; color: transparent; }
.qfh-tag { color: #C9CBE0; font-size: 17px !important; margin: 6px 0 0 !important; }
.qfh-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
.qfh-pill { font-size: 13px; color: #E9EAF5; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1);
  border-radius: 999px; padding: 5px 12px; }

.qfh-side-brand { display: flex; align-items: center; gap: 10px; margin: -6px 0 6px; }
.qfh-side-brand svg { width: 42px; height: 42px; }
.qfh-side-brand b { font-family: 'Space Grotesk', sans-serif; font-size: 20px; color: inherit; }
.qfh-note { font-size: 12.5px; color: #9EA3C0; line-height: 1.45; }

.qfh-engine { border-radius: 16px; padding: 14px 16px 6px; background: #1B1F33; border: 1px solid rgba(255,255,255,.06);
  border-top: 4px solid var(--c); margin-bottom: 10px; }
.qfh-engine-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
.qfh-engine-head b { font-family: 'Space Grotesk', sans-serif; font-size: 19px; color: #fff; }
.qfh-engine-head span { font-size: 12px; color: #9EA3C0; }
.qfh-label { font-size: 11.5px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #9EA3C0; margin: 12px 0 6px; }
.qfh-q { display: flex; gap: 10px; align-items: flex-start; padding: 7px 10px; margin: 5px 0; border-radius: 10px;
  background: rgba(255,255,255,.04); color: #EDEEF7; font-size: 14.5px; overflow-wrap: anywhere; }
.qfh-q .n { flex: none; min-width: 26px; text-align: center; font-size: 12px; font-weight: 600; padding: 2px 6px;
  border-radius: 6px; background: var(--c); color: #0F1220; }
.qfh-q .t { font-size: 11px; color: #9EA3C0; border: 1px solid rgba(255,255,255,.15); border-radius: 5px; padding: 0 5px; margin-left: auto; flex: none; }
.qfh-run { font-size: 12px; color: #9EA3C0; margin: 10px 0 2px; }
.qfh-empty { font-size: 14px; color: #9EA3C0; font-style: italic; padding: 6px 0; }
.qfh-err { font-size: 14px; color: #FF8A80; padding: 6px 0; }

[data-testid="stMetric"] { background: #1B1F33; border: 1px solid rgba(255,255,255,.06); border-radius: 16px; padding: 14px 18px; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { font-family: 'Space Grotesk', sans-serif; color: #FFFFFF !important; }
/* Colori espliciti: le card restano scure anche se Streamlit è in tema chiaro. */
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color: #B4B8D4 !important; }
.stButton > button[kind="primary"] { background: linear-gradient(90deg, #FFB547, #FF5E62); border: 0; color: #1A0E08; font-weight: 700; }
.stButton > button[kind="primary"]:hover { filter: brightness(1.06); color: #1A0E08; }
.qfh-footer { font-size: 12.5px; color: #8A8FAE; margin-top: 30px; border-top: 1px solid rgba(255,255,255,.07); padding-top: 14px; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

if "results" not in st.session_state:
    st.session_state.results = []


# --- Barra laterale: chiavi e impostazioni -----------------------------------

with st.sidebar:
    st.markdown(f'<div class="qfh-side-brand">{LOGO.replace(chr(10), "")}<b>Query Fan Hound</b></div>',
                unsafe_allow_html=True)

    st.subheader("🔑 Chiavi API")
    openai_key = st.text_input("OpenAI API key", type="password", placeholder="sk-...",
                               help="Crea la chiave su platform.openai.com/api-keys")
    gemini_key = st.text_input("Gemini API key", type="password", placeholder="AIza...",
                               help="Crea la chiave su aistudio.google.com/apikey")
    st.markdown(
        '<p class="qfh-note">Le chiavi restano solo in questa sessione del browser: non vengono salvate, '
        "registrate né condivise. Ricaricando la pagina vanno reinserite.</p>",
        unsafe_allow_html=True,
    )

    st.subheader("🎯 Motori")
    use_openai = st.toggle("OpenAI", value=bool(openai_key), disabled=not openai_key)
    use_gemini = st.toggle("Gemini", value=bool(gemini_key), disabled=not gemini_key)

    st.subheader("⚙️ Impostazioni")
    runs = st.slider("Ripetizioni per prompt", 1, 5, 1,
                     help="Il fan-out cambia da un run all'altro: con più ripetizioni vedi quali query tornano sempre.")
    country = st.selectbox(
        "Paese della ricerca (OpenAI)",
        ["IT", "ES", "FR", "DE", "GB", "US", ""],
        format_func=lambda c: {"IT": "🇮🇹 Italia", "ES": "🇪🇸 Spagna", "FR": "🇫🇷 Francia", "DE": "🇩🇪 Germania",
                               "GB": "🇬🇧 Regno Unito", "US": "🇺🇸 Stati Uniti", "": "Nessuno"}[c],
    )
    effort = st.selectbox(
        "Ragionamento (OpenAI)", ["medium", "low", "high", ""],
        format_func=lambda e: {"low": "Basso", "medium": "Medio", "high": "Alto", "": "Non inviare"}[e],
        help="Più ragionamento di solito significa più ricerche (e più costi). 'Non inviare' per modelli come gpt-4.1.",
    )
    with st.expander("Modelli"):
        openai_model = st.text_input("Modello OpenAI", DEFAULT_MODELS["openai"])
        gemini_model = st.text_input("Modello Gemini", DEFAULT_MODELS["gemini"])


# --- Intestazione ---------------------------------------------------------

# Niente righe indentate nell'HTML: per il Markdown di Streamlit diventerebbero blocchi di codice.
PILLS = ["🐾 Query di fan-out", "🔗 Fonti lette e citate", "🔁 Ripetizioni a confronto", "📥 Export CSV ed Excel"]
st.markdown(
    '<div class="qfh-hero"><div class="qfh-hero-row">' + LOGO.replace("\n", "")
    + '<div><div class="qfh-title">Query Fan Hound</div>'
    + '<div class="qfh-tag">Segui la pista: scopri cosa cercano davvero ChatGPT e Gemini prima di risponderti.</div>'
    + '</div></div><div class="qfh-pills">'
    + "".join(f'<span class="qfh-pill">{p}</span>' for p in PILLS)
    + "</div></div>",
    unsafe_allow_html=True,
)


# --- Input ----------------------------------------------------------------

def prompts_from_file(upload):
    text = upload.getvalue().decode("utf-8-sig", errors="replace")
    if upload.name.lower().endswith(".csv"):
        try:
            dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = [r[0].strip() for r in csv.reader(text.splitlines(), dialect) if r and r[0].strip()]
        if rows and rows[0].lower() in ("prompt", "query", "keyword", "domanda"):
            rows = rows[1:]
        return rows
    return [line.strip() for line in text.splitlines() if line.strip()]


left, right = st.columns([3, 2], gap="large")
with left:
    typed = st.text_area(
        "Prompt da analizzare (uno per riga)",
        height=150,
        placeholder="migliori viaggi di gruppo in Giappone per under 35\nquando andare in Islanda per vedere l'aurora boreale",
    )
with right:
    upload = st.file_uploader("…oppure carica un file", type=["txt", "csv"],
                              help="TXT con un prompt per riga, oppure CSV con il prompt nella prima colonna.")
    st.caption("I prompt del file si aggiungono a quelli scritti a sinistra.")

prompts = [p.strip() for p in typed.splitlines() if p.strip()]
if upload:
    prompts += prompts_from_file(upload)

engines = {}
if use_openai and openai_key:
    engines["openai"] = {"key": openai_key, "model": openai_model.strip() or DEFAULT_MODELS["openai"]}
if use_gemini and gemini_key:
    engines["gemini"] = {"key": gemini_key, "model": gemini_model.strip() or DEFAULT_MODELS["gemini"]}

b1, b2, _ = st.columns([2.4, 1.3, 2.3])
go = b1.button("🐾 Sguinzaglia il segugio", type="primary", width="stretch", disabled=not (prompts and engines))
if b2.button("Pulisci risultati", width="stretch", disabled=not st.session_state.results):
    st.session_state.results = []
    st.rerun()

if not engines:
    st.info("Inserisci almeno una API key nella barra laterale per iniziare.", icon="🔑")
elif prompts:
    calls = len(prompts) * len(engines) * runs
    st.caption(f"{len(prompts)} prompt × {len(engines)} motori × {runs} ripetizioni = {calls} chiamate API")

if go:
    results = []
    bar = st.progress(0.0, text="Il segugio è sulle tracce…")
    for i, prompt in enumerate(prompts):
        bar.progress(i / len(prompts), text=f"Fiuto il prompt {i + 1} di {len(prompts)}: {prompt[:70]}")
        results += run_prompt(prompt, engines, runs, country, effort)
    bar.empty()
    st.session_state.results = results
    errors = [r for r in results if not r["ok"]]
    if errors:
        st.warning(f"{len(errors)} chiamate non sono andate a buon fine: trovi il dettaglio nei risultati.", icon="⚠️")
    else:
        st.toast("Pista trovata! 🐕", icon="✅")


# --- Risultati ------------------------------------------------------------

def domain_of(src):
    host = urlparse(src["url"]).netloc.lower()
    if "vertexaisearch" in host or not host:
        return (src.get("title") or host).lower().removeprefix("www.")
    return host.removeprefix("www.")


def queries_df(results):
    return pd.DataFrame(
        [{"prompt": r["prompt"], "motore": ENGINE_LABELS[r["engine"]], "modello": r["model"], "run": r["run"],
          "n": i, "tipo": q["type"], "query": q["text"]}
         for r in results for i, q in enumerate(r["queries"], 1)],
        columns=["prompt", "motore", "modello", "run", "n", "tipo", "query"],
    )


def sources_df(results):
    return pd.DataFrame(
        [{"prompt": r["prompt"], "motore": ENGINE_LABELS[r["engine"]], "run": r["run"], "citata": s["cited"],
          "dominio": domain_of(s), "titolo": s["title"], "url": s["url"]}
         for r in results for s in r["sources"]],
        columns=["prompt", "motore", "run", "citata", "dominio", "titolo", "url"],
    )


def query_row(n, text, kind, color):
    tag = f'<span class="t">{html.escape(kind)}</span>' if kind != "search" else ""
    return (f'<div class="qfh-q" style="--c:{color}"><span class="n">{n}</span>'
            f"<span>{html.escape(text)}</span>{tag}</div>")


def render_engine(engine, runs_list):
    color = ENGINE_COLORS[engine]
    model = next((r["model"] for r in runs_list if r["model"]), "")
    ok_runs = [r for r in runs_list if r["ok"]]
    parts = [f'<div class="qfh-engine" style="--c:{color}"><div class="qfh-engine-head">'
             f"<b>{ENGINE_LABELS[engine]}</b><span>{html.escape(model)}</span></div>"]

    if len(runs_list) > 1 and ok_runs:
        freq = Counter(t for r in ok_runs for t in {q["text"] for q in r["queries"] if q["type"] == "search"})
        parts.append(f'<div class="qfh-label">Query più ricorrenti · {len(ok_runs)} run</div>')
        parts += [query_row(f"{n}×", t, "search", color) for t, n in freq.most_common()] or \
                 ['<div class="qfh-empty">Nessuna ricerca eseguita</div>']

    per_run = []
    for r in runs_list:
        if len(runs_list) > 1:
            per_run.append(f'<div class="qfh-run">Run {r["run"]} · {r["seconds"]}s</div>')
        if not r["ok"]:
            per_run.append(f'<div class="qfh-err">⚠️ {html.escape(r["error"])}</div>')
        elif not r["queries"]:
            per_run.append('<div class="qfh-empty">Nessuna ricerca: il modello ha risposto senza cercare.</div>')
        else:
            per_run += [query_row(i, q["text"], q["type"], color) for i, q in enumerate(r["queries"], 1)]

    # Con un solo run le query stanno nella card; con più run il dettaglio va in una sezione richiudibile.
    if len(runs_list) == 1:
        parts += ['<div class="qfh-label">Query</div>', *per_run]
    elif not ok_runs:
        parts += per_run
    st.markdown("".join(parts) + "</div>", unsafe_allow_html=True)
    if len(runs_list) > 1 and ok_runs:
        with st.expander("Dettaglio per run"):
            st.markdown(f'<div style="--c:{color}">' + "".join(per_run) + "</div>", unsafe_allow_html=True)

    sources = {}
    for r in ok_runs:
        for s in r["sources"]:
            prev = sources.setdefault(s["url"], {**s, "cited": False})
            prev["cited"] = prev["cited"] or s["cited"]
    if sources:
        df = pd.DataFrame([{"citata": s["cited"], "dominio": domain_of(s), "titolo": s["title"], "url": s["url"]}
                           for s in sources.values()]).sort_values("citata", ascending=False)
        st.markdown(f'<div class="qfh-label">Fonti · {int(df["citata"].sum())} citate su {len(df)}</div>',
                    unsafe_allow_html=True)
        st.dataframe(df, hide_index=True, width="stretch", height=min(38 + 35 * len(df), 280),
                     column_config={"citata": st.column_config.CheckboxColumn("Citata", width="small"),
                                    "url": st.column_config.LinkColumn("Link", display_text="apri ↗", width="small")})

    answered = next((r for r in ok_runs if r["answer"]), None)
    if answered:
        with st.expander(f"Risposta del modello (run {answered['run']})"):
            st.markdown(answered["answer"])


results = st.session_state.results
if results:
    qdf, sdf = queries_df(results), sources_df(results)
    search_q = qdf[qdf["tipo"] == "search"]

    st.markdown("### Cosa ha fiutato il segugio")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prompt", len({r["prompt"] for r in results}))
    m2.metric("Ricerche eseguite", len(search_q))
    m3.metric("Query uniche", search_q["query"].str.lower().nunique())
    m4.metric("Fonti citate", int(sdf.drop_duplicates(["motore", "url"])["citata"].sum()) if len(sdf) else 0)

    tab_prompt, tab_overview, tab_export = st.tabs(["🐾 Per prompt", "📊 Panoramica", "📥 Esporta"])

    with tab_prompt:
        by_prompt = {}
        for r in results:
            by_prompt.setdefault(r["prompt"], {}).setdefault(r["engine"], []).append(r)
        for i, (prompt, by_engine) in enumerate(by_prompt.items()):
            with st.expander(f"**{prompt}**", expanded=i == 0):
                cols = st.columns(len(by_engine), gap="medium")
                for col, (engine, runs_list) in zip(cols, by_engine.items()):
                    with col:
                        render_engine(engine, sorted(runs_list, key=lambda r: r["run"]))

    with tab_overview:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("#### Ricerche per motore")
            per_engine = search_q.groupby(["prompt", "motore"]).size().unstack(fill_value=0)
            if len(per_engine):
                label_colors = {ENGINE_LABELS[e]: c for e, c in ENGINE_COLORS.items()}
                st.bar_chart(per_engine, horizontal=True, color=[label_colors[c] for c in per_engine.columns])
            else:
                st.caption("Nessuna ricerca da mostrare.")
        with c2:
            st.markdown("#### Domini più citati")
            cited = sdf[sdf["citata"]].drop_duplicates(["prompt", "motore", "url"])
            if len(cited):
                top = cited.groupby("dominio").size().sort_values(ascending=False).head(12)
                st.bar_chart(top.rename("citazioni"), horizontal=True, color="#FF8A5B")
            else:
                st.caption("Nessuna fonte citata.")

        st.markdown("#### Tutte le query, dalla più frequente")
        if len(search_q):
            agg = (search_q.assign(chiave=search_q["query"].str.lower().str.strip())
                   .groupby("chiave")
                   .agg(query=("query", "first"), volte=("query", "size"),
                        motori=("motore", lambda s: ", ".join(sorted(set(s)))),
                        prompt=("prompt", "nunique"))
                   .sort_values("volte", ascending=False).reset_index(drop=True))
            st.dataframe(agg, hide_index=True, width="stretch",
                         column_config={"volte": st.column_config.ProgressColumn(
                             "Volte", format="%d", min_value=0, max_value=int(agg["volte"].max())),
                             "prompt": st.column_config.NumberColumn("Prompt diversi")})

    with tab_export:
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        export_sdf = sdf.assign(citata=sdf["citata"].map({True: "sì", False: "no"}))
        xlsx = io.BytesIO()
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            qdf.to_excel(writer, sheet_name="Query", index=False)
            export_sdf.to_excel(writer, sheet_name="Fonti", index=False)
        st.markdown("Scarica i risultati. I CSV usano il separatore `;` e si aprono già in colonne in Excel.")
        e1, e2, e3, e4 = st.columns(4)
        e1.download_button("📊 Excel (query + fonti)", xlsx.getvalue(), f"query-fan-hound-{stamp}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        e2.download_button("🐾 CSV query", qdf.to_csv(sep=";", index=False).encode("utf-8-sig"),
                           f"query-fan-hound-{stamp}-query.csv", "text/csv", width="stretch")
        e3.download_button("🔗 CSV fonti", export_sdf.to_csv(sep=";", index=False).encode("utf-8-sig"),
                           f"query-fan-hound-{stamp}-fonti.csv", "text/csv", width="stretch")
        e4.download_button("🧾 JSON completo", json.dumps(results, ensure_ascii=False, indent=2).encode("utf-8"),
                           f"query-fan-hound-{stamp}.json", "application/json", width="stretch")

st.markdown(
    '<div class="qfh-footer">Il fan-out via API è un\'approssimazione: i modelli non usano lo stesso system prompt '
    "di chatgpt.com o dell'app Gemini. Per Gemini i link delle fonti sono redirect di Google e il dominio viene dal titolo. "
    "AI Mode di Google non ha un'API e non è coperta. Ogni ricerca ha un costo sul tuo account API.</div>",
    unsafe_allow_html=True,
)
