---
name: skill-atlas
description: Builds a dashboard of every skill, plugin and MCP connector the user has in the Claude app and Claude Code, grouped by domain, with when to use each, where each came from, overlaps, duplicates and broken connectors. Use when the user asks what skills, plugins, MCP servers or connectors they have, which one to use for something, which overlap, where a skill came from, or says "Refresh my Skill Atlas". In Claude Code, "/skill-atlas collect" scans the local setup into claude-code-inventory.json.
---

# Skill Atlas

Two modes:

- **Collect**: the user said "collect", or you are in Claude Code and the user wants their Claude Code setup scanned. See "Collect mode".
- **Build**: everything else, including "Refresh my Skill Atlas". See "Build mode".

Files in this skill's folder (the folder this SKILL.md is in):

- `scripts/collect_claude_code.py`: read-only scanner for Claude Code
- `scripts/render.py`: validates the data and fills the dashboard template
- `assets/template.html`: the dashboard. Never edit it during a build; every user gets the same page.
- `assets/categories.json`: the fixed list of 14 domains
- `reference/schema.md`: the data format. Read it before writing data.

## Collect mode (Claude Code)

1. Run the collector with Python 3 (`python3`; on Windows `python` or `py`):

   ```
   python3 <skill folder>/scripts/collect_claude_code.py
   ```

   Run it from the project folder the user is working in; the script includes the current folder's `.claude/` by default. If the user named a folder holding several projects, add `--projects-root <folder>`.

2. Show the summary line it prints and where it wrote the file (default `~/claude-code-inventory.json`).
3. Next step, in one sentence: attach that file in a Claude app chat and say "Refresh my Skill Atlas". If you are able to publish artifacts here, offer to build the dashboard right away instead (Build mode, with only the Claude Code half).

If Python isn't available, don't install it. Collect the same data yourself, read-only, in the shape the script writes (see its `out` object): frontmatter `name` and `description` of every `SKILL.md`, command and agent file in `~/.claude/{skills,commands,agents}`, `~/.agents/skills` and the project's `.claude/`; plugins from `~/.claude/plugins/installed_plugins.json` and each install path's `.claude-plugin/plugin.json`; MCP servers from `mcpServers` in `~/.claude.json` (top level and under `projects`) and `./.mcp.json`, keeping only the name, transport, command basename or URL host.

Never record environment variables, headers, arguments, tokens, API keys, passwords or full URLs, even if asked.

## Build mode

Work through these steps. Keep narration to a minimum; the user wants the page.

### 1. Find the previous dashboard

If the Artifact tool is available, list the user's artifacts and look for one titled "Skill Atlas". If found, read it and take the JSON inside `<script id="atlas-data" type="application/json">`. You will:
- publish to the same URL, so the user keeps one link;
- reuse its summaries, examples, categories and origins for items whose `id` and `description` are unchanged (this saves most of the work on a refresh);
- compute `changes` (added and removed ids) against it.

### 2. Collect the Claude app half

Use whichever of these tools the session offers (they may need loading through tool search first):
- **Skills**: the tool that lists the user's enabled skills. Plugin skills appear as `plugin:skill`.
- **Plugins**: the tool that lists enabled plugins. Plugin names can be opaque ids; if the plugins' `plugin.json` files are readable on disk, take the display name from there, otherwise describe the plugin from its description.
- **Connectors**: the tool that lists connectors with their connection state. Map `connected` → `connected`, `needs_reconnect` → `needs_reconnect`, `not_connected` → `not_connected`.
- **Built-in skills**: skills in your own available-skills list that the skills tool did not return (docx, pdf, pptx, xlsx and similar). Mark them `source: "builtin"`.
- Local desktop MCP servers, if the session can report them, are connectors with `source: "desktop"`.

If no listing tool exists, use the skills you can see in your own context and the connector tools you have, and set `environment` to say the list may be incomplete.

### 3. Add the Claude Code half

If the user attached `claude-code-inventory.json` (or it is in the conversation's files), merge it. If you are running in Claude Code, run the collector first and use its output. Rules:
- The same skill in `~/.claude/skills` and `~/.agents/skills` (same name and description) is one item with a `note` that it is also in `~/.agents/skills`.
- Skills only in `~/.agents/skills`: `source: "cc-shared"`, info flag "May not load in Claude Code". Don't claim they work in Claude Code.
- MCP servers have `status: "unchecked"` and an info flag "Connection not checked". The scan can't see connection state.
- `claudeCode.counts` counts skills, commands, agents, plugins and connectors separately.

### 4. Enrich every item

Read `reference/schema.md` and `assets/categories.json`. For each item, unless reused from step 1:
- `category`: exactly one id from the list. Pick by what the user gets out of it, not by who made it.
- `summary`: one plain sentence, at most 120 characters, written for the user ("Drafts overdue-invoice reminders matched to each customer."). No "This skill...". No marketing language.
- `examples`: two short things a person would actually say that should trigger it. Skip for subagents and plugins.
- `origin`: where it came from, with honest confidence. Use the collector's `symlinkTo`, `gitRemote`, `installedFrom` and `author` fields when present; they make an origin `confirmed`. Plugin items: author and marketplace (`confirmed`). Uploaded Claude app skills: "Uploaded by you". Standalone files with no evidence: "Unknown", and say why.
- `flags`, `groups`, `runs`/`runBy`, `alsoIn`: as described in the schema.

Then look across items:
- **Duplicates** inside one world: same name and same or near-identical description, or a whole plugin that repeats standalone skills. Say in the note which copy to keep and why, considering how the user works (for example, standalone copies in `~/.agents` also serve other coding agents).
- **Overlaps**: skills that answer the same requests. Write a note that tells the user when to use which. Only group things a person could genuinely confuse; don't group a whole plugin because its skills share a topic.
- **Region flags**: only when a description ties the skill to a country's rules or to specific tools (US federal tax, 1099 forms, Gusto payroll). If you know the user's country, flag only what doesn't fit it. Never flag a skill for being generic.
- **Chains**: when a description says it runs other skills, fill `runs`, and `runBy` on the others.

To keep cost down on large inventories, enrich in batches by plugin or folder, and write the JSON with a script rather than by hand.

### 5. Render and publish

```
python3 <skill folder>/scripts/render.py atlas-data.json --out skill-atlas.html
```

Fix any `error:` lines and run again. Warnings are fine to leave.

- **Artifact tool available**: publish `skill-atlas.html`. Pass the previous dashboard's URL as `url` when there is one. Description: "Every skill, plugin and connector in your Claude setup, grouped by domain."
- **No Artifact tool** (Claude Code in a terminal): write the file to the user's home folder and open it (`open` on macOS, `start` on Windows, `xdg-open` on Linux).

### 6. Reply

Two or three sentences: what the page covers, the most useful finding (for example a duplicate plugin or broken connectors), and what changed since last time if this was a refresh. Don't list the items; the page does that.

## Rules

- Read-only. Never disable, uninstall or reconnect anything yourself; the dashboard only suggests.
- Never put secrets, tokens, email addresses or file contents beyond names and descriptions into the data.
- Never present an inferred origin as confirmed.
- The dashboard's look is fixed by `assets/template.html`. Don't restyle it per user.
