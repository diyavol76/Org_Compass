# Adoption checklist

## Fit test (all four must be true)

- [ ] Specialist knowledge is mostly tacit (in people's heads, scattered docs).
- [ ] Consistency across assessments matters.
- [ ] Demand exceeds expert capacity.
- [ ] A general-purpose LLM gives analysis experts call inadequate.

If one is false, a plain RAG assistant or a single `AGENTS.md` is likely enough.

## Preconditions

- [ ] 2-3 named SMEs who commit weekly review time.
- [ ] 20-40 past cases with expert-quality answers (seeds for `eval/benchmarks/`).
- [ ] Source documents collected, with owners and access rights; sensitive content cleared for the model/provider in use.
- [ ] Place for the kb in version control with pull-request review.
- [ ] Agent runtime that supports skills/subagents or fresh sessions (OpenCode, Claude Code, equivalent).
- [ ] Risk tier agreed and approved by the business owner.
- [ ] Baseline measured: time per assessment, rework rate.

## Pilot plan (three sprints; adapt)

**Sprint 1 - Foundation.** Bootstrap workspace. Distill the highest-frequency positions (aim 20-50 files), a taxonomy, one routing index, one or two gateways. Write the router and one phase recipe. Seed benchmarks with SMEs. Lint clean. Checkpoints at every step.

**Sprint 2 - Loop.** Collect expert corrections from real use, diagnose, run the improvement pipeline end to end on 5-10 issues. Establish judge rubric and run regression. Track attribution mix.

**Sprint 3 - Calibrate.** Expand coverage to remaining recipes and positions, review metrics, relax checkpoint density where evidence supports it, decide go/no-go for a wider rollout.

## Go/no-go signals

- SME usefulness rating stable or rising across sprints.
- Regressions pre-merge caught and not reaching experts.
- Knowledge size within budget; mean tokens per turn flat or falling.
- Experts spend time on ambiguous cases rather than re-deriving routine analysis.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Invented positions | `draft` status until SME review; `sources:` required; judge penalizes ungrounded claims |
| Wiki bloat | Token budgets in lint; wiki vs search split by density and frequency |
| Stale knowledge | `last_reviewed` ages flagged by lint (`--strict`); owners per file |
| Over-trust | Checkpoints by tier; label provisional content |
| Judge noise | Majority of k samples; SME spot audits of judge verdicts |
| Expert disagreement baked in | `ambiguity` verdict; never auto-edit |
| Confidential data leakage | Clear data classification before distilling; keep `sources/` out of public repos |
| Treating one company's metrics as a promise | Measure your own baseline |

## Things this skill cannot do

- Replace SME judgment or approve its own positions.
- Guarantee zero regressions: it only blocks regressions the suite can see.
- Verify truth of source documents.
