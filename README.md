# ask-jev

Agent skill + CLI for [Jev](https://typesafe.ai), TypeSafe AI's hosted
System One model — the remote counterpart to
[ask-laya](https://github.com/v3moreno/ask-laya) (local laya daemon). Same
typed-decision interface (choice / score / noul over a state), same wire
format (`POST …/v1/systemone`), but runs on TypeSafe's frontier decision model
instead of the local distilled checkpoint: better calibration, no GPU/CPU
footprint, needs network.

## Providers

All expose the same `{state, questions}` → `{answers}` API; pick one:

| Provider | Endpoint | Auth env | Model id | Notes |
|---|---|---|---|---|
| TypeSafe direct | `api.typesafe.ai/v1/systemone` | `TYPESAFE_API_KEY` | `jev-latest` | official; early-access waitlist |
| **OpenCode Zen** | `opencode.ai/zen/v1/systemone` | `OPENCODE_API_KEY` | `jev-1.13`, **`jev-1.13-free`** | free tier exists; zero-config if opencode is already authed (reads `opencode-go` from `auth.json`) |
| Vercel AI Gateway | `ai-gateway.vercel.sh/typesafe/v1/systemone` | `AI_GATEWAY_API_KEY` or `VERCEL_OIDC_TOKEN` | `typesafe-ai/jev` | typesafe-compat path; native API is `POST /v1/evaluate`, AI SDK `evaluate()` |
| Cloudflare Workers AI | `api.cloudflare.com/client/v4/accounts/<id>/ai/run/typesafe/jev` | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` | `typesafe/jev` | response wrapped in `{result: …}` — handled, untested |
| OpenRouter, NanoGPT, Vivgrid | provider-specific | `OPENROUTER_API_KEY` etc. | `typesafe/jev-latest` | listed hosts; use `JEV_URL`/`JEV_API_KEY`/`JEV_MODEL` for any compatible endpoint |

## CLI

```bash
BIN=~/Projects/ask-jev/bin/ask-jev

$BIN route "the user's request"          # task + needs_web/docs/reasoning scores
$BIN relevant "question" file1 file2...  # relevance per doc; keep >= 0.5
$BIN triage file1 file2...               # message type per doc
$BIN yesno "state" "instruction"         # yes/no score
$BIN predict "state" '<questions-json>'  # raw call, full answers
$BIN status                              # resolved provider + model
```

Provider resolution order (first configured wins):
`JEV_URL`+`JEV_API_KEY` → `TYPESAFE_API_KEY` → `OPENCODE_API_KEY` or
opencode `auth.json` → `AI_GATEWAY_API_KEY`/`VERCEL_OIDC_TOKEN` →
`CLOUDFLARE_ACCOUNT_ID`+`CLOUDFLARE_API_TOKEN`. `JEV_MODEL` overrides the
model id.

## MCP server

`jev-mcp.py` exposes the same tool surface as `local-laya/laya-mcp.py` —
`jev_route`, `jev_filter`, `jev_triage`, `jev_yesno`, `jev_pick`,
`jev_decide`, `jev_status` — over stdio, for agents that take MCP servers
(needs the `mcp` package). File scoring is parallel across the provider
(jev has no batch endpoint). Register like any MCP server, e.g. opencode:

```json
{"mcp": {"jev": {"type": "local",
  "command": ["python3", "/path/to/jev-mcp.py"], "enabled": true}}}
```

`laya-gate.py` (local-laya ≥ `873e0a7`) and the ask-laya opencode plugin
already credit `jev_*` MCP calls and `ask-jev` shell commands — jev is a
drop-in decision layer wherever laya enforcement is installed.

## Where it fits

- **Agent skill**: `SKILL.md` mirrors ask-laya's rule — every
  classify/route/filter/score/yes-no decision goes through `ask-jev`. Point
  any agent's skill loader at it, or drop an `AGENTS.md` with the rule into
  the workspace (see `smoke/AGENTS.md`).
- **Not a subagent**: Jev returns structured values, not text — it can't be
  an opencode subagent/model. The right wiring is a tool the *existing* agent
  calls (this CLI or the MCP server), same pattern as laya.
- **vs local laya**: jev is more accurate and needs no GPU slot; laya is
  ~20 ms and works offline. Same question schema — pick per environment, or
  let both be registered and steer via AGENTS.md.

## Tested

`smoke/` — the same 6-test suite as ask-laya, run against opencode +
gpt-6-luna with laya's MCP disabled (jev-only): **6/6 correct, every test
routed through jev** (`jev_jev_*` MCP tools + `ask-jev` CLI), doc gate
opened by both paths. Direct CLI checks on `jev-1.13-free`: doc relevance
0.97 vs ~0.01 separation, triage correct on all 5 fixtures. Reproduce:
`cd smoke && ./run.sh`.
