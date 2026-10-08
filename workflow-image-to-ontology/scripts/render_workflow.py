#!/usr/bin/env python3
"""Render a validated workflow graph JSON into agent/ontology-ready artifacts (stdlib only).

Usage: render_workflow.py <graph.json> [--out DIR] [--formats md,ttl,mmd]

Writes into DIR (default: next to the graph):
  <id>.md   human + agent readable specification (stable headings, derived dependency tables)
  <id>.ttl  RDF/Turtle instance data aligned with assets/ontology/workflow-vocabulary.ttl
  <id>.mmd  Mermaid flowchart, for a visual round-trip check against the source image
The JSON graph stays the canonical source; all derived facts are computed here, never hand-written.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

GATEWAYS = {"xor_gateway", "and_gateway", "or_gateway", "event_gateway"}
STEP_TYPES = {"task", "subprocess", "event", "end"}
PASS_THROUGH = GATEWAYS | {"connector"}
FLOW_TYPES = {"sequence", "dependency"}
NON_FLOW = {"data_object", "data_store", "document", "external_system", "annotation"}

CLASS_OF = {
    "start": "StartEvent", "end": "EndEvent", "task": "Task", "subprocess": "Subprocess",
    "event": "IntermediateEvent", "xor_gateway": "ExclusiveGateway", "and_gateway": "ParallelGateway",
    "or_gateway": "InclusiveGateway", "event_gateway": "EventBasedGateway", "data_object": "DataObject",
    "data_store": "DataStore", "document": "Document", "external_system": "ExternalSystem",
    "connector": "Connector", "annotation": "Annotation",
}


# ----------------------------------------------------------------- model
class Model:
    def __init__(self, g):
        self.g = g
        self.meta = g["meta"]
        self.nodes = {n["id"]: n for n in g["nodes"]}
        self.lanes = {l["id"]: l for l in g["lanes"]}
        self.edges = g["edges"]
        flip = self.meta["arrow_semantics"] == "depends_on"
        self.succ = defaultdict(list)   # pred -> [(succ, edge)]
        self.pred = defaultdict(list)   # succ -> [(pred, edge)]
        for e in self.edges:
            if e["type"] in FLOW_TYPES:
                a, b = (e["target"], e["source"]) if flip else (e["source"], e["target"])
                self.succ[a].append((b, e))
                self.pred[b].append((a, e))

    def label(self, i):
        n = self.nodes[i]
        return n["label"] or {"xor_gateway": "(XOR)", "and_gateway": "(AND)", "or_gateway": "(OR)"}.get(n["type"], f"(unlabeled {n['type']})")

    def dependencies(self):
        """Task-level dependency table derived by walking backwards through gateways."""
        res = {}
        for n in self.g["nodes"]:
            if n["type"] not in STEP_TYPES:
                continue
            found = []

            def walk(p, e, conds, via, join, seen):
                c = e.get("condition") or e.get("label") or ""
                conds = conds + ([c] if c else [])
                t = self.nodes[p]["type"]
                if t in STEP_TYPES or t == "start":
                    found.append({"node": p, "conditions": conds, "via": via, "join": join})
                    return
                if t in PASS_THROUGH:
                    if p in seen:
                        return
                    seen = seen | {p}
                    incoming = self.pred[p]
                    j = join
                    if j is None and len(incoming) > 1:
                        j = {"and_gateway": "all", "or_gateway": "any_of", "xor_gateway": "any", "event_gateway": "any"}.get(t, "any")
                    for pp, ee in incoming:
                        walk(pp, ee, conds, via + [p], j, seen)

            for p, e in self.pred[n["id"]]:
                walk(p, e, [], [], None, frozenset())
            uniq, keys = [], set()
            for f in found:
                k = (f["node"], tuple(f["conditions"]), f["join"])
                if k not in keys:
                    keys.add(k)
                    uniq.append(f)
            res[n["id"]] = uniq
        return res

    def paths(self, limit=25):
        starts = [n["id"] for n in self.g["nodes"] if n["type"] == "start"]
        out = []

        def dfs(u, path, seen):
            if len(out) >= limit:
                return
            nxt = self.succ[u]
            if not nxt:
                out.append(path)
                return
            for v, e in nxt:
                if v in seen:
                    out.append(path + [("loop-to", v)])
                    continue
                c = e.get("condition") or e.get("label") or ""
                dfs(v, path + [(c, v)], seen | {v})

        for s in starts:
            dfs(s, [("", s)], {s})
        return out

    def loops(self):
        color, path, res = {}, [], []

        def dfs(u):
            color[u] = 1
            path.append(u)
            for v, _ in self.succ[u]:
                if color.get(v, 0) == 0:
                    dfs(v)
                elif color[v] == 1:
                    res.append(path[path.index(v):] + [v])
            path.pop()
            color[u] = 2

        sys.setrecursionlimit(10000)
        for i in self.nodes:
            if color.get(i, 0) == 0:
                dfs(i)
        return res


# ----------------------------------------------------------------- helpers
def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip() or "-"


def step_name(m, i):
    return f"`{i}` {m.label(i)}"


def dep_cell(m, entries):
    if not entries:
        return "(entry)"
    groups = defaultdict(list)
    singles = []
    for f in entries:
        if f["join"]:
            groups[f["join"]].append(f)
        else:
            singles.append(f)
    parts = []
    for f in singles:
        c = f" [if: {'; '.join(f['conditions'])}]" if f["conditions"] else ""
        parts.append(step_name(m, f["node"]) + c)
    names = {"all": "ALL of", "any": "ANY one of", "any_of": "ANY (one or more) of"}
    for j, fs in groups.items():
        seen, items = set(), []
        for f in fs:
            if f["node"] in seen:
                continue
            seen.add(f["node"])
            c = f" [if: {'; '.join(f['conditions'])}]" if f["conditions"] else ""
            items.append(step_name(m, f["node"]) + c)
        parts.append(f"{names[j]}: " + ", ".join(items))
    return "<br>".join(p.replace("|", "\\|") for p in parts)


# ----------------------------------------------------------------- markdown
def render_md(m: Model, graph_file: str) -> str:
    g, meta = m.g, m.meta
    nodes = g["nodes"]
    deps = m.dependencies()
    steps = [n for n in nodes if n["type"] in STEP_TYPES]
    gws = [n for n in nodes if n["type"] in GATEWAYS]
    starts = [n["id"] for n in nodes if n["type"] == "start"]
    ends = [n["id"] for n in nodes if n["type"] == "end"]
    entries = [n["id"] for n in steps if all(f["node"] in starts for f in deps[n["id"]]) and n["type"] != "end"]
    loops = m.loops()
    low = [n for n in nodes if n["confidence"] < 0.6]
    inferred_n = [n for n in nodes if n["status"] == "inferred"]
    inferred_e = [e for e in m.edges if e["status"] == "inferred"]
    L = []
    a = L.append
    a("---")
    a(f"id: {meta['id']}")
    a("type: workflow-extraction")
    a(f"title: {json.dumps(meta['title'], ensure_ascii=False)}")
    a(f"source_image: {json.dumps(meta['source_image'], ensure_ascii=False)}")
    a(f"notation: {meta['notation']}")
    a(f"arrow_semantics: {meta['arrow_semantics']}")
    a(f"language: {meta['language']}")
    a(f"review_status: {meta['review_status']}")
    a(f"overall_confidence: {meta['overall_confidence']}")
    a(f"canonical_graph: {graph_file}")
    a(f"counts: {{nodes: {len(nodes)}, steps: {len(steps)}, gateways: {len(gws)}, edges: {len(m.edges)}, lanes: {len(g['lanes'])}}}")
    a("---")
    a(f"# {meta['title']}")
    a("")
    if meta.get("description"):
        a(meta["description"])
        a("")
    a(f"> Extracted from `{meta['source_image']}` (notation: {meta['notation']}, arrows read as: **{meta['arrow_semantics']}**). "
      f"Review status: **{meta['review_status']}**. Source of truth: `{graph_file}`; this file is derived, do not hand-edit.")
    a("")
    a("## 1. Summary")
    a("")
    a(f"- Steps: {len(steps)} · gateways: {len(gws)} · lanes/participants: {len(g['lanes'])} · edges: {len(m.edges)}")
    a(f"- Start: {', '.join(step_name(m, s) for s in starts) or 'none drawn'}")
    a(f"- End: {', '.join(step_name(m, s) for s in ends) or 'none drawn'}")
    a(f"- First steps (entry): {', '.join(step_name(m, s) for s in entries) or 'n/a'}")
    a(f"- Decision gateways: {sum(1 for n in gws if n['type'] in ('xor_gateway', 'or_gateway', 'event_gateway'))} · parallel gateways: {sum(1 for n in gws if n['type'] == 'and_gateway')} · loops: {len(loops)}")
    a(f"- Inferred (not drawn): {len(inferred_n)} node(s), {len(inferred_e)} edge(s) · low-confidence (<0.6) nodes: {len(low)} · open questions: {len(g['open_questions'])}")
    a("")
    a("## 2. Participants")
    a("")
    if g["lanes"]:
        a("| id | label | kind | parent |")
        a("|---|---|---|---|")
        for l in g["lanes"]:
            a(f"| `{l['id']}` | {cell(l['label'])} | {l['kind']} | {cell(l.get('parent', ''))} |")
    else:
        a("No lanes or pools are drawn.")
    a("")
    a("## 3. Steps and elements")
    a("")
    a("| id | label | type | participant | confidence | status |")
    a("|---|---|---|---|---|---|")
    for n in nodes:
        lane = m.lanes[n["lane"]]["label"] if n.get("lane") else ""
        lab = cell(n["label"]) if n["label"] else f"*{n['label_status']}*"
        a(f"| `{n['id']}` | {lab} | {n['type']} | {cell(lane)} | {n['confidence']} | {n['status']} |")
    a("")
    a("## 4. Control flow")
    a("")
    a("Edges exactly as drawn (`source -> target`).")
    a("")
    a("| id | from | to | type | condition / label | default | status |")
    a("|---|---|---|---|---|---|---|")
    for e in m.edges:
        c = e.get("condition") or e.get("label") or ""
        a(f"| `{e['id']}` | `{e['source']}` | `{e['target']}` | {e['type']} | {cell(c)} | {'yes' if e.get('is_default') else ''} | {e['status']} |")
    a("")
    a("## 5. Task dependencies (derived)")
    a("")
    if meta["arrow_semantics"] == "unknown":
        a("**Not derivable**: arrow semantics are unknown. Resolve the blocking open question first.")
    else:
        a("A step may start only after its dependencies are satisfied. `ALL of` = parallel join (every one required). `ANY one of` = exclusive merge (exactly one branch arrives). Conditions come from decision branches.")
        a("")
        a("| step | depends on | participant |")
        a("|---|---|---|")
        for n in steps:
            lane = m.lanes[n["lane"]]["label"] if n.get("lane") else ""
            a(f"| {step_name(m, n['id'])} | {dep_cell(m, deps[n['id']])} | {cell(lane)} |")
    a("")
    a("## 6. Decision points")
    a("")
    dec = [n for n in gws if len(m.succ[n["id"]]) > 1 and n["type"] != "and_gateway"]
    if dec:
        for n in dec:
            a(f"### `{n['id']}` {m.label(n['id'])} ({n['type']})")
            a("")
            for v, e in m.succ[n["id"]]:
                c = e.get("condition") or e.get("label") or "(no condition drawn)"
                d = " **(default)**" if e.get("is_default") else ""
                a(f"- if {c}{d} -> {step_name(m, v)}")
            a("")
    else:
        a("None.")
        a("")
    a("## 7. Parallelism")
    a("")
    par = [n for n in gws if n["type"] == "and_gateway" and len(m.succ[n["id"]]) > 1]
    if par:
        for n in par:
            a(f"- `{n['id']}` forks into: " + ", ".join(step_name(m, v) for v, _ in m.succ[n["id"]]))
    else:
        a("None drawn.")
    a("")
    a("## 8. Loops and rework")
    a("")
    if loops:
        for lp in loops:
            a("- " + " -> ".join(f"`{x}`" for x in lp))
    else:
        a("None.")
    a("")
    a("## 9. Execution paths (up to 25, simple paths)")
    a("")
    ps = m.paths()
    if ps:
        for k, p in enumerate(ps, 1):
            segs = []
            for c, v in p:
                if c == "loop-to":
                    segs.append(f"(loops back to `{v}`)")
                    continue
                if m.nodes[v]["type"] in NON_FLOW:
                    continue
                if m.nodes[v]["type"] in PASS_THROUGH and not c:
                    continue
                tag = f"[{c}] " if c else ""
                segs.append(f"{tag}{m.label(v)}")
            a(f"{k}. " + " -> ".join(segs))
    else:
        a("No start node, so no paths enumerated.")
    a("")
    a("## 10. Review queue")
    a("")
    a("Resolve these before treating the specification as `reviewed`.")
    a("")
    if g["open_questions"]:
        a("| id | severity | about | question | candidates |")
        a("|---|---|---|---|---|")
        for q in g["open_questions"]:
            a(f"| {q['id']} | {q['severity']} | {cell(', '.join(q['about']))} | {cell(q['question'])} | {cell('; '.join(q.get('candidates', [])))} |")
        a("")
    else:
        a("No open questions.")
        a("")
    if inferred_n or inferred_e:
        a("Inferred elements (not literally drawn):")
        a("")
        for n in inferred_n:
            a(f"- node `{n['id']}`: {n['inference_basis']}")
        for e in inferred_e:
            a(f"- edge `{e['id']}` (`{e['source']}` -> `{e['target']}`): {e['inference_basis']}")
        a("")
    if low:
        a("Low-confidence nodes: " + ", ".join(f"`{n['id']}` ({n['confidence']})" for n in low))
        a("")
    a("## 11. Ontology mapping")
    a("")
    a("- Vocabulary: `assets/ontology/workflow-vocabulary.ttl` (prefix `wfo:`), aligned to PKO (`pko:Procedure`, `pko:Step`, `pko:hasStep`, `pko:nextStep`), P-Plan (`p-plan:Step`, `p-plan:isPrecededBy`) and PROV-O (`prov:Agent`).")
    a(f"- Instance data: `{meta['id']}.ttl`. Every drawn arrow is also reified as a `wfo:Transition` so conditions are queryable.")
    a("- Derived relations: `wfo:precedes`, `wfo:dependsOn` (step-level, gateways collapsed), `wfo:performedBy` (lane), `wfo:reads` / `wfo:writes` (data edges).")
    a("")
    a("## 12. How an agent should use this document")
    a("")
    a("1. Treat section 5 as the dependency contract: do not schedule or reason about a step before its dependencies.")
    a("2. Honor `ALL of` / `ANY one of` and branch conditions literally; they come from gateway types, not guesses.")
    a("3. Anything in section 10 is unconfirmed. Ask the process owner or escalate instead of assuming; never fill gaps silently.")
    a("4. For exact ids, types and edge semantics, read the canonical JSON graph, not this prose.")
    a("")
    return "\n".join(L)


# ----------------------------------------------------------------- mermaid
def mid(i):
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", i)


def mlabel(s):
    return (s or "?").replace('"', "#quot;").replace("\n", " ")


def render_mmd(m: Model) -> str:
    shape = {
        "start": ("([", "])"), "end": ("(((", ")))"), "task": ("[", "]"), "subprocess": ("[[", "]]"),
        "event": ("((", "))"), "xor_gateway": ("{", "}"), "and_gateway": ("{{", "}}"), "or_gateway": ("{{", "}}"),
        "event_gateway": ("{", "}"), "data_object": ("[(", ")]"), "data_store": ("[(", ")]"), "document": (">", "]"),
        "external_system": ("[/", "/]"), "connector": ("((", "))"), "annotation": ("[", "]"),
    }
    sym = {"xor_gateway": "X", "and_gateway": "+", "or_gateway": "O", "event_gateway": "E"}
    out = ["%% Auto-generated from the workflow graph. Compare visually with the source image.", "flowchart TD"]

    def node_line(n):
        o, c = shape[n["type"]]
        lab = n["label"] or sym.get(n["type"], "?")
        if n["type"] in sym and n["label"]:
            lab = f"{sym[n['type']]} {n['label']}"
        return f'{mid(n["id"])}{o}"{mlabel(lab)}"{c}'

    laned = defaultdict(list)
    free = []
    for n in m.g["nodes"]:
        (laned[n["lane"]] if n.get("lane") in m.lanes else free).append(n)
    for lid, ns in laned.items():
        out.append(f'  subgraph {mid("lane_" + lid)}["{mlabel(m.lanes[lid]["label"])}"]')
        out.extend("    " + node_line(n) for n in ns)
        out.append("  end")
    out.extend("  " + node_line(n) for n in free)
    for e in m.edges:
        c = e.get("condition") or e.get("label") or ""
        lab = f'|"{mlabel(c)}"|' if c else ""
        a, b = mid(e["source"]), mid(e["target"])
        if e["type"] == "message":
            out.append(f"  {a} -.->{lab} {b}")
        elif e["type"] in ("data", "association"):
            out.append(f"  {a} -.-{lab} {b}")
        else:
            out.append(f"  {a} -->{lab} {b}")
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------- turtle
def lit(s, lang=None):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"' + (f"@{lang}" if lang else "")


def render_ttl(m: Model) -> str:
    meta = m.meta
    base = f"https://orgcompass.example/workflow/{meta['id']}#"
    lang = meta["language"] if re.match(r"^[a-zA-Z]{2,3}(-[A-Za-z0-9]+)*$", meta["language"]) else None
    L = [
        "@prefix wfo: <https://orgcompass.example/ontology/workflow#> .",
        "@prefix pko: <https://w3id.org/pko#> .",
        "@prefix p-plan: <http://purl.org/net/p-plan#> .",
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        f"@prefix : <{base}> .",
        "# NOTE: orgcompass.example is a placeholder namespace; replace it with your organization's before publishing.",
        "",
    ]
    ids = lambda i: ":" + re.sub(r"[^A-Za-z0-9_-]", "_", i)  # noqa: E731
    proc = ":process"
    stepsid = [ids(n["id"]) for n in m.g["nodes"] if n["type"] in ("task", "subprocess")]
    L.append(f"{proc} a wfo:Process, pko:Procedure, p-plan:Plan ;")
    L.append(f"    rdfs:label {lit(meta['title'], lang)} ;")
    L.append(f"    wfo:sourceImage {lit(meta['source_image'])} ;")
    L.append(f"    wfo:notation {lit(meta['notation'])} ;")
    L.append(f"    wfo:arrowSemantics {lit(meta['arrow_semantics'])} ;")
    L.append(f"    wfo:reviewStatus {lit(meta['review_status'])} ;")
    if stepsid:
        L.append(f"    wfo:confidence {meta['overall_confidence']} ;")
        L.append("    pko:hasStep " + ", ".join(stepsid) + " .")
    else:
        L.append(f"    wfo:confidence {meta['overall_confidence']} .")
    L.append("")
    for l in m.g["lanes"]:
        L.append(f"{ids(l['id'])} a wfo:Participant, prov:Agent ; rdfs:label {lit(l['label'], lang)} ; wfo:participantKind {lit(l['kind'])} .")
        if l.get("parent"):
            L.append(f"{ids(l['id'])} wfo:partOf {ids(l['parent'])} .")
    L.append("")
    for n in m.g["nodes"]:
        t = ["wfo:" + CLASS_OF[n["type"]]]
        if n["type"] in ("task", "subprocess"):
            t += ["pko:Step", "p-plan:Step"]
        props = [f"wfo:inProcess {proc}", f"wfo:status {lit(n['status'])}", f"wfo:confidence {n['confidence']}"]
        if n["label"]:
            props.insert(0, f"rdfs:label {lit(n['label'], lang)}")
        if n.get("description"):
            props.append(f"rdfs:comment {lit(n['description'], lang)}")
        if n.get("lane"):
            props.append(f"wfo:performedBy {ids(n['lane'])}")
        if n.get("system"):
            props.append(f"wfo:usesSystem {lit(n['system'])}")
        if n["status"] == "inferred":
            props.append(f"wfo:inferenceBasis {lit(n['inference_basis'])}")
        L.append(f"{ids(n['id'])} a {', '.join(t)} ;")
        L.append("    " + " ;\n    ".join(props) + " .")
    L.append("")
    flow_direct = set()
    for e in m.edges:
        props = [f"wfo:flowType {lit(e['type'])}", f"wfo:from {ids(e['source'])}", f"wfo:to {ids(e['target'])}",
                 f"wfo:status {lit(e['status'])}", f"wfo:confidence {e['confidence']}"]
        if e.get("condition"):
            props.append(f"wfo:condition {lit(e['condition'], lang)}")
        if e.get("label"):
            props.append(f"rdfs:label {lit(e['label'], lang)}")
        if e.get("is_default"):
            props.append('wfo:isDefault "true"^^xsd:boolean')
        L.append(f"{ids(e['id'])} a wfo:Transition ;")
        L.append("    " + " ;\n    ".join(props) + " .")
        if e["type"] == "message":
            L.append(f"{ids(e['source'])} wfo:sendsMessageTo {ids(e['target'])} .")
        elif e["type"] == "data":
            s, t_ = m.nodes[e["source"]], m.nodes[e["target"]]
            if s["type"] in ("data_object", "data_store", "document"):
                L.append(f"{ids(e['target'])} wfo:reads {ids(e['source'])} .")
            else:
                L.append(f"{ids(e['source'])} wfo:writes {ids(e['target'])} .")
    L.append("")
    for a, lst in m.succ.items():
        for b, e in lst:
            L.append(f"{ids(a)} wfo:precedes {ids(b)} .")
            if m.nodes[a]["type"] in ("task", "subprocess") and m.nodes[b]["type"] in ("task", "subprocess") and len(lst) == 1:
                L.append(f"{ids(a)} pko:nextStep {ids(b)} .")
                L.append(f"{ids(b)} p-plan:isPrecededBy {ids(a)} .")
    L.append("")
    for step, entries in m.dependencies().items():
        for f in entries:
            if m.nodes[f["node"]]["type"] == "start":
                continue
            L.append(f"{ids(step)} wfo:dependsOn {ids(f['node'])} .")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graph")
    ap.add_argument("--out")
    ap.add_argument("--formats", default="md,ttl,mmd")
    a = ap.parse_args()
    gp = Path(a.graph)
    g = json.loads(gp.read_text(encoding="utf-8"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import validate_workflow as vw  # noqa: E402
    errs, _, _ = vw.check(g)
    if errs:
        print("Refusing to render: graph has validation errors; run validate_workflow.py", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    m = Model(g)
    out = Path(a.out) if a.out else gp.parent
    out.mkdir(parents=True, exist_ok=True)
    fid = g["meta"]["id"]
    fmts = set(a.formats.split(","))
    if "md" in fmts:
        (out / f"{fid}.md").write_text(render_md(m, gp.name), encoding="utf-8")
    if "ttl" in fmts:
        (out / f"{fid}.ttl").write_text(render_ttl(m), encoding="utf-8")
    if "mmd" in fmts:
        (out / f"{fid}.mmd").write_text(render_mmd(m), encoding="utf-8")
    print(f"rendered {', '.join(sorted(fmts))} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
