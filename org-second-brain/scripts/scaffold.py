#!/usr/bin/env python3
"""Create an org-second-brain workspace from the bundled templates.

    scaffold.py <kb-root> --domain "Name" --risk-tier high [--with-opencode] [--language en]
Never overwrites existing files.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TPL = SKILL / "assets" / "templates"
DIRS = [
    "knowledge/positions", "knowledge/taxonomy", "knowledge/routing", "knowledge/gateways",
    "recipes", "sources", "eval/benchmarks", "eval/regression", "eval/runs",
    "feedback/traces", "feedback/issues", "feedback/runs",
]
POLICY = {"high": "every_step", "medium": "phase_boundary", "low": "final_only"}
REVIEWERS = {"high": 2, "medium": 1, "low": 1}


def put(src, dst, subs=None):
    if dst.exists():
        print(f"skip   {dst} (exists)")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text()
    for k, v in (subs or {}).items():
        text = text.replace(k, v)
    dst.write_text(text)
    print(f"create {dst}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--domain", default="example-domain")
    ap.add_argument("--risk-tier", choices=["low", "medium", "high"], default="high")
    ap.add_argument("--language", default="en")
    ap.add_argument("--with-opencode", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
        (root / d / ".gitkeep").touch()

    cfg = json.loads((TPL / "kb.config.json").read_text())
    cfg.update(domain=a.domain, language=a.language, risk_tier=a.risk_tier,
               checkpoint_policy=POLICY[a.risk_tier])
    cfg["improvement"]["required_reviewers"] = REVIEWERS[a.risk_tier]
    cfg_path = root / "kb.config.json"
    if cfg_path.exists():
        print(f"skip   {cfg_path} (exists)")
    else:
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
        print(f"create {cfg_path}")

    subs = {"{{DOMAIN}}": a.domain, "{{RISK_TIER}}": a.risk_tier}
    put(TPL / "AGENTS.md", root / "AGENTS.md", subs)
    put(TPL / "sources-index.md", root / "sources" / "INDEX.md")
    put(TPL / "judge-rubric.md", root / "eval" / "judge-rubric.md")
    # Starter files stay out of the lint graph's way: copy nothing example-like by default;
    # templates remain in the skill and are copied on demand by the agent.

    if a.with_opencode:
        for sub in ("agents", "commands"):
            for f in (SKILL / "assets" / "opencode" / sub).glob("*.md"):
                put(f, root / ".opencode" / sub / f.name)
    print(f"\nworkspace ready: {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
