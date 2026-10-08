---
id: rcp-router
type: recipe
title: Top-level routing recipe
status: draft
owner: sme-name-or-team
version: 1
phase: router
loads: [rt-example-index]
calls: [rcp-example-phase]
checkpoints: [s2]
escalates_when:
  - no routing row matches
  - input is underspecified
done_when:
  - downstream recipes selected and ordered, or case escalated
referenced_by: []
last_reviewed: 2026-01-01
---

# Top-level routing recipe

### Step 1: Examine the input (id: s1)
Load: none
Do: Summarize what the input is, which activity it describes, and which details are missing.
Output: one-paragraph characterization.
Checkpoint: no. Escalate if: input is too thin to route.

### Step 2: Route (id: s2)
Load: `rt-example-index`
Do: Match the characterization to routing rows; pick downstream recipes in order. Check any gateway named in the matched row before calling its recipe.
Output: ordered list of recipe ids with reasons.
Checkpoint: yes. Escalate if: no row matches.

### Step 3: Run downstream recipes (id: s3)
Load: none
Do: Execute each selected recipe in order, passing forward each recipe's output.
Output: the combined analysis plus open questions.
Checkpoint: no. Escalate if: a downstream recipe escalates.
