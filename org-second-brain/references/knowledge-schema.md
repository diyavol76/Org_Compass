# Knowledge schema

Machine-checked by `scripts/lint_knowledge.py`; JSON Schema in `assets/schemas/knowledge-file.schema.json`.

## File types and prefixes

| type | id prefix | directory | Purpose |
|---|---|---|---|
| `position` | `pos-` | `knowledge/positions/` | An authoritative organizational stance: how the organization interprets a domain question, with constraints, boundary conditions and machine-actionable routing implications |
| `taxonomy` | `tax-` | `knowledge/taxonomy/` | Authoritative glossary: entity types, activity categories, classification tiers. One source of truth per term |
| `routing` | `rt-` | `knowledge/routing/` | Maps input characteristics to the knowledge files and recipes that apply. Deterministic, auditable, not embedding-only |
| `gateway` | `gw-` | `knowledge/gateways/` | Threshold tests the agent must pass before entering an analytical domain; prevents applying specialized knowledge where it does not belong |
| `recipe` | `rcp-` | `recipes/` | Procedure; see `recipe-design.md` |

The filename stem equals the id (`pos-data-retention.md` has `id: pos-data-retention`).

## Frontmatter (restricted YAML subset)

The linter reads a deliberately small YAML subset so the skill has no dependencies: one `key: value` per line, scalars, inline lists `[a, b]`, or block lists (`- item`). No nested mappings, no multi-line scalars. Keep long text in the body.

| Field | Req | Meaning |
|---|---|---|
| `id` | yes | Unique, kebab-case, correct prefix |
| `type` | yes | `position`, `taxonomy`, `routing`, `gateway` |
| `title` | yes | Human title |
| `status` | yes | `draft` (unreviewed), `active` (SME approved), `deprecated` |
| `owner` | yes | SME or team accountable for the file |
| `version` | yes | Integer, increment on every landed edit |
| `applies_when` | position, gateway | Triggering scenarios as short phrases. Tells the router and agent when to load |
| `depends_on` | yes (may be `[]`) | Ids this file relies on |
| `referenced_by` | yes (may be `[]`) | Ids that depend on or load this file. Must mirror `depends_on` / recipe `loads` edges. Generate with `--fix-backrefs` |
| `routes_to` | routing | Ids this index points at (also listed in the body table) |
| `sources` | position | Paths under `sources/` or expert references that support the file |
| `token_budget` | no | Per-file override of the budget in `kb.config.json` |
| `last_reviewed` | yes | `YYYY-MM-DD` of last SME review |

## Body structure per type

### Position file

```
# <Title>
## Position            one paragraph: the stance, stated plainly
## Rationale            why the organization holds it; link strategic context
## Constraints and boundaries   what it does NOT cover; conditions under which it stops applying
## Routing implications  machine-actionable: "when X, load `tax-..`; hand off to `rcp-..`"
## Boundary examples    2-4 short cases at the edge, each with the correct reading
## Open questions       known ambiguity; each triggers escalation, not a guess
## Change log           version, date, issue id, one line
```

No procedures. If the content reads as "first do A, then B", it belongs in a recipe.

### Taxonomy file

A table: `term | definition | not to be confused with | aliases`. One term, one definition, in exactly one file. Other files reference the term by link, never redefine it.

### Routing index

A table whose rows map `input characteristics` to `knowledge ids` and `recipe id`. Cells use backticked ids so the linter can check them. Include a default row and an explicit "no match, escalate" row.

### Gateway file

Numbered threshold tests, each phrased as a pass/fail question answerable from the input alone, plus "if any test fails: do not enter this domain, do X instead". Gateways are knowledge (conditions), not procedures.

## Dependency graph rules

1. Edges are declared on both ends. If A lists B in `depends_on`, B lists A in `referenced_by`. A recipe's `loads` edges also appear in the target's `referenced_by`.
2. No cycles among `depends_on` edges.
3. Before proposing any edit, trace `referenced_by` transitively: that set is the blast radius.
4. Deprecating a file requires migrating or deprecating everything in its `referenced_by`.

## Size and budgets

Keep files small enough to load whole. Defaults in `kb.config.json`: soft 1,500 tokens (warning), hard 3,000 (error) per file; total wiki budget configurable. The linter estimates tokens as characters divided by 4. A file near budget should be split along its routing implications, not trimmed of boundary examples.

## Lifecycle

`draft` -> (SME review) -> `active` -> (superseded) -> `deprecated`. Only SMEs promote to `active`. Edits to an `active` file go through the improvement loop and bump `version`. Never delete a deprecated file that a regression case cites.

## Authoring rules

- Write what the organization decides, with the reason, not what the source said.
- Prefer a concrete boundary example to an abstract qualifier.
- Every claim traceable: `sources:` for positions; expert-stated positions cite the issue id that introduced them in the change log.
- One idea per file. If `applies_when` needs "and/or" across unrelated scenarios, split it.
