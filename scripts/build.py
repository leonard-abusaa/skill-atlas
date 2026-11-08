#!/usr/bin/env python3
"""Builds the plugin's text-only bundle from src/.

Anthropic's directory accepts only Markdown, text, JSON, YAML and images from
unverified publishers, so the HTML template and Python scripts ship inside
Markdown files. The skill extracts them at run time (see SKILL.md, step 0).
Edit the files in src/, then run: python3 scripts/build.py
"""
import os, shutil, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "plugins", "skill-atlas", "skills", "skill-atlas")
FENCE = "````"
BUNDLE = [
    ("template.html", "assets/template.md", "html", "Skill Atlas dashboard template",
     "The page every user gets. Claude never edits it; render.py injects the data where it says __ATLAS_DATA__."),
    ("collect_claude_code.py", "scripts/collect_claude_code.md", "python", "Claude Code collector",
     "Read-only scanner for Claude Code. No network calls. Writes ~/claude-code-inventory.json."),
    ("render.py", "scripts/render.md", "python", "Renderer",
     "Validates atlas-data.json and fills the template. No network calls."),
]
for src, dest, lang, title, blurb in BUNDLE:
    code = open(os.path.join(ROOT, "src", src), encoding="utf-8").read()
    if code.startswith("#!"):
        code = code.split("\n", 1)[1]
    assert FENCE not in code, f"{src} contains {FENCE}"
    out = (f"# {title}\n\n{blurb}\n\nThe skill extracts the code block below to `{src}` before running it. "
           f"Source: `src/{src}` in the repository.\n\n<!-- file: {src} -->\n{FENCE}{lang}\n{code.rstrip()}\n{FENCE}\n")
    path = os.path.join(SKILL, dest)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(out)
# Allowed-type check over the whole plugin folder
ALLOWED = (".md", ".json", ".yaml", ".yml", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico")
plugin = os.path.join(ROOT, "plugins", "skill-atlas")
for d, _, files in os.walk(plugin):
    for f in files:
        p = os.path.join(d, f)
        ok = f.endswith(ALLOWED) or f in ("LICENSE", "README", ".gitignore")
        if not ok:
            raise SystemExit(f"not allowed in the plugin folder: {os.path.relpath(p, ROOT)}")
        if not f.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico")):
            b = open(p, "rb").read()
            if b.startswith(b"#!") or b"\x00" in b:
                raise SystemExit(f"starts with #! or holds a NUL byte: {os.path.relpath(p, ROOT)}")
            b.decode("utf-8")
# Upload zip for the Claude app
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
zp = os.path.join(ROOT, "dist", "skill-atlas.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    base = os.path.dirname(SKILL)
    for d, _, files in os.walk(SKILL):
        for f in sorted(files):
            p = os.path.join(d, f)
            z.write(p, os.path.relpath(p, base))
print("built plugin bundle and", os.path.relpath(zp, ROOT))
