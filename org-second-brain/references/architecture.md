# Architecture

Source pattern: Meta Engineering, "An Organizational Second Brain: Building an AI That Learns From Experts" (2 Sept 2026, authors Shaurya Sengar, Jason Nawrocki, Jay Shah, Prashant Kommireddi). Built there for one compliance domain; the authors claim the pattern generalizes to finance, security, engineering standards and procurement. No code or dataset was published, so this skill is an implementation of the described pattern, not a copy of Meta's system.

## Problem

- The most valuable specialist knowledge is implicit: how experts reason, what they prioritize, how they resolve ambiguity. Documents are a by-product of that work, not the knowledge itself.
- An agent that retrieves document chunks at inference time re-derives reasoning on every run: slow, error-prone, inconsistent.
- A general model can say what an organization *could* do (general information) but not what it *should* consider doing (historic positions, company direction, business context).

## The four layers

```
 expert corrections ──► [4 Self-improvement loop] ──edits──► [1 Knowledge system]
                                   ▲  │                          ▲   │ loaded per step
                         gates     │  └──edits──► [2 Reasoning layer: recipes]
                                   │                          │
                          [3 Evaluation framework] ◄──────────┘ runs produce traces + manifests
```

1. **Knowledge system.** Pre-extracted, explicitly structured, progressively disclosed files. Four types: position, taxonomy/vocabulary, routing index, gateway. Frontmatter declares when a file applies and its dependency edges, forming a bidirectional graph the agent can traverse and maintain.
2. **Reasoning layer.** Recipes: imperative, composable procedures. A top-level routing recipe examines the input and selects downstream recipes, each handling one analytical phase.
3. **Evaluation framework.** Targeted replay plus regression benchmarks. Gates every change.
4. **Self-improvement loop.** Treats maintenance of a document-based knowledge base as a *compilation problem*: expert correction in, minimal verified edit out.

## Why files, not weights

- Fast-changing institutional knowledge (positions, policies, judgments) would need retraining for each correction.
- Text edits are reviewable, version-controlled, diffable, reversible.
- Failures attribute to a layer and a file, not to opaque parameters.
- Model-agnostic: the knowledge layer survives model upgrades.

## Wiki versus RAG: split by density and frequency

| | Wiki (curated files) | Search (RAG over `sources/`) |
|---|---|---|
| Content | Positions, decision frameworks, boundary examples, strategic interpretations | Detailed reference material, product specs, historical decision records, niche external knowledge |
| Usage | Consulted on nearly every turn | Matters deeply when it applies, otherwise irrelevant |
| Maintenance | Must stay current; versioned and validated | Append-only, immutable sources |
| Loaded | By routing index or recipe step, deterministically | By semantic or lexical search on demand |

Loading everything into the wiki bloats the system and dilutes attention. The combination grounds core reasoning in the most refined knowledge while keeping supporting evidence reachable.

## Progressive disclosure and token economy

The source reports that restructuring from one flat instruction file plus semantic search of all sources into recipe-driven stages cut tokens consumed per turn by about 80%. Treat this as a direction, not a promise. Measure your own per-turn token use before and after (see `evaluation.md`).

## Reported results (self-reported, one domain, three sprints over six weeks)

- SMEs rated outputs useful almost all the time (up from outputs that needed substantial rework).
- Individual assessment time went from days to minutes.
- Validated knowledge edits at a rate that previously took full engineering sprints.
- Zero regressions across improvement cycles.
- Experts reported the agent handles the vast majority of analytical work, leaving ambiguous cases for them.

## When it fits

All must hold:
- Specialist knowledge exists mostly as tribal knowledge.
- Consistency across assessments matters.
- Work volume exceeds expert capacity.
- Off-the-shelf LLMs give inadequate analysis.

Four adoption requirements: a structured knowledge system with explicit boundaries and dependency graph, a procedural layer separate from knowledge, an automated evaluation suite that grows, human-in-the-loop checkpoints calibrated to risk.

## Related public work

- Andrej Karpathy, "LLM Wiki" gist (4 Apr 2026): agent knowledge as a navigable, LLM-maintained graph of markdown files with raw sources / wiki / schema layers and ingest / query / lint operations.
- Google Cloud, Open Knowledge Format (OKF) v0.1 (12 Jun 2026): vendor-neutral directory of markdown files with YAML frontmatter and a required `type` field. If you need cross-agent portability, consider emitting OKF-compatible frontmatter alongside the fields defined here (mapping is not specified by Meta; verify against the OKF spec before relying on it).
- Meta Engineering, "How Meta Used AI to Map Tribal Knowledge in Large-Scale Data Pipelines" (6 Apr 2026): a different team's, code-oriented variant ("compass, not encyclopedia" context files). Not cited by the second-brain article.
