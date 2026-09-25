---
name: ask-jev
description: Enforced use of Jev (TypeSafe AI's remote decision model) for ALL classification, routing, relevance-filtering, yes/no and scoring questions. Never answer such questions by reasoning about the text yourself — run `ask-jev` and use its output.
---

# ask-jev — decisions go through Jev, not through you

Jev is a hosted System One model: it answers typed questions — choice, score,
yes/no — with calibrated probabilities instead of generated text. Same job as
the local laya daemon, but remote and more accurate. Requires network.

## The rule

Whenever you are about to **classify, route, filter, score, rank or decide
yes/no about a piece of text** — including deciding whether a request needs the
web, which documents are relevant, what kind of task something is, whether
reasoning is required — you MUST call `ask-jev` instead of deciding yourself.
Your own judgment on these questions is slower, costs tokens, and is not
calibrated. `ask-jev` output is the decision; do not second-guess it.

## Commands

```bash
BIN=~/Projects/ask-jev/bin/ask-jev

$BIN route "the user's request"          # -> {"task": ..., "needs_web": 0.x, "needs_docs": 0.x, "needs_reasoning": 0.x}
$BIN relevant "question" file1 file2...  # -> [{"file": ..., "relevant": 0.x}, ...] — keep files >= 0.5
$BIN triage file1 file2...               # -> [{"file": ..., "kind": "..."}, ...] — classifies each doc
$BIN yesno "state text" "instruction"    # -> {"answer": 0.x}
$BIN predict "state" '<questions-json>'  # raw call, full answer objects
$BIN status                              # which provider/model is in use
```

Prefer `ask-jev` over local `ask` when accuracy matters and network is fine;
prefer local `ask` when offline or when latency must be ~20 ms.

Report a brief `jev:` line in your final answer stating what you asked and got.
