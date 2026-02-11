# Power BI Report Translator — Agent Instructions

## When user says "run setup" or "set up MCP"

Read and follow `POWERBI_MCP_SETUP.md` step by step:
1. Find the Power BI MCP extension path on this machine
2. Update `.mcp.json` with the real path (replace `<USERNAME>` and `<VERSION>` placeholders)
3. Verify `.claude/settings.local.json` has `enableAllProjectMcpServers: true`
4. Tell user to restart Claude Code

## When user says "translate" or "translate using the playbook"

Read and follow `TRANSLATION_PLAYBOOK.md` from Phase 0 through Phase 10:
- **Phases 0-9**: Use MCP tools (ToolSearch for `powerbi-modeling` tools) to translate the semantic model
- **Phase 10**: Edit report JSON files on disk (visual titles, nativeQueryRef displayName injection, text boxes)
- For Phase 10 step 10.3, use `pbip_translate_display_names.py` with `translation_map_sv-SE.json` as the base dictionary
- After all phases: run the validation checks in step 10.7 to confirm zero English remains

## Key files

| File | When to use |
|------|-------------|
| `TRANSLATION_PLAYBOOK.md` | The full translation process — read this first |
| `POWERBI_MCP_SETUP.md` | MCP server setup (first time only) |
| `pbip_translate_display_names.py` | Phase 10.3 — bulk nativeQueryRef → displayName |
| `translation_map_sv-SE.json` | Swedish translation dictionary — start from this, add project-specific terms |
| `.mcp.json` | MCP server config template — needs real paths filled in |

## When the existing tools don't cover everything

The `pbip_translate_display_names.py` script handles nativeQueryRef → displayName injection. But each project may have content the script doesn't cover (text boxes, buttons, visual titles, bookmark labels, etc.).

When you find translatable content that requires repetitive manual edits across many files:
1. **Write a project-specific script** in the project's own folder (not this workspace root)
2. Follow the same pattern: scan → build map → dry-run → execute
3. Name it descriptively: `translate_titles.py`, `translate_textboxes.py`, etc.
4. Always include `--dry-run` mode
5. After the project is done, consider whether the script should be generalized and added to this workspace for future reuse

The goal: never do more than 5 manual edits of the same type. If there are more, script it.

## Rules

- Always scan ALL pages, not just a few. Targeted scans miss 80%+ of English.
- Never change `nativeQueryRef` values. Add `displayName` next to them instead.
- Never translate conditional formatting selectors (`scopeId.Comparison.Right.Literal.Value`).
- After editing .pbip JSON, user must close and reopen Power BI Desktop to see changes.
- Run the final audit (Phase 10.7) before declaring done. No "trust me it's translated" — verify.
