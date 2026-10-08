# Extraction protocol

How to read a process diagram image into `workflow-graph.schema.json`. Follow the passes in order.

## 0. Intake checklist

- Image width under about 1200 px, or text that is hard to read at full view: ask for a better export, or tile it (`scripts/tile_image.py`). Downscaling erases exactly the markers that carry semantics.
- Identify notation: `bpmn` (pools/lanes, circles, rounded tasks, diamonds with markers), `flowchart` (ISO shapes: terminator, process, decision diamond, parallelogram I/O), `uml-activity` (fork/join bars, initial and final nodes), `swimlane`, `dependency-graph` (nodes and arrows, no start/end), `pipeline` (CI/CD stages), else `unknown`.
- Decide the **arrow meaning** (`meta.arrow_semantics`):
  - `flow`: arrow means "then" (almost all workflow notations).
  - `depends_on`: arrow from A to B means "A requires B" (typical in build/dependency graphs, task graphs with "blocked by"). Look for a legend, the title, or an unambiguous start-to-end layout.
  - Cannot decide: `unknown` plus a **blocking** open question. Do not pick silently; the dependency direction is the whole point of the output.

## 1. Symbol guide

| Visual | Node type |
|---|---|
| Circle thin border, empty or with envelope/clock | `start` (empty) / `event` |
| Circle thick or double border | `end` |
| Circle with double thin border | `event` (intermediate) |
| Rounded rectangle / plain rectangle with a verb phrase | `task` |
| Rectangle with a small `+` box at the bottom, or double border | `subprocess` |
| Diamond, empty or with `X`; question text with branch labels | `xor_gateway` |
| Diamond with `+` | `and_gateway` (parallel) |
| Diamond with a circle `O` | `or_gateway` |
| Diamond with a pentagon in a double circle | `event_gateway` |
| Fork/join thick bar (UML) | `and_gateway` |
| Cylinder | `data_store` |
| Page with folded corner, `data_object` icon | `document` / `data_object` |
| Box labeled with a system/tool name outside the flow | `external_system` |
| Small circle with a letter/number, "to page 2" | `connector` |
| Dog-eared note, bracket, dotted link to element | `annotation` |

| Line | Edge type |
|---|---|
| Solid arrow between flow elements | `sequence` (put branch text in `condition`, other text in `label`) |
| Dashed arrow, often with an envelope, crossing lanes/pools | `message` |
| Dotted line to a data object/store/document | `data` |
| Arrow in a dependency-style graph | `dependency` |
| Plain line with no arrowhead (annotation link) | `association` |

Label placement is a common trap: an edge label belongs to the arrow it sits **on or beside**, nearest first. If a label floats between two arrows record the best reading with confidence at most 0.85 and open a `minor` question.

## 2. The four passes

**Pass 1, inventory.** List lanes/pools first (they give the actor for every node inside them), then every node: id, label exactly as printed, type, lane, location (coarse description such as "top-left of lane Finance"). Ids: lowercase kebab-case slugs derived from the label (`talep-incele`), unique. Unlabeled gateways keep `label: ""`, `label_status: none`. Do not number things you cannot see.

**Pass 2, edges.** Walk **every arrow from tail to head**. For each: source, target, type, line style, label/condition. Arrowheads decide direction, never layout order. Lines that merge into one arrowhead are separate edges that share a target; lines that leave one point toward several heads are separate edges that share a source. Edges that leave the lane/pool boundary are suspects for `message`.

**Pass 3, semantics.** Gateways: classify by marker, not by guess. A decision diamond with question text and labeled exits is `xor_gateway` with each exit's text in `condition`; mark the unlabeled or "otherwise" exit `is_default: true` only if the image makes that explicit. Check splits and joins: a gateway with one in and several out is a split; several in and one out is a join. Mark loops by simply drawing the back edge, do not invent loop constructs.

**Pass 4, self-check.**
1. Count arrowheads in the image and compare with the number of edges.
2. Every node has at least one edge (annotations excepted).
3. Every decision branch carries a condition; if not, either the image omits it (leave empty, validator will warn, keep it) or you missed text.
4. Run the validator, render Mermaid, and compare topology with the image once more.
5. Lower the confidence of anything you resolved by proximity, inference or squinting.

## 3. Confidence rubric

| Score | Meaning |
|---|---|
| 0.95 | Clearly drawn, text crisp, unambiguous |
| 0.85 | Clear, but one detail resolved by proximity or small text |
| 0.7 | Partly legible, or the type is a judgment (task vs subprocess) |
| 0.5 | Inferred from layout or convention; must have an open question |
| below 0.5 | Do not include as observed. Record it only as an open question |

`meta.overall_confidence`: roughly the confidence of the weakest relation, not the average of easy shapes. Relations are where extraction fails.

## 4. When to stop and ask

Ask the user (or leave a `blocking` question when working unattended) if: arrow meaning is undecidable; a lane assignment changes who is responsible; a gateway kind cannot be read; more than about 15% of labels are unreadable. A short question with the candidate readings is better than a confident wrong graph.

## 5. Failure modes to watch

| Failure | Countermeasure |
|---|---|
| Missed or reversed edges in dense areas | Tile the image; re-trace each arrow; count arrowheads |
| Message flow recorded as sequence | Check dashed style and lane crossing |
| Gateway marker lost on downscale | Zoom on the diamond; never default silently to XOR |
| Hallucinated nodes from legends or titles | A node needs a shape in the diagram body; legends and titles are not nodes |
| Labels "corrected" or translated | Verbatim only |
| Layout order mistaken for flow | Only arrowheads decide direction |
| Confident output on a poor scan | Set `image_quality`, lower confidences, raise questions |

## 6. Evidence and audit

Each node may carry `evidence.text_as_read`, `location` and a normalized `bbox` `[x, y, w, h]` in 0 to 1 (add when you can estimate it; it lets a reviewer jump to the spot). Keep `notes` short and factual.

Background: zero-shot schema-constrained prompting plus optional OCR to fill empty labels is the approach evaluated for BPMN images ([Structured Extraction from Business Process Diagrams Using Vision-Language Models](https://arxiv.org/abs/2511.22448)); it motivates the structure here (explicit schema, name/type/relation split, OCR only for text, never structure).
