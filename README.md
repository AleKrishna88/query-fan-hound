# 🐕 Query Fan Hound

**Segui la pista: scopri cosa cercano davvero ChatGPT e Gemini prima di risponderti.**

Query Fan Hound mostra le query di ricerca (il *fan-out*) che OpenAI e Gemini eseguono per rispondere a un prompt, insieme alle fonti che leggono e a quelle che citano nella risposta. È pensato per SEO e GEO: capire quali ricerche fa un motore AI aiuta a capire quali contenuti deve trovare.

## Funzionalità

- **Query di fan-out** per OpenAI (Responses API con `web_search`) e Gemini (grounding con Google Search).
- **Fonti lette e citate**, con il dominio di ciascuna.
- **Ripetizioni:** il fan-out cambia da un run all'altro. Con 3-5 ripetizioni vedi quali query tornano sempre.
- **Più prompt insieme**, scritti a mano o caricati da file `.txt` / `.csv`.
- **Panoramica:** ricerche per motore, domini più citati, classifica di tutte le query.
- **Export** in Excel (fogli Query e Fonti), CSV con separatore `;` e JSON completo.
- **Chiavi API inserite dall'utente** nella barra laterale: restano solo nella sessione del browser, non vengono salvate né registrate.

## Pubblicarlo su Streamlit Community Cloud

1. **Crea un repository su GitHub** (anche privato) e carica tutti i file di questa cartella, compresa la cartella nascosta `.streamlit` che contiene il tema grafico. Sul Mac, nel Finder, premi `Cmd + Shift + .` per vedere i file nascosti prima di trascinarli nella pagina di upload di GitHub.
2. Vai su [share.streamlit.io](https://share.streamlit.io), accedi con GitHub e clicca **Create app**.
3. Scegli il repository, il branch (`main`) e come file principale `app.py`.
4. Facoltativo: in **App URL** scegli un indirizzo, ad esempio `query-fan-hound`.
5. Clicca **Deploy**. Dopo un paio di minuti l'app è online.

Chi apre l'app inserisce le proprie chiavi nella barra laterale: ogni ricerca viene addebitata sull'account di chi usa la chiave, non su chi ha pubblicato l'app.

## Avviarlo in locale

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Dove prendere le chiavi API

- **OpenAI:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys). Ogni ricerca web viene addebitata.
- **Gemini:** [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Con Gemini 3 e successivi le prime 5.000 ricerche al mese sono gratuite.

## Come leggere i risultati

- **OpenAI:** `search` è una ricerca web. `open_page` e `find_in_page` indicano che il modello ha aperto una pagina o ha cercato un testo al suo interno.
- **Gemini:** i link delle fonti sono redirect di Google (`vertexaisearch...`). Il dominio viene dal titolo della fonte.
- **Nessuna ricerca:** il modello ha risposto senza cercare, cosa che succede con prompt generici o semplici.

## Limiti

- Il fan-out via API è un'approssimazione: i modelli non usano lo stesso system prompt di chatgpt.com o dell'app Gemini, quindi le query possono differire da quelle che vede un utente.
- AI Mode di Google non ha un'API e non è coperta.
- Paese della ricerca e livello di ragionamento valgono solo per OpenAI. Per Gemini il mercato lo determina la lingua del prompt.
- I modelli predefiniti (`gpt-5.5`, `gemini-3.8-flash`) si possono cambiare nella barra laterale, nella sezione **Modelli**.

## Struttura

| File | Contenuto |
|---|---|
| `app.py` | Interfaccia Streamlit |
| `fanout_core.py` | Chiamate alle API ed estrazione di query e fonti |
| `requirements.txt` | Dipendenze |
| `.streamlit/config.toml` | Tema grafico |
