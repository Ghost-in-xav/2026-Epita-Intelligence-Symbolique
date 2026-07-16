"""Live-demo web UI.

A single-page app that runs the pipeline and **streams each attempt live**
(Server-Sent Events): you watch attempt 1 get rejected with the exact Z3
constraints it violated, then the re-prompt correct it. Built for presenting.

    uv run m1 serve            # then open http://127.0.0.1:8000
"""
from __future__ import annotations

import json
import queue
import threading

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from .llm import LLMError, make_provider
from .llm.presets import list_presets
from .pipeline import run_pipeline
from .problems import ALL_PROBLEMS, get_problem
from .strategies import get_strategy, strategy_names

app = FastAPI(title="M1 — Pipeline LLM + vérificateur symbolique")


def _attempt_payload(att) -> dict:
    return {
        "index": att.index,
        "ok": att.result.ok,
        "status": att.result.error_category,
        "parsed": att.parsed,
        "violated": att.result.violated,
        "message": att.result.message,
        "raw": att.response_text,
        "output_tokens": att.output_tokens,
    }


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/api/meta")
def meta():
    return JSONResponse(
        {
            "problems": [
                {"id": p.id, "title": p.title, "domain": p.domain, "satisfiable": p.satisfiable}
                for p in ALL_PROBLEMS
            ],
            "strategies": strategy_names(),
            "providers": ["mock", *[pr.name for pr in list_presets()]],
            "preset_models": {pr.name: pr.default_model for pr in list_presets()},
        }
    )


@app.get("/api/problem/{pid}")
def problem(pid: str):
    try:
        p = get_problem(pid)
    except KeyError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    return JSONResponse(
        {"id": p.id, "title": p.title, "statement": p.statement,
         "answer_format": p.answer_format, "satisfiable": p.satisfiable}
    )


@app.get("/api/run")
def run(provider: str = "anthropic", model: str = "", strategy: str = "counterexample",
        problem: str = "linear_arith", max_attempts: int = 4, temperature: float = 0.0,
        mock_fail_first: int = 0):
    q: queue.Queue = queue.Queue()

    def worker():
        try:
            prob = get_problem(problem)
            strat = get_strategy(strategy)
            prov = make_provider(provider, model=model or None, mock_fail_first=mock_fail_first)
            q.put(("start", {"problem": prob.id, "strategy": strat.name,
                             "provider": prov.name, "model": prov.model,
                             "max_attempts": max_attempts}))
            result = run_pipeline(
                prob, prov, strat, max_attempts=max_attempts, temperature=temperature,
                on_attempt=lambda att: q.put(("attempt", _attempt_payload(att))),
            )
            q.put(("done", {"solved": result.solved, "n_attempts": result.n_attempts}))
        except LLMError as exc:
            q.put(("error", {"message": f"LLM error: {exc}"}))
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            q.put(("error", {"message": f"{type(exc).__name__}: {exc}"}))
        finally:
            q.put((None, None))

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            event, data = q.get()
            if event is None:
                break
            yield _sse(event, data)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(_INDEX_HTML)


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    load_dotenv()
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")


_INDEX_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>M1 — Pipeline LLM + vérificateur symbolique</title>
<style>
  :root{
    --bg:#0f1419; --panel:#1c2530; --panel2:#161e27; --text:#e6e6e6;
    --muted:#8a98a8; --blue:#6cb6ff; --gold:#f0c674; --green:#7bd88f;
    --red:#ff7b72; --border:#2a3744;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  header{padding:18px 28px;border-bottom:1px solid var(--border);
    display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
  header h1{font-size:20px;margin:0;color:var(--blue)}
  header .sub{color:var(--muted);font-size:14px}
  .wrap{display:grid;grid-template-columns:380px 1fr;gap:0;height:calc(100vh - 61px)}
  .left{padding:20px 24px;border-right:1px solid var(--border);overflow:auto}
  .right{padding:20px 28px;overflow:auto}
  label{display:block;font-size:12px;color:var(--muted);
    text-transform:uppercase;letter-spacing:.04em;margin:14px 0 6px}
  select,input{width:100%;background:var(--panel2);color:var(--text);
    border:1px solid var(--border);border-radius:8px;padding:9px 10px;font-size:14px}
  .row{display:flex;gap:12px}
  .row>div{flex:1}
  button{margin-top:20px;width:100%;background:var(--blue);color:#06121e;
    border:0;border-radius:9px;padding:12px;font-size:15px;font-weight:700;cursor:pointer}
  button:disabled{opacity:.5;cursor:default}
  .statement{margin-top:18px;background:var(--panel2);border:1px solid var(--border);
    border-radius:10px;padding:14px;font-size:13.5px;white-space:pre-wrap;line-height:1.5}
  .fmt{margin-top:10px;color:var(--green);font-family:ui-monospace,Menlo,Consolas,monospace;
    font-size:12px;white-space:pre-wrap}
  .badge{display:inline-block;font-size:11px;padding:2px 9px;border-radius:999px;
    font-weight:700;margin-left:8px;vertical-align:middle}
  .b-sat{background:#1e3a2a;color:var(--green)}
  .b-unsat{background:#3a1e1e;color:var(--red)}
  .meta{color:var(--muted);font-size:13px;margin-bottom:14px}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:12px;
    padding:14px 16px;margin-bottom:14px;animation:pop .25s ease}
  @keyframes pop{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .card.accepted{border-color:#2c5a3a}
  .card.rejected{border-color:#5a2c2c}
  .card h3{margin:0 0 8px;font-size:15px;display:flex;align-items:center}
  .st{font-size:12px;font-weight:700;padding:3px 10px;border-radius:999px}
  .st.ok{background:#1e3a2a;color:var(--green)}
  .st.no{background:#3a1e1e;color:var(--red)}
  .ans{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;
    background:var(--panel2);border-radius:8px;padding:8px 10px;margin:8px 0;
    overflow-x:auto;white-space:pre-wrap}
  .viol{margin:6px 0 0;padding-left:0;list-style:none}
  .viol li{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;
    color:var(--gold);padding:2px 0}
  .viol li::before{content:"✗ ";color:var(--red)}
  details{margin-top:8px}
  summary{cursor:pointer;color:var(--muted);font-size:12px}
  details pre{background:var(--panel2);border-radius:8px;padding:10px;font-size:12px;
    overflow-x:auto;color:var(--muted);white-space:pre-wrap}
  .verdict{padding:14px 18px;border-radius:12px;font-size:17px;font-weight:700;margin:6px 0 18px}
  .verdict.win{background:#173026;color:var(--green);border:1px solid #2c5a3a}
  .verdict.lose{background:#301717;color:var(--red);border:1px solid #5a2c2c}
  .err{background:#301717;color:var(--red);border:1px solid #5a2c2c;
    border-radius:10px;padding:14px;margin-top:14px}
  .hint{color:var(--muted);font-size:13px;margin-top:40px;text-align:center}
  .spin{display:inline-block;width:14px;height:14px;border:2px solid var(--muted);
    border-top-color:var(--blue);border-radius:50%;animation:sp .7s linear infinite;
    margin-left:10px;vertical-align:middle}
  @keyframes sp{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<header>
  <h1>M1 · Pipeline LLM + vérificateur symbolique</h1>
  <span class="sub">le LLM propose · Z3 vérifie · re-prompt sur contre-exemple</span>
</header>
<div class="wrap">
  <div class="left">
    <label>Problème</label>
    <select id="problem"></select>
    <label>Fournisseur LLM</label>
    <div class="row">
      <div><select id="provider"></select></div>
      <div><input id="model" placeholder="modèle (défaut du preset)"/></div>
    </div>
    <label>Stratégie de re-prompting</label>
    <select id="strategy"></select>
    <div class="row">
      <div><label>Essais max</label><input id="max" type="number" value="4" min="1" max="10"/></div>
      <div><label>Température</label><input id="temp" type="number" value="0" min="0" max="2" step="0.1"/></div>
      <div><label>Mock: échecs forcés</label><input id="fail" type="number" value="0" min="0" max="9"/></div>
    </div>
    <button id="run">▶  Lancer</button>
    <div class="statement" id="statement">…</div>
    <div class="fmt" id="fmt"></div>
  </div>
  <div class="right">
    <div class="meta" id="meta"></div>
    <div id="verdict"></div>
    <div id="attempts"></div>
    <div class="hint" id="hint">Choisis un problème et un fournisseur, puis lance.
      Astuce démo : provider <b>mock</b> + échecs forcés = 2 pour voir la boucle CEGIS sans clé API.</div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
let es = null;

async function init(){
  const meta = await (await fetch('/api/meta')).json();
  for(const p of meta.problems){
    const o=document.createElement('option');o.value=p.id;
    o.textContent=`${p.title}  ${p.satisfiable?'':'(UNSAT)'}`;$('problem').appendChild(o);
  }
  for(const pr of meta.providers){
    const o=document.createElement('option');o.value=pr;o.textContent=pr;$('provider').appendChild(o);
  }
  for(const s of meta.strategies){
    const o=document.createElement('option');o.value=s;o.textContent=s;
    if(s==='counterexample')o.selected=true;$('strategy').appendChild(o);
  }
  $('provider').value='anthropic';
  window._models=meta.preset_models;
  $('problem').onchange=loadProblem;
  $('provider').onchange=()=>{$('model').placeholder=window._models[$('provider').value]||'modèle';};
  $('provider').onchange();
  await loadProblem();
}

async function loadProblem(){
  const p = await (await fetch('/api/problem/'+$('problem').value)).json();
  const badge = p.satisfiable ? '<span class="badge b-sat">satisfiable</span>'
                              : '<span class="badge b-unsat">UNSAT — piège</span>';
  $('statement').innerHTML = badge + '\n\n' + p.statement;
  $('fmt').textContent = 'format attendu : ' + p.answer_format;
}

function card(a){
  const div=document.createElement('div');
  div.className='card '+(a.ok?'accepted':'rejected');
  let html=`<h3>Tentative ${a.index+1}
    <span style="flex:1"></span>
    <span class="st ${a.ok?'ok':'no'}">${a.ok?'ACCEPTÉ':a.status}</span></h3>`;
  html+=`<div class="ans">${a.parsed?JSON.stringify(a.parsed):'(aucun JSON extrait)'}</div>`;
  if(a.violated && a.violated.length){
    html+='<div style="color:var(--muted);font-size:12px">contraintes violées (renvoyées au LLM) :</div>';
    html+='<ul class="viol">'+a.violated.map(v=>`<li>${escapeHtml(v)}</li>`).join('')+'</ul>';
  } else if(!a.ok && a.message){
    html+=`<div style="color:var(--red);font-size:13px">${escapeHtml(a.message)}</div>`;
  }
  html+=`<details><summary>sortie brute du LLM</summary><pre>${escapeHtml(a.raw||'')}</pre></details>`;
  div.innerHTML=html;
  return div;
}
function escapeHtml(s){return (s+'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

function start(){
  if(es) es.close();
  $('attempts').innerHTML=''; $('verdict').innerHTML=''; $('hint').style.display='none';
  $('run').disabled=true;
  const q=new URLSearchParams({
    provider:$('provider').value, model:$('model').value, strategy:$('strategy').value,
    problem:$('problem').value, max_attempts:$('max').value, temperature:$('temp').value,
    mock_fail_first:$('fail').value });
  es=new EventSource('/api/run?'+q.toString());
  es.addEventListener('start',e=>{
    const d=JSON.parse(e.data);
    $('meta').innerHTML=`problème <b>${d.problem}</b> · stratégie <b>${d.strategy}</b>
      · ${d.provider}/${d.model} · ≤ ${d.max_attempts} essais <span class="spin"></span>`;
  });
  es.addEventListener('attempt',e=>$('attempts').appendChild(card(JSON.parse(e.data))));
  es.addEventListener('done',e=>{
    const d=JSON.parse(e.data);
    $('verdict').innerHTML=`<div class="verdict ${d.solved?'win':'lose'}">
      ${d.solved?'✓ RÉSOLU':'✗ NON RÉSOLU'} — ${d.n_attempts} tentative(s)</div>`;
    finish();
  });
  es.addEventListener('error',e=>{
    if(e.data){ $('verdict').innerHTML=`<div class="err">${escapeHtml(JSON.parse(e.data).message)}</div>`; }
    finish();
  });
}
function finish(){ if(es)es.close(); es=null;
  $('run').disabled=false; const m=$('meta'); const sp=m.querySelector('.spin'); if(sp)sp.remove(); }

$('run').onclick=start;
init();
</script>
</body>
</html>"""
