# Improvement loop

Maintaining a document-based knowledge base is treated as a **compilation problem**: expert correction is the source, a minimal verified edit to knowledge and recipes is the compiled output, and a test suite plus independent review decide whether it ships.

```
trace + corrections + manifest
        │
   1 DIAGNOSE ──► issues (knowledge_gap | recipe_flaw | ambiguity)
        │
   2 COMPILE  ──► impact analysis ► edit set ► lint ► adversarial review
        │
   3 EVALUATE ──► blind targeted replay ► regression suite ► (retry on failure)
        │
   4 LAND     ──► PR + audit trail ► expert review ► regression case added
```

State per issue lives in `feedback/issues/<issue-id>.json` (`status`: `open`, `compiling`, `evaluating`, `ready_for_review`, `landed`, `rejected`, `needs_human_discussion`). Each run writes `feedback/runs/<run-id>.json` (`assets/schemas/improvement-run.schema.json`).

## 1. Diagnose

Inputs: the conversation trace, every expert correction, and the **knowledge manifest** (which files were loaded at which step).

Rules:
1. **Extract signals, do not classify by form.** Read the expert's whole contribution and pull each substantive point. Whether the expert "provided information" or "told the agent it was wrong" says nothing about root cause.
2. Read the actual files in the manifest, then apply the **attribution test**: *could the agent have reached the right answer from the materials it had?*

| Verdict | Condition | Action |
|---|---|---|
| `recipe_flaw` | Right answer was in the materials, agent erred (wrong step order, step skipped, loaded the wrong file, weak decision procedure) | Edit a recipe |
| `knowledge_gap` | Materials lacked the right answer (missing position, outdated, wrong boundary) | Edit or add knowledge files |
| `ambiguity` | Experts disagree with each other, or the case has more than one defensible reading | No edit. Set `needs_human_discussion`, surface to experts |

3. One expert statement may yield several issues; keep them separate so each can land or fail independently.
4. Record `attribution_evidence`: files read, quote of the relevant line (or its absence).

## 2. Compile

1. **Impact analysis**: run in parallel when subagents exist; otherwise sequentially. Dimensions: cross-references (trace `referenced_by` transitively), conflicts with existing positions, token budget headroom, regression coverage of affected files, duplication (does a file already say this?).
2. Produce the **smallest** edit set that resolves the issue. Bump `version`, add change-log lines citing the issue id, update `depends_on` and `referenced_by`. Do not touch unrelated files.
3. **Deterministic validation**: `python3 scripts/lint_knowledge.py <kb-root>`. Must exit 0. Lint failures go back to editing; they are not debated.
4. **Independent adversarial review**: a fresh context that sees only the diffs (and the kb), never the diagnosis or rationale. It tries to break the change: contradictions with other positions, edge cases now mishandled, positions undermined, scope creep. Findings are binding: fix, or document why not.

## 3. Evaluate

1. **Targeted replay.** Re-run the original scenario with the edited kb. The agent is not told it is a test. A separate **blind judge** receives the new output and the expert's original feedback (not the diff, not the diagnosis) and decides whether the feedback is now addressed.
2. **Regression suite.** Run all benchmarks in `eval/`, each in its own independent session, judged by an independent LLM judge against the stored expert answer. See `evaluation.md`.
3. On any failure, **retry compile** with a description of the regression (which case, what changed in the answer). Cap at `improvement.max_compile_retries` (default 3). Still failing: set `needs_human_discussion`, attach the best attempt and the failing diff, stop.

## 4. Land

1. Open a pull request (or write a reviewable patch if there is no VCS) containing: the edit set, the audit trail (issue, attribution evidence, impact analysis, review findings, replay verdict, regression result), and the proposed regression case.
2. A human expert reviews. Reviewing a proven fix takes seconds to minutes; the review is the final gate, not the only one.
3. On approval: merge, set issues `landed`, move proposed regression case into `eval/regression/`, set affected files' `last_reviewed`.
4. On rejection: set `rejected` with the reason; the reason is itself a signal. Re-diagnose if it reveals a wrong attribution.

## Batching

Group open issues by the files they touch so edits to the same file compile together, but evaluate and land each issue independently when possible. Never merge a batch where one issue failed regression.

## Degraded mode (no subagents / fresh sessions)

Run every step in one session but say so. Replace independent review with a second human reviewer; replace blind replay by running the scenario from a clean prompt containing only the scenario text. Record `independence: degraded` in the run file.

## Failure modes to watch

- Treating every correction as a knowledge gap (inflates the wiki, hides recipe flaws).
- Edits that fix the replayed case by over-fitting to its wording; the adversarial review and a paraphrased replay catch this.
- Silent growth beyond token budgets; lint enforces it.
- Merging a position the experts actually disagree on; `ambiguity` exists to stop this.
