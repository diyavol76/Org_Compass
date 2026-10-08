---
description: Extract a workflow diagram image into an ontology-ready graph, spec document, Turtle and Mermaid
---

Load the `workflow-image-to-ontology` skill. Image: $1. Extra context from the user (optional): $2.
Run the extraction protocol (delegate to `@wf-extractor`), validate, render, then run `@wf-verifier` in a fresh context with only the image and the graph JSON. Present: output file list, validator warnings, verifier findings, open questions. Do not mark the result `reviewed`.
