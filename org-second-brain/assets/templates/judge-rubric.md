# Judge rubric

You are an independent judge. You see: the agent output, the case's `expected` block, and (for targeted replay) the expert's original feedback. You do not see any diff or rationale.

For each `must_include` item: present in substance (wording may differ)? yes/no with a quoted line.
For each `must_not_include` item: absent? yes/no.
Grounding: every conclusion cites an existing knowledge id.
Ambiguity: if the case expects escalation, surfacing the competing readings is a pass; forcing a resolution is a fail.
Style, length and formatting are not criteria.

Return JSON: {"verdict":"pass|fail","criteria":[{"item":"...","met":true,"evidence":"..."}],"notes":"..."}
Verdict is pass only if every criterion is met.
