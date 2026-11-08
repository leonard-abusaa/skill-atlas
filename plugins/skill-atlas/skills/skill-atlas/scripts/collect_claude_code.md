# Claude Code collector

Read-only scanner for Claude Code. No network calls. Writes ~/claude-code-inventory.json.

The skill extracts the code block below to `collect_claude_code.py` before running it. Source: `src/collect_claude_code.py` in the repository.

<!-- file: collect_claude_code.py -->
````python
"""Skill Atlas collector for Claude Code.

Read-only. Makes no network calls. Collects names and descriptions of the
skills, slash commands, agents, plugins and MCP servers Claude Code can use,
and writes them to claude-code-inventory.json.

What it never collects: environment variables, headers, API keys, tokens,
command arguments, URLs with paths or query strings, or file contents other
than the frontmatter of SKILL.md / command / agent files.

Usage:
  python3 collect_claude_code.py [--project DIR] [--projects-root DIR] [--out FILE]
"""
import argparse, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HOME = Path.home()
CLAUDE = HOME / ".claude"
READ_LOG = []

def tilde(p):
    p = str(p)
    h = str(HOME)
    return "~" + p[len(h):] if p.startswith(h) else p

def read_text(path, limit=200_000):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return None

def frontmatter(path):
    """Returns the YAML frontmatter as a flat dict (only simple keys)."""
    txt = read_text(path, 20_000)
    if txt is None:
        return None
    READ_LOG.append(tilde(path))
    m = re.match(r"^﻿?---\s*\n(.*?)\n---", txt, re.S)
    fm, cur = {}, None
    if m:
        for line in m.group(1).splitlines():
            km = re.match(r"^([A-Za-z_][\w-]*):\s?(.*)$", line)
            if km:
                cur = km.group(1)
                fm[cur] = km.group(2).strip()
            elif cur and line[:1] in (" ", "\t"):
                fm[cur] = (fm[cur] + " " + line.strip()).strip()
        for k, v in list(fm.items()):
            v = v.strip()
            if v in (">", "|", ">-", "|-", ">+", "|+"):
                v = ""
            v = re.sub(r"^[>|][-+]?\s+", "", v)
            fm[k] = v.strip().strip('"').strip("'")
    if not fm.get("description"):
        # Commands often have no frontmatter: use the first prose line.
        body = txt[m.end():] if m else txt
        for line in body.splitlines():
            s = line.strip()
            if s and not s.startswith(("#", "<!--", "```")):
                fm["description"] = s[:300]
                break
    return fm

def load_json(path):
    txt = read_text(path, 50_000_000)
    if txt is None:
        return None
    try:
        data = json.loads(txt)
        READ_LOG.append(tilde(path))
        return data
    except ValueError:
        return None

def safe_server(name, cfg, scope, where):
    """Keeps only what identifies an MCP server. Drops env, headers, args, tokens."""
    cfg = cfg if isinstance(cfg, dict) else {}
    t = cfg.get("type") or ("stdio" if "command" in cfg else "http" if "url" in cfg else "unknown")
    out = {"name": name, "transport": t, "scope": scope, "where": where}
    if "command" in cfg and isinstance(cfg["command"], str):
        out["command"] = os.path.basename(cfg["command"].split()[0]) if cfg["command"].strip() else ""
    if "url" in cfg and isinstance(cfg["url"], str):
        try:
            out["host"] = urlparse(cfg["url"]).hostname or ""
        except ValueError:
            out["host"] = ""
    return out

def provenance(p):
    """Facts that show where a standalone file came from. Never reads file contents."""
    p = Path(p)
    out = {}
    try:
        st = p.lstat()
        out["installedAt"] = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds")
        if p.is_symlink():
            out["symlinkTo"] = tilde(os.path.realpath(p))
    except OSError:
        pass
    # A git checkout records its remote; keep only host/owner/repo, never credentials
    real = Path(os.path.realpath(p))
    for d in [real] + list(real.parents)[:4]:
        cfg = d / ".git" / "config"
        if cfg.is_file():
            txt = read_text(cfg, 20_000) or ""
            m = re.search(r'url\s*=\s*(\S+)', txt)
            if m:
                u = re.sub(r"^[a-z+]+://([^@/]+@)?", "", m.group(1)).replace("git@", "").replace(":", "/", 1) if "://" not in m.group(1) else re.sub(r"^[a-z+]+://([^@/]+@)?", "", m.group(1))
                out["gitRemote"] = u.removesuffix(".git")
            break
        if d in (HOME, CLAUDE):
            break
    return out

def lock_sources():
    """Reads skill installer lock files, if any, mapping skill name -> source repo."""
    found = {}
    for lf in [HOME / ".agents" / ".skill-lock.json", HOME / ".agents" / "skills-lock.json",
               CLAUDE / "skills-lock.json", HOME / ".skills-lock.json"]:
        data = load_json(lf)
        if not isinstance(data, dict):
            continue
        entries = data.get("skills", data)
        if isinstance(entries, dict):
            for name, v in entries.items():
                if isinstance(v, dict):
                    src = v.get("source") or v.get("remote") or v.get("repo") or v.get("sourceUrl")
                    if isinstance(src, str):
                        found[name] = re.sub(r"^https?://", "", src)[:200]
    return found

def scan_skills_dir(d, source, plugin=None):
    items = []
    d = Path(d)
    if not d.is_dir():
        return items
    for sm in sorted(d.glob("*/SKILL.md")):
        fm = frontmatter(sm) or {}
        name = fm.get("name") or sm.parent.name
        it = {"name": name, "invoke": f"{plugin}:{name}" if plugin else name,
              "description": fm.get("description", ""), "source": source,
              "plugin": plugin, "path": tilde(sm.parent)}
        if not plugin:
            it.update(provenance(sm.parent))
            for k in ("author", "version", "homepage", "repository", "license"):
                if fm.get(k): it[k] = fm[k][:200]
        items.append(it)
    return items

def scan_md_dir(d, source, plugin=None, recursive=False):
    items = []
    d = Path(d)
    if not d.is_dir():
        return items
    files = sorted(d.rglob("*.md") if recursive else d.glob("*.md"))
    for f in files:
        fm = frontmatter(f) or {}
        rel = f.relative_to(d).with_suffix("")
        name = fm.get("name") or ":".join(rel.parts)
        it = {"name": name, "invoke": f"{plugin}:{name}" if plugin else name,
              "description": fm.get("description", ""), "source": source,
              "plugin": plugin, "path": tilde(f)}
        if not plugin:
            it.update(provenance(f))
        items.append(it)
    return items

def plugin_mcp(install, plugin_json):
    servers = {}
    if isinstance(plugin_json.get("mcpServers"), dict):
        servers.update(plugin_json["mcpServers"])
    mj = load_json(install / ".mcp.json")
    if isinstance(mj, dict):
        servers.update(mj.get("mcpServers", mj) if isinstance(mj.get("mcpServers", mj), dict) else {})
    return servers

def collect_plugins():
    plugins, skills, commands, agents, mcp = [], [], [], [], []
    settings = load_json(CLAUDE / "settings.json") or {}
    enabled = settings.get("enabledPlugins", {}) if isinstance(settings.get("enabledPlugins"), dict) else {}
    installed = load_json(CLAUDE / "plugins" / "installed_plugins.json") or {}
    entries = []
    pl = installed.get("plugins", installed) if isinstance(installed, dict) else {}
    if isinstance(pl, dict):
        for key, val in pl.items():
            for e in (val if isinstance(val, list) else [val]):
                if isinstance(e, dict) and e.get("installPath"):
                    entries.append((key, e))
    if not entries:  # Fallback: installed plugin copies live in the plugin cache
        for pj in (CLAUDE / "plugins" / "cache").glob("**/.claude-plugin/plugin.json"):
            entries.append((pj.parent.parent.name, {"installPath": str(pj.parent.parent)}))
    seen = set()
    for key, e in entries:
        install = Path(os.path.expanduser(e["installPath"]))
        if not install.is_dir() or str(install) in seen:
            continue
        seen.add(str(install))
        pj = load_json(install / ".claude-plugin" / "plugin.json") or {}
        slug = pj.get("name") or key.split("@")[0]
        marketplace = key.split("@")[1] if "@" in key else ""
        is_enabled = enabled.get(key, True) if enabled else True
        p_sk = scan_skills_dir(install / "skills", "claude-code-plugin", slug)
        p_cm = scan_md_dir(install / "commands", "claude-code-plugin", slug, recursive=True)
        p_ag = scan_md_dir(install / "agents", "claude-code-plugin", slug)
        p_mcp = [safe_server(n, c, "plugin", slug) for n, c in plugin_mcp(install, pj).items()]
        for x in p_sk + p_cm + p_ag:
            x["enabled"] = is_enabled
        skills += p_sk; commands += p_cm; agents += p_ag; mcp += p_mcp
        plugins.append({"slug": slug, "name": pj.get("displayName") or slug, "version": pj.get("version", e.get("version", "")),
                        "author": (pj.get("author") or {}).get("name", "") if isinstance(pj.get("author"), dict) else str(pj.get("author") or ""),
                        "description": pj.get("description", ""), "marketplace": marketplace,
                        "scope": e.get("scope", "user"), "enabled": is_enabled,
                        "skills": [s["name"] for s in p_sk], "commands": [c["name"] for c in p_cm],
                        "agents": [a["name"] for a in p_ag], "mcpServers": [m["name"] for m in p_mcp]})
    return plugins, skills, commands, agents, mcp

def collect_project(proj):
    proj = Path(proj)
    label = proj.name
    sk = scan_skills_dir(proj / ".claude" / "skills", "claude-code-project")
    cm = scan_md_dir(proj / ".claude" / "commands", "claude-code-project", recursive=True)
    ag = scan_md_dir(proj / ".claude" / "agents", "claude-code-project")
    for x in sk + cm + ag:
        x["project"] = label
    mcp = []
    mj = load_json(proj / ".mcp.json")
    if isinstance(mj, dict) and isinstance(mj.get("mcpServers"), dict):
        mcp = [safe_server(n, c, "project", label) for n, c in mj["mcpServers"].items()]
    return sk, cm, ag, mcp

def main():
    ap = argparse.ArgumentParser(description="Collect a read-only inventory of your Claude Code setup.")
    ap.add_argument("--project", action="append", default=[], help="Project folder to include (repeatable). Defaults to the current folder.")
    ap.add_argument("--projects-root", help="Also include every project under this folder that has a .claude/ or .mcp.json (two levels deep).")
    ap.add_argument("--out", default=str(HOME / "claude-code-inventory.json"))
    a = ap.parse_args()

    if not CLAUDE.is_dir():
        print(f"No Claude Code folder found at {tilde(CLAUDE)}. Is Claude Code installed for this user?", file=sys.stderr)
        sys.exit(1)

    skills = scan_skills_dir(CLAUDE / "skills", "claude-code-user")
    skills += scan_skills_dir(HOME / ".agents" / "skills", "agents-shared")
    commands = scan_md_dir(CLAUDE / "commands", "claude-code-user", recursive=True)
    agents = scan_md_dir(CLAUDE / "agents", "claude-code-user")
    mcp = []

    cj = load_json(HOME / ".claude.json") or {}
    if isinstance(cj.get("mcpServers"), dict):
        mcp += [safe_server(n, c, "user", "~/.claude.json") for n, c in cj["mcpServers"].items()]
    if isinstance(cj.get("projects"), dict):
        for ppath, pcfg in cj["projects"].items():
            if isinstance(pcfg, dict) and isinstance(pcfg.get("mcpServers"), dict) and pcfg["mcpServers"]:
                mcp += [safe_server(n, c, "local", Path(ppath).name) for n, c in pcfg["mcpServers"].items()]

    p_plugins, p_sk, p_cm, p_ag, p_mcp = collect_plugins()
    skills += p_sk; commands += p_cm; agents += p_ag; mcp += p_mcp

    projects = [Path(p).expanduser().resolve() for p in a.project] or [Path.cwd()]
    if a.projects_root:
        root = Path(a.projects_root).expanduser().resolve()
        for depth in ("*", "*/*"):
            for d in root.glob(depth):
                if d.is_dir() and ((d / ".claude").is_dir() or (d / ".mcp.json").is_file()):
                    projects.append(d)
    seen = set()
    project_names = []
    for proj in projects:
        if str(proj) in seen or proj == HOME:
            continue
        seen.add(str(proj))
        sk, cm, ag, pm = collect_project(proj)
        if sk or cm or ag or pm:
            project_names.append(proj.name)
        skills += sk; commands += cm; agents += ag; mcp += pm

    locks = lock_sources()
    for x in skills:
        if x["name"] in locks and not x.get("plugin"):
            x["installedFrom"] = locks[x["name"]]
    out = {
        "schema": "skill-atlas/claude-code-inventory@2",
        "scannedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": sys.platform,
        "skills": skills, "commands": commands, "agents": agents,
        "plugins": p_plugins, "mcpServers": mcp, "projects": project_names,
        "filesRead": len(READ_LOG),
    }
    out_path = Path(a.out).expanduser()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f"Skill Atlas: Claude Code inventory written to {tilde(out_path)}")
    print(f"  {len(skills)} skills, {len(commands)} commands, {len(agents)} agents, "
          f"{len(p_plugins)} plugins, {len(mcp)} MCP servers"
          + (f", projects: {', '.join(project_names)}" if project_names else ""))
    print(f"  Read {len(READ_LOG)} files (frontmatter and config only). No secrets or env values were kept.")

if __name__ == "__main__":
    main()
````
