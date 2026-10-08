---
name: org-second-brain
description: Build and operate an organizational "second brain" domain-expert agent. Distills tacit expert knowledge into a version-controlled, linted wiki of position/taxonomy/routing/gateway files, drives analysis through composable recipes with human checkpoints, and compiles expert corrections into verified, regression-tested edits without model retraining (pattern from Meta's "An Organizational Second Brain", Sept 2026). Use when the user wants to codify institutional expertise for an AI agent, scaffold a knowledge base with a dependency graph, write recipes, diagnose expert feedback, or run the self-improvement loop. Not for personal note-taking or generic RAG setup.
license: MIT
compatibility: opencode
metadata:
  pattern-source: "Meta Engineering, An Organizational Second Brain (2026-09-02)"
  skill-version: "1.0.0"
  scripts-runtime: "python3 (stdlib only)"
---

# Organizational Second Brain

Turn specialist know-how that lives in experts' heads into a text-based knowledge system that an agent can reason over, that experts can review in seconds, and that improves every time an expert corrects it. Complexity lives in text files, never in fine-tuned weights.

## The four layers (they depend on each other, build all four)

| Layer | What it is | Where |
|---|---|---|
| Knowledge system | Distilled files: positions, taxonomy, routing indexes, gateways. Frontmatter declares `applies_when`, `depends_on`, `referenced_by` (bidirectional graph) | `knowledge/` |
| Reasoning layer | Composable **recipes**: imperative, multi-step procedures that load knowledge per step and contain no domain facts | `recipes/` |
| Evaluation framework | Benchmarks plus a regression suite that grows with every fix | `eval/` |
| Self-improvement loop | Diagnose, compile, validate, expert review. Gates every change | `feedback/` |

Remove one layer and the others degrade: the file structure makes automated edits possible, explicit recipes make failure attribution tractable, evaluation gates every change, the loop feeds back into knowledge and recipes.

## Non-negotiable principles

1. **Separate what the agent knows from how it reasons.** Knowledge files state positions and prescribe no procedure. Recipes prescribe procedure and contain no domain facts. This is what lets a failure be attributed to exactly one layer.
2. **Text, not weights.** Every improvement is a text edit a human can review in about 30 seconds, version-controlled, diffable, reversible.
3. **Progressive disclosure.** Each recipe step loads only the files that step needs. Never front-load a monolithic instruction set or dump the whole wiki into context.
4. **Humans stay in control.** Checkpoints surface intermediate reasoning for expert review. Escalations hand genuine ambiguity to the expert instead of forcing a resolution. Default to human-in-the-loop for compliance, financial risk, security review and engineering safety.
5. **Nothing lands ungated.** Every change passes: deterministic lint, independent adversarial review, blind targeted replay, regression suite, then expert approval. Each landed fix adds a regression case.
6. **Prefer deterministic checks.** Linting, dependency tracing and routing are programmatic and auditable. Do not rely on embedding similarity alone to choose which knowledge applies.
7. **Never invent organizational positions.** Anything not traceable to a source document or an expert statement is written with `status: draft` and flagged for SME review.

## First step: find the knowledge base

Look for `kb.config.json` in the working directory or ask the user for the kb root.

- Not found and the user wants a new domain: run **Bootstrap**.
- Found: pick the mode below from the user's intent. Read `kb.config.json` first, it sets budgets, risk tier, checkpoint policy and paths.

## Modes

| User intent | Mode | Primary reference |
|---|---|---|
| "Set up a second brain for <domain>" | Bootstrap | `references/adoption-checklist.md` |
| "Turn these documents / this expert into knowledge files" | Distill | `references/knowledge-schema.md` |
| "Write / fix a recipe" | Recipe design | `references/recipe-design.md` |
| "Analyze <case> with the expert agent" | Answer | `references/recipe-design.md`, `references/human-in-the-loop.md` |
| "Here is expert feedback / a corrected trace" | Diagnose | `references/improvement-loop.md` |
| "Apply these issues / run the improvement loop" | Improve | `references/improvement-loop.md`, `references/evaluation.md` |
| "Check the knowledge base" | Lint | `references/knowledge-schema.md` |

Load only the reference you need for the current mode.

### Bootstrap

1. Interview the user (one short question batch): domain name, risk tier (`low|medium|high`), SMEs and reviewers, source document locations, whether subagents are available, language of the outputs.
2. Scaffold: `python3 <skill-dir>/scripts/scaffold.py <kb-root> --domain "<name>" --risk-tier <tier>`. This copies the templates, creates the directory layout and writes `kb.config.json`.
3. Optionally install the OpenCode agents and commands: `python3 <skill-dir>/scripts/scaffold.py <kb-root> --with-opencode` (copies `assets/opencode/*` into `.opencode/`).
4. Run `python3 <skill-dir>/scripts/lint_knowledge.py <kb-root>` to confirm the empty skeleton is clean.
5. Hand over a short next-steps list (Distill the first sources, write the router recipe, build a first benchmark).

### Distill

Distillation is an offline, long-running pass. The goal is the **reasoning**, not a summary: how experts interpret the domain, what they prioritize, how they resolve ambiguity.

1. Inventory sources in `sources/` (immutable, never edit). Record each in `sources/INDEX.md`.
   Sources that are workflow or process diagram images: run the companion skill `workflow-image-to-ontology` first and store its output under `sources/workflows/<slug>/` (graph JSON, spec `.md`, `.ttl`), then distill from the spec.
2. Partition by **information density and expected usage frequency**:
   - High-density and frequently referenced: distill into wiki files (positions, decision frameworks, boundary examples, strategic interpretations).
   - Sparse and situational (specs, historical decision records, niche external material): leave in `sources/` and serve through search. List them in `sources/INDEX.md` with a one-line "when to look here".
3. For each wiki file use the template in `assets/templates/` and the field rules in `references/knowledge-schema.md`. Start every new file as `status: draft`, with `sources:` pointing to the evidence.
4. Build the supporting files: taxonomy (one authoritative glossary entry per term), routing index (input characteristics to files and recipes), gateways (threshold tests before entering an analytical domain).
5. Fill `depends_on`. Run lint with `--fix-backrefs` to generate `referenced_by`, then lint again.
6. Request SME review. Only SMEs flip a file to `status: active`.

### Recipe design

Follow `references/recipe-design.md`. Start from `assets/templates/recipe-router.md` for the top-level routing recipe and `assets/templates/recipe.md` for phase recipes. A recipe step names exactly which knowledge ids to load, the decision procedure, and the completion criterion. Add checkpoints and escalation triggers per `kb.config.json`.

### Answer

1. Follow `recipes/router.md`. Examine the input, choose downstream recipes, run them in order.
2. At every step load only the knowledge ids that step lists. Honor gateways before entering an analytical domain.
3. Write a knowledge manifest as you go: `feedback/traces/<run_id>.manifest.json` (schema: `assets/schemas/knowledge-manifest.schema.json`). It must record every file loaded, at which step, and how it was used. Diagnosis depends on it.
4. At each checkpoint, stop and present the intermediate reasoning, then wait for the expert to confirm, correct or redirect. On genuine ambiguity (underspecified input, or evidence supporting more than one defensible reading), escalate with the competing readings instead of picking one.
5. Cite knowledge ids for every conclusion. State uncertainty instead of masking it.

### Diagnose

Input: a conversation trace with expert corrections plus the run's knowledge manifest. Output: issue files in `feedback/issues/` validating against `assets/schemas/feedback-issue.schema.json`.

1. **Extract, do not classify.** Pull every substantive signal from the expert alongside the full manifest. Do not classify by conversational form: "the expert gave information" does not imply a knowledge gap.
2. **Apply the single attribution test** after reading the actual knowledge files: *could the agent have reached the correct conclusion from its source materials?*
   - Materials contained the right answer, agent still erred: `recipe_flaw`.
   - Materials did not contain the right answer: `knowledge_gap`.
   - Experts themselves disagree: `ambiguity`, flag for human discussion, do not edit.
3. Record the evidence for the verdict in the issue (`attribution_evidence`), including which files were read.

### Improve

Run the pipeline for each `open` issue. Full protocol in `references/improvement-loop.md`.

1. **Compile** the smallest edit set. Analyze impact (cross-references, conflicts with existing positions, token budget, test coverage, duplication risk), in parallel subagents where available.
2. **Deterministic validation**: `scripts/lint_knowledge.py`. Pass or fail, no judgment.
3. **Independent adversarial review**: a separate agent in a fresh context that receives only the proposed diffs, never the rationale. Use `@kb-adversarial-reviewer`. It hunts for contradictions, broken edge cases, undermined positions.
4. **Targeted replay** of the original scenario, blind: the agent does not know it is being tested, and the judge (`@kb-replay-judge`) sees the new output plus the original expert feedback but not the diff.
5. **Regression suite** across the benchmarks, in parallel independent sessions. On failure, retry compilation with the regression described, up to `improvement.max_compile_retries`.
6. **Land** as a pull request or reviewable diff with the complete audit trail (`assets/schemas/improvement-run.schema.json`). A human expert reviews a proven fix.
7. After approval, add the failing scenario and its validated answer to `eval/regression/` (`assets/schemas/regression-case.schema.json`).

If subagents or fresh sessions are unavailable, say so plainly: the independence guarantee of steps 3 and 4 is weakened, so require a second human reviewer for the diff.

### Lint

`python3 <skill-dir>/scripts/lint_knowledge.py <kb-root> [--fix-backrefs] [--json] [--strict]`

Checks: frontmatter schema, id/filename/prefix consistency, id collisions, dangling `depends_on`/`loads`/`calls`/routing targets, bidirectional dependency consistency, dependency cycles, per-file and total token budgets, orphan active files unreachable from any routing index, recipe/knowledge separation heuristics. Exit code 1 on errors.

## Bundled resources

| Path | Purpose |
|---|---|
| `references/architecture.md` | Four layers, wiki vs RAG split, limits of the evidence |
| `references/knowledge-schema.md` | File types, frontmatter fields, sections, budgets, lifecycle |
| `references/recipe-design.md` | Recipe anatomy, composition, checkpoints, anti-patterns |
| `references/improvement-loop.md` | Diagnose, compile, validate, land protocol |
| `references/evaluation.md` | Benchmarks, blind judge protocol, regression growth, metrics |
| `references/human-in-the-loop.md` | Checkpoints, escalations, risk tiers, reviewer roles |
| `references/adoption-checklist.md` | Preconditions, 3-sprint pilot plan, risks |
| `assets/schemas/*.schema.json` | JSON Schemas: knowledge file frontmatter, recipe frontmatter, kb config, manifest, issue, regression case, improvement run |
| `assets/templates/*` | Starter files for every file type, workspace `AGENTS.md`, `kb.config.json`, example benchmark |
| `assets/opencode/agents/*`, `assets/opencode/commands/*` | Optional OpenCode agents and slash commands for the loop |
| `scripts/scaffold.py` | Create the kb workspace from templates |
| `scripts/lint_knowledge.py` | Deterministic structural validator |
| `scripts/validate_json.py` | Validate a JSON file against a bundled schema (stdlib) |

## Output conventions

- Reply in the user's language. When the user writes Turkish, keep widely used technical terms in English (agent, skill, recipe, context, regression, lint) and do not translate them.
- When finishing a mode, report: what changed (file ids), lint status, what needs human review. Do not recap steps.
- Never present self-reported results from the source article (for example "zero regressions", "days to minutes") as guaranteed outcomes of this skill. They are one organization's measurements.
