# atlas-data.json

The file `scripts/render.py` turns into the dashboard. Write it as UTF-8 JSON.
`render.py` fills `categories` from `assets/categories.json` and adds defaults, so you don't write those.

## Top level

| Field | Type | Notes |
|---|---|---|
| `generatedAt` | ISO 8601 with offset | When this build ran, in the user's time zone. |
| `environment` | string | Plain words for what was scanned, e.g. "Claude desktop app and Claude Code". |
| `items` | array | Every skill, command, subagent, plugin and connector. See Items. |
| `groups` | array | Duplicate, overlap and "often confused" groups. See Groups. |
| `claudeCode` | object or null | Present only when a Claude Code inventory was merged. |
| `changes` | object or null | What changed since the previous build. null on the first build. |

`claudeCode`: `{ "count": int, "scannedAt": iso, "platform": "darwin|win32|linux", "projects": [names], "counts": {"skill": n, "command": n, "agent": n, "plugin": n, "connector": n} }`

`changes`: `{ "since": iso, "added": [ids], "removed": [ids], "note": "short reason, e.g. Claude Code scan added" }`

## Items

Common fields:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable across builds so changes can be tracked. Use the patterns below. |
| `kind` | yes | `skill`, `plugin` or `connector`. Commands and subagents are `skill` with a `subtype`. |
| `subtype` | no | `command` or `agent`. Omit for ordinary skills. |
| `world` | yes | `claude-app` (claude.ai, desktop and mobile apps) or `claude-code`. |
| `name` | yes | Name as the user sees it. |
| `invoke` | skills | What the user types after `/`. Plugin skills: `plugin:skill`. null for subagents and connectors. |
| `source` | yes | See Sources. |
| `plugin` | no | Plugin slug the item belongs to, or null. |
| `category` | yes | One id from `assets/categories.json`. |
| `summary` | yes | One plain sentence, at most 120 characters, saying what it does for the user. |
| `examples` | no | Up to 2 things the user might say that should trigger it. Real phrasings, not commands. |
| `description` | no | The original description, verbatim. |
| `flags` | no | Badges. See Flags. |
| `origin` | yes | Where it came from. See Origin. |
| `runs` / `runBy` | no | Ids of skills this one runs, or that run it (chains). |
| `alsoIn` | no | Id of the same skill in the other world. |
| `note` | no | One sentence the drawer shows in a highlighted box. |
| `path` | Claude Code | `~/...` path of the file or folder. |

Plugins add `version`, `author`, `marketplace`, `skills` (ids of everything the plugin installs).
Connectors add `status` (`connected`, `needs_reconnect`, `not_connected`, `unchecked`) and `scope` (one line, e.g. "claude.ai connector" or "Claude Code · from plugin firebase · http mcp.firebase.com").

### Id patterns

- Claude app skill: its name; built-in skill: `builtin:<name>`; plugin skill: `<plugin>:<skill>`; plugin: `plugin:<slug>`; connector: `conn:<slug-of-name>`
- Claude Code: skill `cc:<plugin or cc-user/cc-shared/cc-project>:<name>`; command `cc:command:<plugin or user>:<name>`; agent `cc:agent:<plugin or user>:<name>`; plugin `cc-plugin:<slug>`; MCP server `cc-mcp:<scope>:<name>`

### Sources

| `source` | Meaning |
|---|---|
| `builtin` | Ships with Claude in every account |
| `account` | Skill enabled or uploaded in the user's Claude app account |
| `plugin` | Part of a Claude app plugin (set `plugin` too) |
| `desktop` | Local MCP server configured in the desktop app |
| `cc-user` | Standalone in `~/.claude/skills`, `~/.claude/agents` or `~/.claude/commands` |
| `cc-shared` | Only in `~/.agents/skills` |
| `cc-plugin` | Part of a Claude Code plugin (set `plugin` too) |
| `cc-plugin-root` | A Claude Code plugin itself |
| `cc-project` | In a project's `.claude/` folder |
| `cc-mcp` | A Claude Code MCP server (set `plugin` if a plugin provides it) |

Claude app connectors use `source: "account"` and `kind: "connector"`.

### Flags

`{ "type": "...", "label": "...", "group": <index into groups, for duplicate/overlap/pair> }`

| type | Use for | Label |
|---|---|---|
| `duplicate` | The item to switch off in a duplicate group | "Duplicate" |
| `overlap` | Member of an overlap group | "Overlaps" |
| `pair` | Member of an "often confused" pair | "Often confused" |
| `region` | Built for a country or tool the user likely doesn't use | The reason, e.g. "US federal tax only" |
| `health` | Connector not working | "Needs reconnect" or "Not connected" |
| `info` | Neutral facts | e.g. "Also in Claude Code", "Connection not checked", "May not load in Claude Code", "Described from its tools" |

### Origin

`{ "label": "...", "detail": "...", "confidence": "confirmed|matched|inferred|unknown" }`

- `confirmed`: recorded by the system: built-in, plugin author and marketplace, account manifest, symlink or git remote from the collector, installer lock file.
- `matched`: name and description match a known public pack or another installed copy.
- `inferred`: reasoned from evidence (shared files, install date, naming). Say what the evidence is in `detail`.
- `unknown`: no evidence. `detail` says why ("Files copied in by hand don't record where they came from.").

Never present an inference as confirmed.

## Groups

`{ "kind": "duplicate|overlap|pair", "world": "claude-app|claude-code", "title": "...", "members": [ids], "keep": id or null, "keepLabel": "text when the keeper isn't one item", "note": "one or two sentences: when to pick which, or which to remove and why" }`

- Groups stay inside one world. The same skill in the Claude app and in Claude Code is not a duplicate; mark it with `alsoIn` and an info flag.
- `duplicate`: the same job installed twice. Every member except `keep` gets a duplicate flag. When a whole plugin duplicates standalone skills, flag the plugin and its copies, and list the plugin first; the "Consider disabling" page shows the plugin as one row.
- `overlap`: different skills that answer similar requests. The note says which to use when.
- `pair`: complementary skills people mix up (docs vs docx).
