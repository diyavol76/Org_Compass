---
name: workflow-image-to-ontology
description: Extract a workflow, process or dependency diagram from an image (BPMN, flowchart, swimlane, pipeline, dependency graph) into a validated graph JSON plus a derived specification document, Turtle (RDF) and Mermaid, so the process can feed an ontology or be reasoned over by another agent. Use when the user gives a diagram image/screenshot and wants steps, dependencies, decisions, parallelism or actors mapped. Not for charts, org charts without flow semantics, or UI mockups.
license: MIT
compatibility: opencode
metadata:
  skill-version: "1.0.0"
  scripts-runtime: "python3 (stdlib only; Pillow optional for tile_image.py)"
  companion-skill: org-second-brain
---

# Workflow image to ontology

Turn a picture of a process into three things: a **canonical graph** (JSON, lossless, validated), a **specification document** another agent can follow (dependencies, decisions, paths, review queue), and **RDF/Turtle** aligned with PKO, P-Plan and PROV-O for the ontology. The model reads the picture; scripts do everything deterministic (validation, dependency derivation, rendering). Derived facts are never hand-written.

## Principles

1. **Observed vs inferred.** Everything drawn is `status: observed`. Anything implied (missing start, assumed condition) is `status: inferred` with an `inference_basis`. Anything unclear becomes an `open_question`, not a guess. Same rule as org-second-brain: never invent organizational positions.
2. **Store arrows as drawn.** `meta.arrow_semantics` (`flow` | `depends_on` | `unknown`) says how to read them. The renderer normalizes direction; the extractor never flips edges silently.
3. **Verbatim labels, original language.** Do not translate, fix or paraphrase labels. Unreadable text: empty label, `label_status: unreadable`, plus an open question.
4. **Relations are the hard part.** Published evaluation of vision-language models on BPMN images shows names and types extract far better than relations (best strict relation F1 around 0.48), with errors concentrated on gateways, message vs sequence flow, dense multi-lane layouts and low-res small markers. So: trace edges deliberately, tile big images, and verify with an independent pass. See `references/extraction-protocol.md`.
5. **Draft until a human says otherwise.** Output is `review_status: draft`. Only a reviewer sets `reviewed`.

## Workflow

1. **Intake.** Locate the image (ask if absent). Note notation if the user said it, domain, language, and what arrows mean if known. Check size; if wide, dense or small-text, run
   `python3 <skill-dir>/scripts/tile_image.py <image> --out <work>/tiles` and read the tiles plus the overview.
2. **Extract** following `references/extraction-protocol.md` (four passes: inventory, edges, semantics, self-check). Write `<slug>.graph.json` matching `assets/schemas/workflow-graph.schema.json`.
3. **Validate.** `python3 <skill-dir>/scripts/validate_workflow.py <slug>.graph.json`. Fix errors by re-reading the image, never by editing to satisfy the validator. Warnings (orphans, unlabeled branches, unreachable nodes, implicit splits) usually mean a missed edge: check the image again.
4. **Render.** `python3 <skill-dir>/scripts/render_workflow.py <slug>.graph.json --out <dir>` writes `<slug>.md`, `<slug>.ttl`, `<slug>.mmd`. Compare the Mermaid topology against the image once more.
5. **Independent verification** (fresh context, only the image and the graph): `@wf-verifier` where subagents exist. Without subagents say so plainly and ask the user to review the Mermaid against the image.
6. **Report**: files written, validator warnings, verifier findings, open questions, low-confidence items. Do not recap the steps.

## Output set

| File | Role | Consumer |
|---|---|---|
| `<slug>.graph.json` | Canonical, lossless. Source of truth | Any agent or script; ontology loaders |
| `<slug>.md` | Derived spec: participants, steps, control flow, **task dependency table**, decisions, parallelism, loops, paths, review queue, usage notes | Agents and humans (stable headings 1 to 12) |
| `<slug>.ttl` | RDF instance data (`wfo:` over PKO, P-Plan, PROV-O), arrows reified as `wfo:Transition` | Triple store, ontology tooling |
| `<slug>.mmd` | Mermaid flowchart | Visual round-trip check |

Vocabulary: `assets/ontology/workflow-vocabulary.ttl`. Mapping rules and competency questions: `references/ontology-mapping.md`. How another agent should consume the output: `references/agent-consumption.md`. A complete worked example (image, graph, spec, Turtle, Mermaid) is in `assets/examples/`.

## Use with org-second-brain

Store each result under `sources/workflows/<slug>/` (sources are immutable), keep the original image beside it, and add a row to `sources/INDEX.md`. During **Distill**, derive from the spec: process steps and decision rules become `position` candidates (`status: draft`, `sources:` pointing at the spec), entity and activity names go to `taxonomy`, and the dependency table feeds recipe step ordering. Nothing becomes `active` without SME review.

## Install the OpenCode agents and commands (optional)

`python3 <skill-dir>/scripts/install_opencode.py <project-root>` copies `wf-extractor`, `wf-verifier`, `/wf-extract` and `/wf-check` into `.opencode/`.

## Bundled resources

| Path | Purpose |
|---|---|
| `references/extraction-protocol.md` | Symbol guide, four-pass procedure, confidence rubric, failure modes |
| `references/ontology-mapping.md` | Graph to PKO / P-Plan / PROV-O mapping, derived relations, competency questions |
| `references/agent-consumption.md` | How a downstream agent should read and respect the outputs |
| `assets/schemas/workflow-graph.schema.json` | Canonical graph schema |
| `assets/ontology/workflow-vocabulary.ttl` | `wfo:` vocabulary and alignments |
| `assets/examples/` | Worked example, Turkish swimlane diagram |
| `assets/opencode/*` | Optional agents and commands |
| `scripts/validate_workflow.py` | Schema plus graph checks |
| `scripts/render_workflow.py` | Derive md, ttl, mmd |
| `scripts/tile_image.py` | Overlapping upscaled tiles for dense images |
| `scripts/validate_json.py` | Stdlib JSON Schema validator |

## Output conventions

- Reply in the user's language. For Turkish, keep technical terms (workflow, gateway, lane, agent, graph) in English.
- Generated headings in the `.md` are English and fixed on purpose: agents can rely on them. Labels inside keep the diagram's language.
- Never present extraction as certain: always surface confidence, inferred elements and open questions.
