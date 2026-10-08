# Organizational second brain workspace

Domain: {{DOMAIN}}   Risk tier: {{RISK_TIER}}

This workspace holds a version-controlled knowledge base for a domain-expert agent. Use the `org-second-brain` skill for any work in it.

Rules for every session here:
- `sources/` is immutable. Never edit it.
- Knowledge files (`knowledge/`) state positions and contain no procedures. Recipes (`recipes/`) contain procedures and no domain facts.
- Load only the knowledge ids a recipe step lists. Record every load in `feedback/traces/<run_id>.manifest.json`.
- Honor checkpoints and escalations. Never force a resolution on genuine ambiguity.
- Run `python3 <skill-dir>/scripts/lint_knowledge.py .` before any change is proposed. Nothing lands with lint errors.
- Only SMEs promote a file from `draft` to `active`.
