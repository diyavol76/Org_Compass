# Human-in-the-loop

Autonomy is a dial calibrated to risk, not a goal. The agent does the analytical bulk; experts keep judgment over ambiguity, consequential steps and every change to what the agent knows.

## Risk tiers (`kb.config.json: risk_tier`)

| Tier | Typical domains | Checkpoints | Review of landed edits |
|---|---|---|---|
| `high` | compliance, legal, financial risk, security review, engineering safety | After every consequential step and before any final conclusion | Two expert reviewers; no auto-merge |
| `medium` | procurement, internal standards, policy Q&A | At phase boundaries and at boundary applications of a position | One expert reviewer |
| `low` | internal FAQs, formatting conventions | Final answer only; escalations still apply | One reviewer, may batch |

Source article: starts conservative, with expert checkpoints, then relaxes as trust grows. Relax by changing config after reviewing metrics, never silently.

## Checkpoint

The agent stops and presents:
1. What it concluded so far, in two to five sentences.
2. Which knowledge ids support each conclusion.
3. What it plans to do next.
4. Questions where it is least certain.

The expert answers `confirm`, `correct: <text>`, or `redirect: <text>`. Corrections are captured verbatim in the trace; they are the training signal for the improvement loop.

## Escalation

Triggered by:
- Underspecified input where the missing detail changes the conclusion.
- Two or more defensible readings of a position at its boundary.
- Gateway failure the agent cannot resolve from the input.
- A listed `Open question` in a loaded position file.
- No routing row matches.

Escalation message format: the readings, evidence for each with knowledge ids, the exact question for the expert, and the default the agent would take if forced (labelled as default, not decision).

## Roles

| Role | Does |
|---|---|
| SME / domain expert | Answers checkpoints, escalations; approves positions; reviews landed edits |
| KB maintainer | Owns lint, budgets, structure; runs the loop |
| Judge / reviewer agents | Independent verification; advisory, never final authority |
| Product owner | Sets risk tier, approves relaxing checkpoint density |

## Rules for the agent

- Never present a checkpoint as optional or skip one to save time.
- Never merge or auto-promote `draft` to `active`.
- Never state organizational positions as fact when the supporting file is `draft`; label them provisional.
- If an expert's correction conflicts with an `active` position, record both and diagnose; do not silently overwrite.
