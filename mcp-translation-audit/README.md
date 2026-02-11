# Power BI Translation Audit MCP Server

MCP server that provides translation audit tools for Power BI .pbip reports.

Scans report JSON files to find remaining English content after translation. Used by Claude Code agents during report localization workflow.

## What It Does

Provides three tools to verify translation completeness:

1. **scan_english_remaining** - Find all suspected English strings (titles, displayName, textbox content)
2. **scan_missing_displaynames** - Find projections with English nativeQueryRef but no displayName override
3. **validate_translation_coverage** - Run both scans, produce summary with PASS/FAIL verdict

## Requirements

- Python 3.10+
- No external dependencies (standard library only)

## Installation

### Add to Claude Code's MCP configuration

Edit your `.mcp.json` file (in project root or `~/.mcp.json`):

```json
{
  "mcpServers": {
    "powerbi-translation-audit": {
      "command": "python",
      "args": [
        "E:/powerbi_mcp_vscode/mcp-translation-audit/server.py"
      ]
    }
  }
}
```

**Note:** Use forward slashes in paths, even on Windows.

### Restart Claude Code

After updating `.mcp.json`, restart Claude Code for changes to take effect.

## Usage

In Claude Code, the tools are available as `mcp__powerbi-translation-audit__<tool_name>`.

### Example: Full validation

```
Use the validate_translation_coverage tool to check the report at:
E:/path/to/report.Report/definition/pages
```

The tool will:
- Count total projections
- Count how many have displayName overrides
- Find suspected English in titles, displayName values, textbox content
- Report PASS if zero English found, FAIL otherwise

### Example: Detailed scan

```
Use scan_english_remaining to find all English strings in:
E:/path/to/report.Report/definition/pages
```

Returns list of files with suspected English, organized by content type.

### Example: Missing displayName check

```
Use scan_missing_displaynames to find projections without displayName in:
E:/path/to/report.Report/definition/pages
```

Returns list of nativeQueryRef values that need displayName overrides added.

## How English Detection Works

Uses simple heuristic:

**A string is "suspected English" if:**
- Contains NO Swedish characters (å, ä, ö, Å, Ä, Ö)
- AND matches common English patterns:
  - Contains words like "year", "month", "quarter", "amount", "invoice", "budget", "forecast", etc.
  - OR is a multi-word phrase with English words

**Skip known neutrals:**
- Abbreviations: FC, BU, ACT, PY, YoY, VTC%, etc.
- Internal measures: Color PnL Background, VAR IsExpandable, etc.
- Formatting values: color codes, font names, true/false

## Output Format

All tools return plain text reports. Example:

```
TRANSLATION COVERAGE VALIDATION
==================================================

Total projections: 423
Projections with displayName: 401 (94.8%)
Projections without displayName: 22

SUSPECTED ENGLISH CONTENT:
  Title text: 3
  DisplayName values: 5
  Missing displayName (English nativeQueryRef): 18
  Textbox content: 0

Total suspected English strings: 26

VERDICT: FAIL

Translation incomplete. Run scan_english_remaining for details.
```

## Typical Workflow

1. **After semantic model translation** (MCP tools for captions, data values, DAX)
2. **After report JSON translation** (pbip_translate_display_names.py script)
3. **Run validation:**
   - `validate_translation_coverage` → get summary verdict
   - If FAIL, run `scan_english_remaining` → see specific issues
   - Fix issues (add displayName, translate titles, etc.)
   - Re-run validation until PASS

## Integration with Translation Playbook

This MCP server implements **Phase 10 verification** from the Translation Playbook:

- **Phase 10.7** - Final validation step
- Used after bulk displayName injection via `pbip_translate_display_names.py`
- Catches edge cases missed by scripted updates
- Verifies completeness before final review in Power BI Desktop

## Limitations

- **English detection is heuristic** - not perfect. Some English might pass (proper nouns, technical terms), some Swedish might flag (lacks å/ä/ö and uses loanwords).
- **Does NOT check:**
  - Page names (in page.json)
  - Bookmark names
  - Button labels
  - Tooltip page titles
  - Conditional formatting selectors (those should NOT be translated anyway)
- **Only scans visual.json files** - assumes other report metadata already handled

## File Structure

```
mcp-translation-audit/
├── server.py       # MCP server implementation
└── README.md       # This file
```

## Protocol Details

Implements MCP protocol over stdio (JSON-RPC 2.0).

Handles:
- `initialize` - server info and capabilities
- `initialized` - notification (no response)
- `tools/list` - return tool definitions
- `tools/call` - execute tool and return results

Each message uses HTTP-style headers:
```
Content-Length: <byte_length>\r\n
\r\n
<JSON-RPC message>
```

## Troubleshooting

**Tools not showing up in Claude Code:**
- Check `.mcp.json` path is absolute
- Use forward slashes even on Windows
- Restart Claude Code after config changes

**"File not found" errors:**
- Verify `pages_dir` path is absolute
- Must point to `<report>.Report/definition/pages` folder
- Check path exists and contains visual.json files

**False positives in English detection:**
- Add terms to skip list (edit NEUTRAL_ABBR in server.py)
- Or use manual review - tool is advisory, not enforcing

## License

MIT
