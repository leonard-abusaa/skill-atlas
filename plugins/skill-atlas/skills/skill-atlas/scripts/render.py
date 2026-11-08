#!/usr/bin/env python3
"""Skill Atlas renderer.

Validates an atlas-data.json file against the schema in reference/schema.md,
fills in safe defaults, and injects it into assets/template.html.

Usage:
  python3 render.py atlas-data.json [--out skill-atlas.html]
Exit code 1 means the data has errors that would break the page; the messages say what to fix.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
KINDS = {"skill", "plugin", "connector"}
SUBTYPES = {None, "command", "agent"}
WORLDS = {"claude-app", "claude-code"}
FLAG_TYPES = {"duplicate", "overlap", "pair", "region", "health", "info"}
GROUP_KINDS = {"duplicate", "overlap", "pair"}
CONFIDENCE = {"confirmed", "matched", "inferred", "unknown"}
STATUSES = {"connected", "needs_reconnect", "not_connected", "unchecked"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--out", default="skill-atlas.html")
    a = ap.parse_args()

    data = json.load(open(a.data, encoding="utf-8"))
    cats = json.load(open(os.path.join(SKILL, "assets", "categories.json"), encoding="utf-8"))["categories"]
    cat_ids = {c["id"] for c in cats}
    errors, warnings = [], []

    # Categories always come from the shipped list, in its order
    data["categories"] = [{"id": c["id"], "label": c["label"], "blurb": c["blurb"]} for c in cats]
    data.setdefault("generatedAt", "")
    data.setdefault("environment", "Claude")
    data.setdefault("groups", [])
    data.setdefault("claudeCode", None)
    data.setdefault("changes", None)

    items = data.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items: must be a non-empty list")
        items = []
    ids = set()
    for n, i in enumerate(items):
        where = f"items[{n}] ({i.get('id', '?')})"
        for k in ("id", "kind", "name", "category", "summary", "world"):
            if not i.get(k):
                errors.append(f"{where}: missing {k}")
        if i.get("id") in ids:
            errors.append(f"{where}: duplicate id")
        ids.add(i.get("id"))
        if i.get("kind") not in KINDS:
            errors.append(f"{where}: kind must be one of {sorted(KINDS)}")
        if i.get("subtype") not in SUBTYPES:
            errors.append(f"{where}: subtype must be command, agent or absent")
        if i.get("world") not in WORLDS:
            errors.append(f"{where}: world must be claude-app or claude-code")
        if i.get("category") not in cat_ids:
            errors.append(f"{where}: category '{i.get('category')}' is not in assets/categories.json")
        for k, v in (("examples", []), ("flags", []), ("runs", []), ("runBy", []), ("groups", []), ("description", "")):
            i.setdefault(k, v)
        i.setdefault("invoke", None)
        i.setdefault("plugin", None)
        i.setdefault("source", "")
        if i["kind"] == "plugin":
            i.setdefault("skills", [])
        if i["kind"] == "connector":
            if i.get("status") not in STATUSES:
                warnings.append(f"{where}: status '{i.get('status')}' unknown, set to unchecked")
                i["status"] = "unchecked"
        o = i.get("origin")
        if not isinstance(o, dict) or not o.get("label"):
            warnings.append(f"{where}: no origin, set to Unknown")
            i["origin"] = {"label": "Unknown", "detail": "", "confidence": "unknown"}
        elif o.get("confidence") not in CONFIDENCE:
            o["confidence"] = "unknown"
        for f in i["flags"]:
            if f.get("type") not in FLAG_TYPES:
                errors.append(f"{where}: flag type '{f.get('type')}' not allowed")
        if len(i["summary"]) > 160:
            warnings.append(f"{where}: summary longer than 160 characters")

    # Groups: drop members that don't exist, then re-derive item.groups from them
    for g_index, g in enumerate(data["groups"]):
        if g.get("kind") not in GROUP_KINDS:
            errors.append(f"groups[{g_index}]: kind must be duplicate, overlap or pair")
        g.setdefault("world", "claude-app")
        missing = [m for m in g.get("members", []) if m not in ids]
        if missing:
            warnings.append(f"groups[{g_index}] '{g.get('title')}': dropped unknown members {missing}")
            g["members"] = [m for m in g.get("members", []) if m in ids]
        if g.get("keep") and g["keep"] not in ids:
            g["keep"] = None
    by_id = {i["id"]: i for i in items}
    for i in items:
        i["groups"] = []
        for f in i["flags"]:
            if "group" in f and not (isinstance(f["group"], int) and 0 <= f["group"] < len(data["groups"])):
                errors.append(f"{i['id']}: flag points to group {f.get('group')}, which doesn't exist")
    for g_index, g in enumerate(data["groups"]):
        for m in g["members"]:
            by_id[m]["groups"].append(g_index)
    for i in items:
        for k in ("runs", "runBy", "skills"):
            if k in i:
                i[k] = [x for x in i[k] if x in ids]
        if i.get("alsoIn") and i["alsoIn"] not in ids:
            i.pop("alsoIn")

    for w in warnings:
        print("warning:", w, file=sys.stderr)
    if errors:
        for e in errors:
            print("error:", e, file=sys.stderr)
        sys.exit(1)

    tpl = open(os.path.join(SKILL, "assets", "template.html"), encoding="utf-8").read()
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = tpl.replace("__ATLAS_DATA__", blob, 1)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    kinds = {}
    for i in items:
        kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
    print(f"Rendered {a.out}: {len(items)} items {kinds}, {len(data['groups'])} groups, {len(warnings)} warnings")

if __name__ == "__main__":
    main()
