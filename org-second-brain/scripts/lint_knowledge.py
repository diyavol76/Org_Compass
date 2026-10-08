#!/usr/bin/env python3
"""Deterministic linter for an org-second-brain knowledge base (stdlib only).

    lint_knowledge.py <kb-root> [--fix-backrefs] [--json] [--strict]

Checks: frontmatter schema, id/filename/prefix, id collisions, dangling refs
(depends_on, loads, calls, routes_to, referenced_by, backticked ids in
routing bodies), bidirectional edge consistency, dependency cycles, token
budgets, orphan active files, recipe/knowledge separation heuristics,
stale reviews. Exit 1 on errors (and on warnings with --strict).
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_json import load_schema, validate  # noqa: E402

PREFIX = {"position": "pos", "taxonomy": "tax", "routing": "rt", "gateway": "gw", "recipe": "rcp"}
ID_RE = re.compile(r"`((?:pos|tax|rt|gw|rcp)-[a-z0-9]+(?:-[a-z0-9]+)*)`")
LIST_KEYS = {"applies_when", "depends_on", "referenced_by", "routes_to", "sources", "loads",
             "calls", "checkpoints", "escalates_when", "done_when"}
INT_KEYS = {"version", "token_budget"}


def parse_scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def parse_frontmatter(text):
    """Return (dict, body, error). Restricted YAML subset."""
    if not text.startswith("---"):
        return None, text, "missing frontmatter"
    lines = text.split("\n")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None, text, "unterminated frontmatter"
    data, i = {}, 1
    while i < end:
        ln = lines[i]
        if not ln.strip() or ln.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", ln)
        if not m:
            return None, text, f"line {i + 1}: unsupported YAML ({ln.strip()[:40]})"
        k, v = m.group(1), m.group(2).strip()
        if v == "":
            items, j = [], i + 1
            while j < end and re.match(r"^\s*-\s+", lines[j]):
                items.append(parse_scalar(re.sub(r"^\s*-\s+", "", lines[j])))
                j += 1
            if items or k in LIST_KEYS:
                data[k] = items
                i = j
                continue
            data[k] = ""
        elif v.startswith("["):
            if not v.endswith("]"):
                return None, text, f"line {i + 1}: multi-line lists unsupported"
            inner = v[1:-1].strip()
            data[k] = [parse_scalar(x) for x in inner.split(",")] if inner else []
        else:
            data[k] = parse_scalar(v)
        i += 1
    return data, "\n".join(lines[end + 1:]), None


def set_list(path, key, values):
    """Rewrite one list key in a file's frontmatter as an inline list."""
    lines = path.read_text().split("\n")
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    new = f"{key}: [" + ", ".join(sorted(values)) + "]"
    for i in range(1, end):
        if re.match(rf"^{key}:", lines[i]):
            j = i + 1
            while j < end and re.match(r"^\s*-\s+", lines[j]):
                j += 1
            lines[i:j] = [new]
            break
    else:
        lines.insert(end, new)
    path.write_text("\n".join(lines))


def tokens(text):
    return (len(text) + 3) // 4


class Linter:
    def __init__(self, root, cfg):
        self.root, self.cfg = root, cfg
        self.issues = []
        self.files = {}  # id -> dict(path, fm, body, kind)

    def add(self, level, code, file, msg):
        self.issues.append({"level": level, "code": code, "file": str(file), "message": msg})

    def collect(self):
        paths = self.cfg["paths"]
        for kind, sub in (("knowledge", paths["knowledge"]), ("recipe", paths["recipes"])):
            base = self.root / sub
            for p in sorted(base.rglob("*.md")) if base.exists() else []:
                rel = p.relative_to(self.root)
                fm, body, err = parse_frontmatter(p.read_text())
                if err:
                    self.add("error", "frontmatter", rel, err)
                    continue
                schema = load_schema("recipe" if kind == "recipe" else "knowledge-file")
                for e in validate(fm, schema):
                    self.add("error", "schema", rel, e)
                fid = fm.get("id")
                if not isinstance(fid, str):
                    continue
                if fid in self.files:
                    self.add("error", "id-collision", rel,
                             f"id '{fid}' also used by {self.files[fid]['rel']}")
                    continue
                if p.stem != fid:
                    self.add("error", "id-filename", rel, f"filename stem '{p.stem}' != id '{fid}'")
                t = fm.get("type")
                if t in PREFIX and not fid.startswith(PREFIX[t] + "-"):
                    self.add("error", "id-prefix", rel, f"type '{t}' requires id prefix '{PREFIX[t]}-'")
                if kind == "recipe" and t != "recipe":
                    self.add("error", "type-dir", rel, "files under recipes/ must have type: recipe")
                if kind == "knowledge" and t == "recipe":
                    self.add("error", "type-dir", rel, "recipes belong under recipes/")
                self.files[fid] = {"path": p, "rel": rel, "fm": fm, "body": body, "kind": kind}

    def edges(self, fid):
        """Outgoing edges as (target, edge_kind)."""
        fm = self.files[fid]["fm"]
        out = []
        for key in ("depends_on", "routes_to", "loads", "calls"):
            for t in fm.get(key, []) or []:
                out.append((t, key))
        return out

    def check_refs(self):
        for fid, f in self.files.items():
            for key in ("depends_on", "routes_to", "loads", "calls", "referenced_by"):
                for t in f["fm"].get(key, []) or []:
                    if t not in self.files:
                        self.add("error", "dangling-ref", f["rel"], f"{key} -> '{t}' does not exist")
            if f["fm"].get("type") == "routing":
                for t in set(ID_RE.findall(f["body"])):
                    if t not in self.files:
                        self.add("error", "dangling-ref", f["rel"], f"body references '{t}', which does not exist")
                    elif t not in (f["fm"].get("routes_to") or []):
                        self.add("warning", "routes-to-missing", f["rel"],
                                 f"body mentions '{t}' but routes_to does not list it")

    def expected_backrefs(self):
        exp = {fid: set() for fid in self.files}
        for fid in self.files:
            for t, _ in self.edges(fid):
                if t in exp:
                    exp[t].add(fid)
        return exp

    def check_backrefs(self, fix):
        exp = self.expected_backrefs()
        for fid, f in self.files.items():
            have = set(f["fm"].get("referenced_by", []) or [])
            if have == exp[fid]:
                continue
            if fix:
                set_list(f["path"], "referenced_by", exp[fid])
                f["fm"]["referenced_by"] = sorted(exp[fid])
                self.add("info", "backref-fixed", f["rel"], f"referenced_by set to {sorted(exp[fid])}")
                continue
            for m in sorted(exp[fid] - have):
                self.add("error", "backref-missing", f["rel"], f"'{m}' points here but is not in referenced_by")
            for m in sorted(have - exp[fid]):
                if m in self.files:
                    self.add("error", "backref-stale", f["rel"], f"referenced_by lists '{m}' which has no edge here")

    def check_cycles(self):
        graph = {fid: [t for t, k in self.edges(fid) if k in ("depends_on", "calls") and t in self.files]
                 for fid in self.files}
        state, stack, seen = {}, [], set()

        def dfs(n):
            state[n] = 1
            stack.append(n)
            for m in graph[n]:
                if state.get(m) == 1:
                    cyc = stack[stack.index(m):] + [m]
                    key = frozenset(cyc)
                    if key not in seen:
                        seen.add(key)
                        self.add("error", "cycle", self.files[m]["rel"], " -> ".join(cyc))
                elif m not in state:
                    dfs(m)
            stack.pop()
            state[n] = 2

        for n in graph:
            if n not in state:
                dfs(n)

    def check_budgets(self):
        b = self.cfg["budgets"]
        total = 0
        for fid, f in self.files.items():
            n = tokens(f["path"].read_text())
            total += n
            hard = f["fm"].get("token_budget") or b["file_hard_tokens"]
            soft = min(b["file_soft_tokens"], hard)
            if n > hard:
                self.add("error", "budget", f["rel"], f"~{n} tokens exceeds hard budget {hard}")
            elif n > soft:
                self.add("warning", "budget", f["rel"], f"~{n} tokens exceeds soft budget {soft}")
        if "total_tokens" in b and total > b["total_tokens"]:
            self.add("error", "budget-total", self.cfg["paths"]["knowledge"],
                     f"~{total} total tokens exceeds {b['total_tokens']}")

    def check_orphans_and_separation(self):
        for fid, f in self.files.items():
            fm, body = f["fm"], f["body"]
            is_router = fm.get("phase") == "router"
            if fm.get("status") == "active" and not is_router and not (fm.get("referenced_by") or []):
                self.add("warning", "orphan", f["rel"], "active file is not referenced by any routing index, recipe or file")
            if f["kind"] == "knowledge" and re.search(r"^#{2,4}\s*Step\s+\d+", body, re.M):
                self.add("warning", "separation", f["rel"], "knowledge file contains recipe-style steps; move procedure to a recipe")
            if f["kind"] == "recipe" and re.search(r"^#{1,3}\s*(Position|Rationale|Boundary examples)\s*$", body, re.M):
                self.add("warning", "separation", f["rel"], "recipe contains position-style sections; move domain facts to a knowledge file")
            if f["kind"] == "recipe":
                step_ids = set(re.findall(r"\(id:\s*(s\d+)\)", body))
                for c in fm.get("checkpoints", []) or []:
                    if c not in step_ids:
                        self.add("error", "checkpoint-step", f["rel"], f"checkpoint '{c}' has no matching step")
                loaded_in_steps = set()
                for ln in body.split("\n"):
                    if ln.startswith("Load:"):
                        loaded_in_steps.update(ID_RE.findall(ln))
                for t in loaded_in_steps - set(fm.get("loads", []) or []):
                    self.add("error", "load-undeclared", f["rel"], f"step loads '{t}' not declared in frontmatter loads")
                for t in set(fm.get("loads", []) or []) - loaded_in_steps:
                    self.add("warning", "load-unused", f["rel"], f"'{t}' declared in loads but no step lists it")
                if fm.get("status") == "active" and not step_ids:
                    self.add("error", "no-steps", f["rel"], "active recipe has no '(id: sN)' steps")
            stale = self.cfg["budgets"].get("stale_review_days")
            lr = fm.get("last_reviewed")
            if stale and isinstance(lr, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", lr) and fm.get("status") == "active":
                try:
                    age = (dt.date.today() - dt.date.fromisoformat(lr)).days
                    if age > stale:
                        self.add("warning", "stale", f["rel"], f"last reviewed {age} days ago (limit {stale})")
                except ValueError:
                    self.add("error", "schema", f["rel"], f"invalid date {lr}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--fix-backrefs", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    cfg_path = root / "kb.config.json"
    if not cfg_path.exists():
        print(f"error: {cfg_path} not found (run scaffold.py first)", file=sys.stderr)
        return 2
    cfg = json.loads(cfg_path.read_text())
    cfg_errs = validate(cfg, load_schema("kb-config"))
    lint = Linter(root, cfg)
    for e in cfg_errs:
        lint.add("error", "config", "kb.config.json", e)
    lint.collect()
    lint.check_refs()
    lint.check_backrefs(a.fix_backrefs)
    lint.check_cycles()
    lint.check_budgets()
    lint.check_orphans_and_separation()

    errors = [i for i in lint.issues if i["level"] == "error"]
    warns = [i for i in lint.issues if i["level"] == "warning"]
    if a.json:
        print(json.dumps({"files": len(lint.files), "errors": len(errors), "warnings": len(warns),
                          "issues": lint.issues}, indent=2))
    else:
        for i in lint.issues:
            print(f"{i['level'].upper():7} [{i['code']}] {i['file']}: {i['message']}")
        print(f"\n{len(lint.files)} files, {len(errors)} errors, {len(warns)} warnings")
    return 1 if errors or (a.strict and warns) else 0


if __name__ == "__main__":
    sys.exit(main())
