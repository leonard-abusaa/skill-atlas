# Skill Atlas

Skill Atlas builds a private dashboard of everything Claude can use for you: every skill, slash command, subagent, plugin and MCP connector in the Claude app and in Claude Code, grouped into 14 domains such as Marketing, Engineering, Design and Finance.

For each item it shows a plain one-line summary, example phrases that trigger it, the command to call it directly, and where it came from: built into Claude, uploaded by you, part of a plugin (with author and marketplace), or a standalone file, each with a confidence label. It also flags skills installed twice, skills that overlap, skills built for a country or tool you may not use, and connectors that need reconnecting. The dashboard only suggests; it never disables, uninstalls or reconnects anything.

![Skill Atlas dashboard](docs/screenshot.png)

## Use

- In the Claude app, say **"Refresh my Skill Atlas"**. Claude lists your skills, plugins and connectors with its built-in listing tools, writes the dashboard data, and publishes it as a private artifact in your account. Running it again updates the same link and shows what changed.
- In Claude Code, run **`/skill-atlas:skill-atlas collect`** to scan your local setup into `~/claude-code-inventory.json`, then attach that file in a Claude app chat and say "Refresh my Skill Atlas" to see both in one dashboard.

## What it runs, reads and sends

- `collect_claude_code.py` (shipped inside `scripts/collect_claude_code.md`) runs only in Claude Code, when you ask for "collect". It is read-only and makes no network calls. It reads:
  - the `name` and `description` at the top of skill, command and agent files in `~/.claude`, `~/.agents/skills` and the current project's `.claude/` folder;
  - installed plugin manifests (`plugin.json`, `installed_plugins.json`, `settings.json` for which plugins are enabled);
  - the `mcpServers` entries in `~/.claude.json` and the project's `.mcp.json`. From each server it keeps only the name, transport type, and command name or URL host. Every other key in `~/.claude.json`, including account details, is ignored. Environment variables, headers, arguments, tokens, passwords and full URLs are never kept, and credentials are stripped from git remotes.

  It writes one JSON file, `~/claude-code-inventory.json`, which you choose whether to share.
- `render.py` (inside `scripts/render.md`) validates the dashboard data and fills the template from `assets/template.md`. No network calls.
- At the start of a conversation the skill extracts these code blocks, unchanged, into a temporary folder and runs them from there. The code is readable in the Markdown files.
- The dashboard is published as a private artifact in your own Claude account.
- When you open the dashboard, your browser loads the Poppins and Lora fonts from Google Fonts (`fonts.googleapis.com`). That is the only outside request, and it carries no data from your setup.
- The plugin has no code that sends data anywhere. The GitHub links in `plugin.json` are the project's homepage, not a destination for data.

## License

MIT. Not affiliated with Anthropic.
