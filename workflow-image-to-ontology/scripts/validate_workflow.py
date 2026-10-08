#!/usr/bin/env python3
"""Validate a workflow graph JSON: JSON Schema + semantic/graph checks (stdlib only).

Usage: validate_workflow.py <graph.json> [--strict] [--json]
Exit 1 on errors (or on warnings with --strict).
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate_json as vj  # noqa: E402

SCHEMA = HERE.parent / "assets" / "schemas" / "workflow-graph.schema.json"
GATEWAYS = {"xor_gateway", "and_gateway", "or_gateway", "event_gateway"}
FLOW_TYPES = {"sequence", "dependency"}
STEP_TYPES_IMPLICIT = {"task", "subprocess", "event"}
NON_FLOW_NODES = {"data_object", "data_store", "document", "external_system", "annotation"}


def check(g):
    errs, warns, info = [], [], []
    schema = json.loads(SCHEMA.read_text())
    errs += vj.validate(g, schema)
    if errs:  # structural problems: semantic checks would just crash
        return errs, warns, info

    nodes = {n["id"]: n for n in g["nodes"]}
    lanes = {l["id"] for l in g["lanes"]}
    edges = g["edges"]

    # unique ids across every namespace
    seen = defaultdict(list)
    for kind, items in (("node", g["nodes"]), ("edge", edges), ("lane", g["lanes"])):
        for it in items:
            seen[it["id"]].append(kind)
    for i, kinds in seen.items():
        if len(kinds) > 1:
            errs.append(f"duplicate id '{i}' used by {kinds}")

    for l in g["lanes"]:
        if l.get("parent") and l["parent"] not in lanes:
            errs.append(f"lane '{l['id']}': unknown parent '{l['parent']}'")

    for n in g["nodes"]:
        if n.get("lane") and n["lane"] not in lanes:
            errs.append(f"node '{n['id']}': unknown lane '{n['lane']}'")
        if n["label_status"] == "legible" and not n["label"].strip():
            errs.append(f"node '{n['id']}': label_status=legible but label is empty")
        if n["label_status"] in ("unreadable", "none") and n["label"].strip():
            errs.append(f"node '{n['id']}': label_status={n['label_status']} but label is not empty (never guess a label)")
        if n["label_status"] in ("unreadable", "partial") and not any(n["id"] in q["about"] for q in g["open_questions"]):
            warns.append(f"node '{n['id']}': {n['label_status']} label has no open_question")
        if n["confidence"] < 0.6:
            info.append(f"low confidence node '{n['id']}' ({n['confidence']})")

    eids = set()
    out_e, in_e = defaultdict(list), defaultdict(list)
    for e in edges:
        ok = True
        for end in ("source", "target"):
            if e[end] not in nodes:
                errs.append(f"edge '{e['id']}': unknown {end} '{e[end]}'")
                ok = False
        if not ok:
            continue
        eids.add(e["id"])
        out_e[e["source"]].append(e)
        in_e[e["target"]].append(e)
        s, t = nodes[e["source"]], nodes[e["target"]]
        if e["source"] == e["target"]:
            warns.append(f"edge '{e['id']}': self loop on '{e['source']}'")
        if e["type"] == "sequence":
            ps, pt = (t, s) if g["meta"]["arrow_semantics"] == "depends_on" else (s, t)  # normalized pred/succ
            if ps["type"] == "end":
                errs.append(f"edge '{e['id']}': sequence edge leaves end node '{ps['id']}' (after normalizing arrow direction)")
            if pt["type"] == "start":
                errs.append(f"edge '{e['id']}': sequence edge enters start node '{pt['id']}' (after normalizing arrow direction)")
            for x in (s, t):
                if x["type"] in NON_FLOW_NODES:
                    errs.append(f"edge '{e['id']}': sequence edge touches non-flow node '{x['id']}' ({x['type']}); use type data/association")
        if e["type"] == "message" and s.get("lane") and s.get("lane") == t.get("lane"):
            warns.append(f"edge '{e['id']}': message flow inside one lane ('{s['lane']}'); is it really a message?")
        if e["type"] == "data" and not ({s["type"], t["type"]} & {"data_object", "data_store", "document"}):
            warns.append(f"edge '{e['id']}': data edge without data/document endpoint")

    meta = g["meta"]
    if meta["arrow_semantics"] == "unknown":
        warns.append("meta.arrow_semantics is 'unknown': dependency direction cannot be derived; add a blocking open_question")
    if meta["review_status"] == "draft" and meta["overall_confidence"] >= 0.95:
        warns.append("overall_confidence >= 0.95 on a draft: confirm it is justified")

    # flow graph
    # normalized flow graph: "pred -> succ" regardless of how arrows were drawn.
    # Entries carry 'source'/'target' already normalized so every check below reads one direction.
    flip = meta["arrow_semantics"] == "depends_on"
    flow_out, flow_in = defaultdict(list), defaultdict(list)
    for e in edges:
        if e["type"] in FLOW_TYPES and e["source"] in nodes and e["target"] in nodes:
            ne = dict(e)
            if flip:
                ne["source"], ne["target"] = e["target"], e["source"]
            flow_out[ne["source"]].append(ne)
            flow_in[ne["target"]].append(ne)

    # orphans
    for n in g["nodes"]:
        if n["type"] == "annotation":
            continue
        if not out_e[n["id"]] and not in_e[n["id"]] and len(g["nodes"]) > 1:
            warns.append(f"orphan node '{n['id']}' ('{n['label']}'): no edges at all")

    # gateways
    for n in g["nodes"]:
        if n["type"] not in GATEWAYS:
            continue
        i, o = len(flow_in[n["id"]]), len(flow_out[n["id"]])
        if i < 2 and o < 2:
            warns.append(f"gateway '{n['id']}': in={i} out={o}; neither split nor join (missed edge?)")
        if i >= 2 and o >= 2:
            warns.append(f"gateway '{n['id']}': both join and split (in={i} out={o}); consider splitting into two gateways")
        if n["type"] in ("xor_gateway", "or_gateway") and o >= 2:
            unlabeled = [e["id"] for e in flow_out[n["id"]] if not (e.get("condition") or e.get("label")) and not e.get("is_default")]
            if unlabeled:
                warns.append(f"decision '{n['id']}': outgoing edges without condition/label: {unlabeled}")

    for n in g["nodes"]:
        if n["type"] in STEP_TYPES_IMPLICIT and len(flow_in[n["id"]]) > 1:
            info.append(f"implicit merge: '{n['id']}' has {len(flow_in[n['id']])} incoming flows without a gateway (treated as ANY-one-of)")
        if n["type"] in STEP_TYPES_IMPLICIT and len(flow_out[n["id"]]) > 1 and not any(e.get("condition") for e in flow_out[n["id"]]):
            warns.append(f"implicit split: '{n['id']}' has {len(flow_out[n['id']])} outgoing flows without a gateway; AND or XOR? (add open_question or a gateway marked inferred)")

    # reachability
    starts = [n["id"] for n in g["nodes"] if n["type"] == "start"]
    ends = [n["id"] for n in g["nodes"] if n["type"] == "end"]
    if not starts:
        warns.append("no start node (add an inferred start only with inference_basis, else open_question)")
    if not ends:
        warns.append("no end node")

    def reach(seeds, adj):
        seen_, stack = set(seeds), list(seeds)
        while stack:
            x = stack.pop()
            for e in adj[x]:
                y = e["target"] if adj is flow_out else e["source"]
                if y not in seen_:
                    seen_.add(y)
                    stack.append(y)
        return seen_

    flow_nodes = [n["id"] for n in g["nodes"] if n["type"] not in NON_FLOW_NODES and n["type"] != "annotation"]
    if starts:
        r = reach(starts, flow_out)
        for i in flow_nodes:
            if i not in r and (flow_in[i] or flow_out[i]):
                warns.append(f"node '{i}' not reachable from any start")
    if ends:
        r = reach(ends, flow_in)
        for i in flow_nodes:
            if i not in r and (flow_in[i] or flow_out[i]):
                warns.append(f"node '{i}' cannot reach any end")

    # cycles (info, loops are legitimate in workflows)
    color, stack_path, loops = {}, [], []

    def dfs(u):
        color[u] = 1
        stack_path.append(u)
        for e in flow_out[u]:
            v = e["target"]
            if color.get(v, 0) == 0:
                dfs(v)
            elif color[v] == 1:
                loops.append(stack_path[stack_path.index(v):] + [v])
        stack_path.pop()
        color[u] = 2

    sys.setrecursionlimit(10000)
    for i in nodes:
        if color.get(i, 0) == 0:
            dfs(i)
    for lp in loops:
        info.append("loop: " + " -> ".join(lp))

    for q in g["open_questions"]:
        for ref in q["about"]:
            if ref not in nodes and ref not in eids and ref not in lanes:
                errs.append(f"open_question '{q['id']}': unknown reference '{ref}'")
    blocking = [q["id"] for q in g["open_questions"] if q["severity"] == "blocking" and not q.get("resolution")]
    if blocking:
        warns.append(f"unresolved blocking open_questions: {blocking}")
    return errs, warns, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graph")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        g = json.loads(Path(a.graph).read_text(encoding="utf-8"))
    except Exception as ex:  # noqa: BLE001
        print(f"FAIL cannot read {a.graph}: {ex}")
        return 1
    errs, warns, info = check(g)
    if a.json:
        print(json.dumps({"errors": errs, "warnings": warns, "info": info}, ensure_ascii=False, indent=2))
    else:
        for m in errs:
            print(f"ERROR   {m}")
        for m in warns:
            print(f"WARNING {m}")
        for m in info:
            print(f"INFO    {m}")
        print(f"{'FAIL' if errs or (a.strict and warns) else 'OK'}: {len(errs)} error(s), {len(warns)} warning(s), {len(info)} info")
    return 1 if errs or (a.strict and warns) else 0


if __name__ == "__main__":
    sys.exit(main())
