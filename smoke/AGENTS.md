# Project rules

This project has the `ask-jev` CLI at ~/Projects/ask-jev/bin/ask-jev backed by
the Jev decision model (TypeSafe AI). Read ~/Projects/ask-jev/SKILL.md and
follow it: ALL classification, routing, relevance-filtering, ranking and
yes/no decisions about text MUST go through `ask-jev` — never decide them
yourself. When you use it, report one line like `jev: route=email kept 2/5 docs`.

`./docs/` contains several emails and notes. Before reading any of them for a
question, run `ask-jev relevant` to decide which are worth reading.
