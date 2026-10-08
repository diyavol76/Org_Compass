#!/usr/bin/env python3
"""Minimal JSON Schema validator (stdlib only) for the bundled schemas.

Supports: type, enum, const, required, properties, additionalProperties,
items, minItems, uniqueItems, minLength, minimum, maximum, pattern,
allOf, if/then. Usage:
    validate_json.py <schema-name-or-path> <file.json> [more.json ...]
Schema name is a file stem in assets/schemas, e.g. regression-case.
"""
import json
import re
import sys
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "assets" / "schemas"

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "null": type(None),
}


def _is_type(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def validate(inst, schema, path="$"):
    errs = []
    t = schema.get("type")
    if t and not _is_type(inst, t):
        return [f"{path}: expected {t}, got {type(inst).__name__}"]
    if "const" in schema and inst != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and inst not in schema["enum"]:
        errs.append(f"{path}: {inst!r} not in {schema['enum']}")
    if isinstance(inst, str):
        if len(inst) < schema.get("minLength", 0):
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errs.append(f"{path}: {inst!r} does not match {schema['pattern']}")
    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
        if "minimum" in schema and inst < schema["minimum"]:
            errs.append(f"{path}: {inst} < minimum {schema['minimum']}")
        if "maximum" in schema and inst > schema["maximum"]:
            errs.append(f"{path}: {inst} > maximum {schema['maximum']}")
    if isinstance(inst, list):
        if len(inst) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(x, sort_keys=True) for x in inst]
            if len(seen) != len(set(seen)):
                errs.append(f"{path}: items not unique")
        if "items" in schema:
            for i, x in enumerate(inst):
                errs += validate(x, schema["items"], f"{path}[{i}]")
    if isinstance(inst, dict):
        for k in schema.get("required", []):
            if k not in inst:
                errs.append(f"{path}: missing required '{k}'")
        props = schema.get("properties", {})
        for k, v in inst.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property '{k}'")
    for sub in schema.get("allOf", []):
        errs += _conditional(inst, sub, path)
    return errs


def _conditional(inst, sub, path):
    if "if" in sub:
        if not validate(inst, sub["if"], path):
            return validate(inst, sub.get("then", {}), path)
        return validate(inst, sub["else"], path) if "else" in sub else []
    return validate(inst, sub, path)


def load_schema(name_or_path):
    p = Path(name_or_path)
    if p.exists():
        return json.loads(p.read_text())
    for cand in (SCHEMA_DIR / f"{name_or_path}.schema.json", SCHEMA_DIR / name_or_path):
        if cand.exists():
            return json.loads(cand.read_text())
    raise SystemExit(f"schema not found: {name_or_path}")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    schema = load_schema(argv[1])
    bad = 0
    for f in argv[2:]:
        try:
            data = json.loads(Path(f).read_text())
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {f}: {e}")
            bad += 1
            continue
        errs = validate(data, schema)
        if errs:
            bad += 1
            print(f"FAIL {f}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"OK   {f}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
