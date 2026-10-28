"""Chiamate a OpenAI e Gemini ed estrazione delle query di fan-out.

Nessuna dipendenza esterna: le API key arrivano come parametro e non vengono mai salvate.
"""

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = 180

DEFAULT_MODELS = {"openai": "gpt-5.5", "gemini": "gemini-3.8-flash"}
ENGINE_LABELS = {"openai": "OpenAI", "gemini": "Gemini"}


def post_json(url, payload, headers):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(body).get("error", {}).get("message") or body
        except (ValueError, AttributeError):
            message = body
        raise RuntimeError(f"HTTP {e.code}: {message[:500]}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connessione non riuscita: {e.reason}") from None


# --- OpenAI (Responses API + web_search) ----------------------------------

def call_openai(prompt, key, model, country="", effort=""):
    tool = {"type": "web_search"}
    if country:
        tool["user_location"] = {"type": "approximate", "country": country}
    payload = {
        "model": model,
        "input": prompt,
        "tools": [tool],
        "tool_choice": "auto",
        "include": ["web_search_call.action.sources"],
    }
    if effort:
        payload["reasoning"] = {"effort": effort}
    raw = post_json("https://api.openai.com/v1/responses", payload, {"Authorization": f"Bearer {key}"})
    return raw, parse_openai(raw)


def parse_openai(raw):
    queries, sources, answer = [], {}, []

    def add_source(url, title="", cited=False):
        if not url:
            return
        src = sources.setdefault(url, {"url": url, "title": "", "cited": False})
        src["title"] = src["title"] or title or ""
        src["cited"] = src["cited"] or cited

    for item in raw.get("output", []):
        if item.get("type") == "web_search_call":
            action = item.get("action") or {}
            kind = action.get("type", "search")
            if kind == "search":
                texts = action.get("queries") or ([action["query"]] if action.get("query") else [])
                for text in texts:
                    queries.append({"text": text, "type": "search"})
                for src in action.get("sources") or []:
                    add_source(src.get("url"), src.get("title", ""))
            elif kind == "open_page":
                queries.append({"text": action.get("url", ""), "type": "open_page"})
                add_source(action.get("url"))
            elif kind == "find_in_page":
                text = f"{action.get('pattern', '')}  ⟶  {action.get('url', '')}"
                queries.append({"text": text, "type": "find_in_page"})
        elif item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") != "output_text":
                    continue
                answer.append(part.get("text", ""))
                for ann in part.get("annotations", []):
                    if ann.get("type") == "url_citation":
                        add_source(ann.get("url"), ann.get("title", ""), cited=True)

    return {
        "model": raw.get("model", ""),
        "queries": queries,
        "sources": list(sources.values()),
        "answer": "\n".join(answer).strip(),
    }


# --- Gemini (generateContent + google_search) -----------------------------

def call_gemini(prompt, key, model, country="", effort=""):
    # Gemini non accetta una posizione utente: la lingua del prompt guida il mercato.
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
    }
    raw = post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        payload,
        {"x-goog-api-key": key},
    )
    return raw, parse_gemini(raw, model)


def parse_gemini(raw, model=""):
    cand = (raw.get("candidates") or [{}])[0]
    meta = cand.get("groundingMetadata") or {}
    queries = [{"text": q, "type": "search"} for q in meta.get("webSearchQueries", [])]

    cited_idx = set()
    for support in meta.get("groundingSupports", []):
        cited_idx.update(support.get("groundingChunkIndices", []))

    sources = []
    for i, chunk in enumerate(meta.get("groundingChunks", [])):
        web = chunk.get("web") or {}
        if web.get("uri"):
            # uri è un redirect di Google (vertexaisearch...); title di solito è il dominio della fonte.
            sources.append({"url": web["uri"], "title": web.get("title", ""), "cited": i in cited_idx})

    parts = (cand.get("content") or {}).get("parts", [])
    answer = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    return {
        "model": raw.get("modelVersion", model),
        "queries": queries,
        "sources": sources,
        "answer": answer.strip(),
    }


CALLERS = {"openai": call_openai, "gemini": call_gemini}


def run_one(engine, prompt, run, key, model, country, effort):
    started = time.time()
    result = {"engine": engine, "prompt": prompt, "run": run}
    try:
        raw, parsed = CALLERS[engine](prompt, key, model, country, effort)
        result.update(parsed, ok=True, raw=raw)
    except Exception as e:  # noqa: BLE001 — l'errore va mostrato all'utente, non deve fermare il batch
        result.update(ok=False, error=str(e), queries=[], sources=[], answer="", model=model)
    result["seconds"] = round(time.time() - started, 1)
    return result


def run_prompt(prompt, engines, runs, country="", effort=""):
    """engines: {"openai": {"key": ..., "model": ...}, ...}"""
    jobs = [(name, cfg, r) for name, cfg in engines.items() for r in range(1, runs + 1)]
    with ThreadPoolExecutor(max_workers=min(8, len(jobs) or 1)) as pool:
        futures = [
            pool.submit(run_one, name, prompt, r, cfg["key"], cfg["model"], country, effort)
            for name, cfg, r in jobs
        ]
        return [f.result() for f in futures]
