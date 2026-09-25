"""jev-mcp — stdio MCP server exposing Jev's typed decisions as tools.

Agents spawn this once and get jev_* tools; calls go straight to whichever
remote provider is configured — no local model, no daemon. Mirrors the
laya-mcp.py surface.

    python jev-mcp.py            # needs `mcp` package on the interpreter

Providers (first configured wins): JEV_URL+JEV_API_KEY, TYPESAFE_API_KEY,
OPENCODE_API_KEY or opencode auth.json, AI_GATEWAY_API_KEY/VERCEL_OIDC_TOKEN,
CLOUDFLARE_ACCOUNT_ID+CLOUDFLARE_API_TOKEN. JEV_MODEL overrides the model id.
"""

import glob as _glob
import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from mcp.server.mcpserver import MCPServer

AUTH_JSON = os.path.expanduser("~/.local/share/opencode/auth.json")

ROUTE_Q = {
    "task": {"type": "choice", "instructions": "What kind of task is this request?",
             "criteria": {"email": "reading or replying to an email/message",
                          "document_search": "find which file/doc contains an answer",
                          "code": "write, fix or explain code",
                          "question": "answer a question from knowledge",
                          "action": "run commands, edit files, operate the machine",
                          "other": "none of the above"}},
    "needs_docs": {"type": "noul", "instructions": "Does this request require reading local files or documents?"},
    "needs_reasoning": {"type": "noul", "instructions": "Does this request require multi-step reasoning or careful analysis?"},
}

TRIAGE_Q = {
    "kind": {"type": "choice", "instructions": "What kind of message or document is this?",
             "criteria": {"invoice_or_billing": "an invoice, charge, payment, refund or billing correction",
                          "personal": "personal note, plans, recommendations or family",
                          "booking_or_itinerary": "travel booking, itinerary or tickets",
                          "notice": "delivery, legal, rent or administrative notice",
                          "work": "team updates, tasks, oncall or meetings",
                          "other": "none of the above"}},
    "urgency": {"type": "score", "instructions": "How urgent is this message?",
                "criteria": ["no time pressure", "needs attention soon", "blocking issue or hard deadline"]},
    "needs_reply": {"type": "noul", "instructions": "Does the sender expect a reply?"},
    "is_spam": {"type": "noul", "instructions": "Is this unsolicited spam, bulk marketing or a scam/phishing attempt?"},
}


def _opencode_key():
    try:
        return json.load(open(AUTH_JSON))["opencode-go"]["key"]
    except Exception:
        return None


def provider():
    """Resolve (name, url, key, model, unwrap). First configured wins."""
    if os.environ.get("JEV_URL") and os.environ.get("JEV_API_KEY"):
        u = os.environ["JEV_URL"].rstrip("/")
        return ("custom", u if u.endswith("/v1/systemone") else u + "/v1/systemone",
                os.environ["JEV_API_KEY"], os.environ.get("JEV_MODEL", "jev-latest"), False)
    if os.environ.get("TYPESAFE_API_KEY"):
        return ("typesafe", "https://api.typesafe.ai/v1/systemone",
                os.environ["TYPESAFE_API_KEY"], os.environ.get("JEV_MODEL", "jev-latest"), False)
    key = os.environ.get("OPENCODE_API_KEY") or _opencode_key()
    if key:
        return ("opencode-zen", "https://opencode.ai/zen/v1/systemone",
                key, os.environ.get("JEV_MODEL", "jev-1.13-free"), False)
    key = os.environ.get("AI_GATEWAY_API_KEY") or os.environ.get("VERCEL_OIDC_TOKEN")
    if key:
        return ("vercel-ai-gateway", "https://ai-gateway.vercel.sh/typesafe/v1/systemone",
                key, os.environ.get("JEV_MODEL", "typesafe-ai/jev"), False)
    if os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN"):
        return ("cloudflare",
                "https://api.cloudflare.com/client/v4/accounts/%s/ai/run/typesafe/jev"
                % os.environ["CLOUDFLARE_ACCOUNT_ID"],
                os.environ["CLOUDFLARE_API_TOKEN"], None, True)
    raise RuntimeError("no jev provider configured")


def _slim(result):
    out = {}
    for qid, a in (result or {}).get("answers", {}).items():
        if isinstance(a, dict):
            out[qid] = a.get("choice", a.get("score", a.get("noul", a)))
        else:
            out[qid] = a
    return out


def _post(state, questions):
    name, url, key, model, unwrap = provider()
    body = {"state": state, "questions": questions}
    if model:
        body["model"] = model
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key,
                 # cloudflare 1010 blocks the default urllib UA
                 "User-Agent": "ask-jev/1.0"})
    res = json.load(urllib.request.urlopen(req, timeout=60))
    return res.get("result", res) if unwrap else res


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return f"file: {os.path.basename(path)}\n\n" + fh.read()[:4000]


def _expand(files):
    """Expand globs and ~; keep order, drop dupes. Empty -> docs/* —
    models fumble glob arrays often."""
    if not files:
        files = ["docs/*"]
    out, seen = [], set()
    for f in files or []:
        hits = sorted(_glob.glob(os.path.expanduser(str(f)))) if _glob.has_magic(str(f)) else [os.path.expanduser(str(f))]
        for h in hits or [os.path.expanduser(str(f))]:
            if h not in seen:
                seen.add(h)
                out.append(h)
    return out


def _score_items(items, questions):
    """Parallel /v1/systemone per state — remote latency, no batch endpoint.
    Returns {file: slim answers} keyed on the readable items."""
    def one(it):
        return it["file"], _slim(_post(it["state"], questions))
    good = [it for it in items if "state" in it]
    with ThreadPoolExecutor(max_workers=8) as ex:
        return dict(ex.map(one, good))


server = MCPServer("jev", instructions=(
    "Jev is a remote calibrated decision model (TypeSafe AI): classification, "
    "filtering, ranking and yes/no scoring with probabilities, no generated "
    "text. RULES: (1) Before reading files under docs/ or deciding which "
    "documents to open, call jev_filter or jev_triage — never classify "
    "documents yourself. (2) For yes/no or classification questions about "
    "text, call jev_yesno instead of reasoning yourself. (3) For choosing "
    "among options, call jev_pick."))


@server.tool(name="jev_status", description="Which jev provider/model is configured.")
def jev_status() -> str:
    try:
        name, url, _k, model, _u = provider()
        return json.dumps({"provider": name, "endpoint": url, "model": model})
    except Exception as e:
        return json.dumps({"status": "unconfigured", "error": str(e)})


@server.tool(name="jev_route", description=(
    "Classify a request: task kind + needs_docs/needs_reasoning scores. "
    "Call first on multi-step or document-touching requests."))
def jev_route(text: str) -> str:
    return json.dumps(_slim(_post(text, ROUTE_Q)))


@server.tool(name="jev_filter", description=(
    "Score which of the given file paths are relevant to a question (0-1, ranked). "
    "Pass file paths, not contents — the server reads them. Only open files listed under 'read'."))
def jev_filter(question: str, files: list) -> str:
    items = []
    for f in _expand(files):
        try:
            items.append({"file": f, "state": _read(f)})
        except OSError as e:
            items.append({"file": f, "error": str(e)})
    scores = _score_items(items, {"relevant": {"type": "noul",
        "instructions": f"Does this text contain information that helps answer: {question}?"}})
    ranked = sorted(
        ({"file": it["file"], "relevant": scores[it["file"]].get("relevant")}
         if it["file"] in scores else it for it in items),
        key=lambda x: -(x.get("relevant") or 0))
    return json.dumps({"ranked": ranked,
                       "read": [x["file"] for x in ranked if (x.get("relevant") or 0) >= 0.5]})


@server.tool(name="jev_triage", description=(
    "Classify document files without reading them: per file returns kind, urgency, "
    "needs_reply, is_spam. Pass file paths. Never classify documents yourself."))
def jev_triage(files: list) -> str:
    items = []
    for f in _expand(files):
        try:
            items.append({"file": f, "state": _read(f)})
        except OSError as e:
            items.append({"file": f, "error": str(e)})
    scores = _score_items(items, TRIAGE_Q)
    return json.dumps([{"file": it["file"], **scores[it["file"]]} if "state" in it else it
                       for it in items])


@server.tool(name="jev_yesno", description=(
    "Yes/no or 0-1 decision about a piece of text: returns a calibrated score. "
    "Do not decide such questions yourself."))
def jev_yesno(state: str, instruction: str) -> str:
    return json.dumps(_slim(_post(state, {
        "answer": {"type": "noul", "instructions": instruction}})))


@server.tool(name="jev_pick", description=(
    "Choose the single best option among candidates, in context. Pass option names as a list."))
def jev_pick(state: str, options: list, instruction: str = "Which option fits best?") -> str:
    criteria = {str(o)[:40]: f"the option: {o}" for o in options}
    return json.dumps(_slim(_post(state, {
        "pick": {"type": "choice", "instructions": instruction, "criteria": criteria}})))


@server.tool(name="jev_decide", description=(
    "Escape hatch: arbitrary typed decision. questions is a map of name -> "
    "{type: 'choice'|'score'|'noul', instructions, criteria?}."))
def jev_decide(state: str, questions: dict) -> str:
    return json.dumps(_slim(_post(state, questions)))


if __name__ == "__main__":
    server.run()
