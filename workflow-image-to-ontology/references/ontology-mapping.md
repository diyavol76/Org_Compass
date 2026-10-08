# Ontology mapping

The JSON graph is canonical. The Turtle output maps it onto a small `wfo:` vocabulary (`assets/ontology/workflow-vocabulary.ttl`) that reuses established procedural-knowledge models instead of inventing new ones.

## Why this shape

- **PKO** (Procedural Knowledge Ontology) gives `pko:Procedure`, `pko:Step`, `pko:hasStep`, `pko:nextStep`. It deliberately models only sequential order and keeps control flow simple ([paper](https://arxiv.org/abs/2503.20634)). Workflow diagrams have gateways, so `wfo:` adds them as explicit nodes.
- **P-Plan** (`p-plan:Plan`, `p-plan:Step`, `p-plan:isPrecededBy`) and **PROV-O** (`prov:Agent`) give provenance-friendly plans and actors. Lanes become `wfo:Participant`, a subclass of `prov:Agent`.
- **Specification vs execution.** The graph describes the *specified* process. Runtime executions (who did what, when) are a different layer; model them later as `prov:Activity` / PKO executions that point at the steps here. Do not mix them in this graph.
- **Gateways stay explicit.** Collapsing a diamond into plain `precedes` edges loses ALL vs ANY semantics. Gateways are nodes; a derived `wfo:dependsOn` collapses them for convenience, and the markdown spec states the join kind.
- **Arrows are reified** as `wfo:Transition` (from, to, flowType, condition, status, confidence). This is what makes "which branch applies when" queryable.

## Node type mapping

| Graph `type` | RDF class | Also typed as |
|---|---|---|
| `task` | `wfo:Task` | `pko:Step`, `p-plan:Step` |
| `subprocess` | `wfo:Subprocess` | `pko:Step`, `p-plan:Step` |
| `start` / `end` / `event` | `wfo:StartEvent` / `wfo:EndEvent` / `wfo:IntermediateEvent` | |
| `xor_gateway` / `and_gateway` / `or_gateway` / `event_gateway` | `wfo:ExclusiveGateway` / `wfo:ParallelGateway` / `wfo:InclusiveGateway` / `wfo:EventBasedGateway` | |
| `data_object` / `data_store` / `document` / `external_system` | `wfo:DataObject` / `wfo:DataStore` / `wfo:Document` / `wfo:ExternalSystem` | |
| lane / pool / team / role | `wfo:Participant` | `prov:Agent` |
| whole diagram | `wfo:Process` | `pko:Procedure`, `p-plan:Plan` |

## Derived relations (computed by `render_workflow.py`)

| Relation | Meaning | How derived |
|---|---|---|
| `wfo:precedes` | Directly follows in control flow | Flow edges after normalizing arrow direction (`depends_on` diagrams are flipped) |
| `pko:nextStep`, `p-plan:isPrecededBy` | Same, only between two steps with a single successor | Subset of `precedes` |
| `wfo:dependsOn` | Step needs another step done first | Walk backwards through gateways until a step is reached |
| join kind (in the md spec) | `ALL of` (AND join), `ANY one of` (XOR merge), `ANY (one or more)` (OR) | First join gateway met on the backward walk |
| branch condition | Condition under which a dependency applies | Edge `condition` collected along the walk |
| `wfo:performedBy` | Responsible participant | The node's lane |
| `wfo:sendsMessageTo` | Cross-participant message | `message` edges |
| `wfo:reads` / `wfo:writes` | Data access | `data` edges, direction from the data node |

Namespace caveat: `https://orgcompass.example/...` is a placeholder. Swap in the organization's namespace (single find-and-replace across `.ttl` files) before loading into a shared store. PKO's namespace is `https://w3id.org/pko#`.

## Competency questions the output should answer

Use these as acceptance tests for a mapping (SPARQL over the Turtle, or filters over the JSON):

1. Which steps must complete before step X can start? (`wfo:dependsOn`)
2. Which steps can run in parallel? (steps downstream of the same `wfo:ParallelGateway` split)
3. Under which condition does step X run? (transition `wfo:condition` along the path)
4. Which participant performs step X, and which steps hand over between participants?
5. Where are the loops (rework cycles)?
6. Which parts of this process are inferred or low-confidence and need review?
7. Which steps read or write which data objects or systems?

Example SPARQL (competency question 1):

```sparql
PREFIX wfo: <https://orgcompass.example/ontology/workflow#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?step ?needs WHERE {
  ?s wfo:dependsOn ?n . ?s rdfs:label ?step . ?n rdfs:label ?needs .
}
```

## Merging several diagrams

Each graph is its own `wfo:Process` with its own base IRI (`.../workflow/<slug>#`). To connect diagrams (a subprocess drawn elsewhere, the same task in two flows), add an explicit link with a reviewer-approved `owl:sameAs` or `skos:exactMatch` between step IRIs. Never auto-merge by label equality; labels collide across teams.

## Planned, not done

SHACL shapes for the Turtle (the PKO authors defer validation to SHACL too) and a runtime-execution layer are out of scope for v1.
