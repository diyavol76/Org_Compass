# Evaluation framework

Two instruments, both mandatory: **targeted replay** (did this fix work?) and **regression suite** (did anything else break?). Together they gate every change.

## Layout

```
eval/
  benchmarks/        seed cases written with experts before the first improvement
  regression/        cases promoted from landed fixes (one per fix)
  runs/              per-run results (json)
  judge-rubric.md    shared rubric for the independent judge
```

## Case format

Each case is `eval/<set>/<case-id>.json` validating against `assets/schemas/regression-case.schema.json`:

- `id`, `title`, `domain_tags`
- `input`: the scenario text exactly as a user would submit it
- `expected`: the validated expert answer, split into `must_include` (claims, conclusions, cited positions), `must_not_include`, and optional `reference_answer`
- `origin`: `seed` or an issue id
- `knowledge_under_test`: ids expected to be loaded (used for coverage reports)
- `checkpoint_script`: pre-recorded expert responses for each checkpoint so replays run unattended

## Blind replay protocol

1. Start a fresh session. The prompt contains only `input`; the agent is **not** told it is an evaluation and does not see the expected answer, the diff or the issue.
2. Checkpoints are answered from `checkpoint_script`; unscripted escalations count as an outcome and are compared with `expected.escalation` if present.
3. The judge is a separate session. It gets: the agent output, the `expected` block, the rubric. For targeted replay of a fix it additionally gets the original expert feedback. It never gets the diff or rationale.
4. Judge returns `pass|fail`, per-criterion results, and quoted evidence. Judgments are stored in `eval/runs/`.

## Judge rubric essentials (`assets/templates/judge-rubric.md`)

- Pass requires every `must_include` item present in substance (wording may differ) and no `must_not_include` item.
- Cited knowledge ids must exist; a conclusion without grounding fails.
- Surfacing genuine ambiguity where the case calls for it is a pass; forcing a resolution is a fail.
- Style differences are not failures.

## Regression suite execution

- One independent session per case, run in parallel where possible.
- Same model and temperature settings as production; record them in the run file.
- LLM judging is noisy: for borderline or flaky cases run `k` samples (default 3) and require majority pass. Record per-case pass rate.
- A new failure that passed before the edit is a **regression**. It blocks landing and triggers compile retry.

## Growth rule

Every landed fix adds its failing scenario with the validated answer to `eval/regression/`, so the suite encodes everything experts ever corrected. Dedupe near-identical cases; keep the one with sharper `must_include`.

## Metrics to track (per sprint)

| Metric | Why |
|---|---|
| SME usefulness rating (1-5) per output | Quality as experts experience it |
| Share of outputs needing rework | The practical failure rate |
| Time per assessment, agent vs. baseline | Value |
| Issues by attribution (gap / flaw / ambiguity) | Where the system is weak |
| Regressions caught pre-merge | Evidence the gate works |
| Mean tokens per turn | Progressive disclosure payoff |
| Wiki size (files, tokens) vs. budget | Bloat control |

Measure a pre-agent baseline before the pilot; the source article's numbers are self-reported and not a benchmark for your domain.

## Pitfalls

- Judge and agent from the same session or sharing context: results become self-grading.
- Cases whose `expected` is only the final answer, not the key reasoning claims: passes by luck.
- Never re-using regression cases as few-shot examples in recipes; that contaminates the suite.
- Benchmarks authored only by engineers. Seed them with SMEs.
