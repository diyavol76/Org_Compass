---
id: rcp-example-phase
type: recipe
title: Example phase recipe
status: draft
owner: sme-name-or-team
version: 1
phase: example-phase
loads: [pos-example-topic]
checkpoints: [s2]
escalates_when:
  - evidence supports more than one defensible reading
done_when:
  - every conclusion cites a knowledge id
  - open questions are listed
referenced_by: []
last_reviewed: 2026-01-01
---

# Example phase recipe

### Step 1: Characterize the input (id: s1)
Load: none
Do: Extract the entities, activity and constraints from the input; list anything missing.
Output: structured characterization.
Checkpoint: no. Escalate if: missing detail would change the conclusion.

### Step 2: Apply the position (id: s2)
Load: `pos-example-topic`
Do: Compare the characterization with the position's boundaries; decide applies / does not apply / boundary.
Output: decision with cited ids.
Checkpoint: yes. Escalate if: result is "boundary" and examples do not settle it.
