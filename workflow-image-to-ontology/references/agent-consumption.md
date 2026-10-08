# Consuming the output (for downstream agents)

Which file to read for what, and the rules that keep the extraction trustworthy.

## Which file

| Need | Read |
|---|---|
| Understand the process quickly, plan, schedule, explain | `<slug>.md` (sections 1 to 9) |
| Exact ids, edge types, conditions, confidences | `<slug>.graph.json` (canonical) |
| Query across several processes, link to an ontology | `<slug>.ttl` |
| Show or sanity-check the shape | `<slug>.mmd` |

Progressive disclosure: load the `.md` first. Open the JSON only for exact semantics or when you must act on a specific element. Do not paste whole graphs into context when section 5 answers the question.

## Reading the dependency table (section 5)

- `(entry)`: no predecessor; may start when the process starts.
- Single dependency: strict sequence.
- `ALL of: A, B`: parallel join. Start only when every listed step is done.
- `ANY one of: A, B`: exclusive merge. Start when whichever branch was taken completes.
- `[if: text]`: the dependency applies only on that branch condition. Conditions are quoted from the diagram; evaluate them with the case at hand, do not reinterpret them.
- Loops (section 8) mean a step can run more than once; "done" means done in the current iteration.

## Rules

1. **Respect status.** `inferred` elements and anything in section 10 (review queue) are hypotheses. Surface them when they affect your answer; never present them as fact.
2. **Respect `review_status`.** `draft` output is fine for analysis and ideation. For compliance, financial, security or safety decisions, require `reviewed` or escalate to a human.
3. **Blocking open questions stop dependency reasoning.** If `arrow_semantics` is `unknown`, do not derive order from the graph; ask.
4. **Do not fill gaps.** A decision branch without a condition stays unconditioned. A missing end stays missing. Ask the process owner.
5. **Do not edit derived files.** Change the JSON (or re-extract), validate, re-render. The `.md`, `.ttl`, `.mmd` are regenerated and hand edits are lost.
6. **Corrections from a human** go into the JSON, with the question resolved in `open_questions[].resolution` and `review_status`/`reviewed_by` updated by the reviewer.

## Hand-off prompt snippet

```
You are given a workflow specification (workflow-image-to-ontology output).
Use section 5 as the dependency contract and section 6 for decision rules.
Treat inferred elements and section 10 as unconfirmed; ask before relying on them.
Cite step ids (`like-this`) in your reasoning. If arrow_semantics is unknown, stop and ask.
```
