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

## Where it fits

- **Agent skill**: `SKILL.md` mirrors ask-laya's rule — every
  classify/route/filter/score/yes-no decision goes through `ask-jev`. Point
  any agent's skill loader at it, or drop an `AGENTS.md` with the rule into
  the workspace.
- **Not a subagent**: Jev returns structured values, not text — it can't be
  an opencode subagent/model. The right wiring is a tool the *existing* agent
  calls (this CLI, or an MCP wrapper), same pattern as laya.
- **vs local laya**: jev is more accurate and needs no GPU slot; laya is
  ~20 ms and works offline. They speak the same question schema, so a gate
  like `local-laya/laya-gate.py` could fall back to jev when the daemon is
  down (not yet implemented).

Verified live on `jev-1.13-free` via OpenCode Zen: doc relevance gave 0.97 vs
~0.01 separation, and triage classified all 5 fixture docs correctly.
