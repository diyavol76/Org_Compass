# Recipe design

Knowledge files are declarative. Recipes are imperative. A recipe prescribes a multi-step analytical workflow: what to examine first, which knowledge to load at each step, which decision procedure to follow, what a complete analysis looks like. Schema: `assets/schemas/recipe.schema.json`.

## The separation rule

- Recipes reference knowledge ids and contain **no domain facts**.
- Knowledge files state positions and prescribe **no procedures**.

Consequences:
- New organizational position: add a knowledge file and update a routing index. No recipe change.
- Flawed methodology: edit a recipe. No knowledge change.
- A failure attributes cleanly to one layer: was the knowledge wrong or the procedure?

## Frontmatter

| Field | Req | Meaning |
|---|---|---|
| `id` | yes | `rcp-...` |
| `type` | yes | `recipe` |
| `title` | yes | |
| `status`, `owner`, `version`, `last_reviewed` | yes | as for knowledge files |
| `phase` | yes | `router`, or the analytical phase this recipe handles |
| `loads` | yes | All knowledge ids any step may load (union). The linter checks each exists |
| `calls` | no | Recipe ids this recipe delegates to |
| `checkpoints` | yes (may be `[]`) | Step ids where the agent must stop for expert review |
| `escalates_when` | yes | Short phrases describing genuine-ambiguity triggers |
| `done_when` | yes | Completion criteria for a complete analysis |
| `referenced_by` | yes | Recipe ids that call this one |

## Body: steps

Number steps. Each step has the same four parts so a diagnoser can point at one:

```
### Step 3: <name>   (id: s3)
Load: `pos-...`, `tax-...`          only what this step needs
Do: <the decision procedure, imperative, explicit>
Output: <what this step must produce for the next step>
Checkpoint: yes|no       Escalate if: <condition>
```

## Composition

- The **router recipe** (`phase: router`) examines the input, applies gateways, consults routing indexes, and selects which downstream recipes to invoke, in what order. It decides routing only.
- Each downstream recipe handles one analytical phase and may call sub-recipes.
- Analogy: a head chef's master recipe delegates to sub-recipes for sauce, protein and garnish without containing their details.

## Progressive disclosure

Early flat designs load all sources into context every run. Recipe-driven stages load a small targeted subset per step. Rule: **a step may load only ids it lists in `Load:`**, and the manifest records each load. If a step needs something it did not list, that is a recipe bug to diagnose, not something to patch ad hoc at run time.

## Checkpoints and escalations

- A **checkpoint** surfaces intermediate reasoning and waits for the expert to confirm, correct or redirect. Place them after steps whose errors would compound downstream, and after any step that applies a position at its boundary.
- An **escalation** fires on genuine ambiguity: underspecified input, or evidence supporting more than one defensible reading. State the readings, the evidence for each, and the question for the expert. Never force a resolution.
- Calibrate density by risk tier (`human-in-the-loop.md`).

## Anti-patterns

| Anti-pattern | Why it hurts | Fix |
|---|---|---|
| Domain facts inside a recipe | Two sources of truth; failures cannot be attributed | Move the fact to a position file, load it by id |
| Step that says "load everything relevant" | Defeats progressive disclosure, hides what was used | List exact ids; use a routing index for dynamic choice |
| Recipe without `done_when` | No definition of a complete analysis | Add explicit completion criteria |
| Silent tie-breaking on ambiguity | Masks uncertainty, destroys trust | Escalate |
| One mega-recipe | No reuse, hard to diagnose | Split by phase, compose |
| Checkpoint only at the end | Errors compound before review | Checkpoint after consequential steps |

## Writing a new recipe: procedure

1. List the phases an expert actually walks through, in the order they think. Interview or read expert traces; do not invent the method.
2. One recipe per phase; one router on top.
3. For each step: which knowledge, which decision procedure, what output.
4. Mark checkpoints and escalation triggers.
5. Write `done_when` from what experts consider a complete answer.
6. Lint, then replay two or three past cases blind and compare with expert answers.
