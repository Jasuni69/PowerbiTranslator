# Power BI Report Translator

Translate Power BI reports from English to Swedish using Claude Code + MCP tools.

## Prerequisites

- **Power BI Desktop** (with your English report open)
- **VS Code** with the [Power BI Modeling MCP](https://marketplace.visualstudio.com/items?itemName=analysis-services.powerbi-modeling-mcp) extension installed
- **Claude Code** CLI installed and configured

## Quick Start

### 1. Open your English report

Open the `.pbix` file in Power BI Desktop.

### 2. Save as Power BI Project

In Power BI Desktop: **File → Save as → Power BI Project (.pbip)**

Save it into this workspace folder. This unpacks the report into editable files:

```
powerbi_mcp_vscode/
├── YourReport.pbip
├── YourReport.Report/
│   ├── report.json
│   └── definition/
│       └── pages/          ← visual titles, text boxes (Phase 10)
├── YourReport.SemanticModel/
│   └── ...                 ← model definition (Phases 0-9 via MCP)
```

### 3. Set up the MCP server (first time only)

The `.mcp.json` file in this workspace is a template with `<USERNAME>` and `<VERSION>` placeholders. Follow `POWERBI_MCP_SETUP.md` to fill in your actual paths. You only need to do this once per machine.

### 4. Keep Power BI Desktop open

The MCP tools connect to the running Power BI Desktop instance through its local port. Do NOT close Desktop during translation.

### 5. Launch Claude Code

Open a terminal in this workspace and run:

```
claude
```

Claude Code will auto-detect the MCP server config (`.mcp.json`) and connect to the Power BI modeling tools.

### 6. Start the translation

Tell Claude:

> Follow the TRANSLATION_PLAYBOOK.md to translate the open report to Swedish (sv-SE). Do all phases including Phase 10 report JSON editing.

Claude will:
- **Phases 0-9**: Translate the semantic model via MCP tools (captions, data values, DAX expressions, date tables)
- **Phase 10**: Edit the report JSON files directly (visual titles, text boxes, page labels)

### 7. Save and publish

After translation completes:
1. Save the project in Power BI Desktop (Ctrl+S)
2. Publish to Fabric / Power BI Service
3. Users with Swedish locale will see full Swedish translation

## What Gets Translated

| What | How | When visible |
|------|-----|-------------|
| Column/measure/table names | sv-SE captions (MCP) | When user locale is sv-SE |
| Data values (selectors, dates, labels) | Physical data change (MCP) | Always |
| DAX display text (titles, headlines) | Expression edit (MCP) | Always |
| Visual titles, text boxes, buttons | Report JSON edit (file system) | Always |
| Page names, bookmarks | Report JSON edit (file system) | Always |

## What WON'T be translated

- Source system identifiers (IDs, codes, technical names)
- Data in external sources that requires credentials to refresh (documented per run)
- Pre-existing broken measures referencing deleted tables

## File Reference

| File | Purpose |
|------|---------|
| `TRANSLATION_PLAYBOOK.md` | Detailed step-by-step translation checklist (for Claude) |
| `pbip_translate_display_names.py` | Reusable script: bulk nativeQueryRef → displayName translation |
| `translation_map_sv-SE.json` | Swedish translation dictionary (109 terms, financial reporting domain) |
| `mcp-translation-audit/server.py` | MCP server: translation completeness audit (PASS/FAIL verdict) |
| `POWERBI_MCP_SETUP.md` | MCP server setup instructions (one-time) |
| `.mcp.json` | MCP server connection config (template — fill in your paths) |
| `.claude/settings.local.json` | Claude Code project settings |

## Troubleshooting

**Claude can't find MCP tools**
→ Make sure Power BI Desktop is open with the report loaded. Restart Claude Code (`/exit` then relaunch).

**Captions not showing in Fabric**
→ User must have browser language set to Swedish (sv-SE). Check Power BI Service → Settings → Language.

**Some pages Swedish, others English**
→ Pages with dynamic titles (from measures) show Swedish. Pages with static visual titles need Phase 10 (report JSON editing). Tell Claude to run Phase 10 if it hasn't.

**"Credentials required" errors during table refresh**
→ Expected for tables loaded from external sources (Fabric SQL, etc.). Claude will rebuild small tables as static M expressions. Large tables are documented for manual refresh after publishing with credentials.
