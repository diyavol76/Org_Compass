---
description: Validate a workflow graph JSON and regenerate its derived files
---

Load the `workflow-image-to-ontology` skill. Run `python3 <skill-dir>/scripts/validate_workflow.py $1` and report errors, warnings and info grouped by element id. If there are no errors, re-run `scripts/render_workflow.py $1`. Propose minimal fixes; do not edit without confirmation.
