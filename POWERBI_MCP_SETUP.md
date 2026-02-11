# Power BI MCP Server — Setup Instructions for Claude Code Agent

## Context

The user has installed the VS Code extension "Power BI Modeling MCP" by Analysis Services. The extension installs an MCP server executable but Claude Code doesn't know about it yet. You need to create config files to wire it up.

## Step 1: Find the Extension Path

The executable lives inside the user's VS Code extensions folder. Find it:

```bash
ls ~/.vscode/extensions/ | grep -i powerbi
```

This returns a folder like:
```
analysis-services.powerbi-modeling-mcp-0.1.9-win32-x64
```

The version number and platform suffix will vary. The full path to the server executable is:

```
<USERPROFILE>\.vscode\extensions\<that-folder>\server\powerbi-modeling-mcp.exe
```

Verify the `.exe` exists:
```bash
ls ~/.vscode/extensions/analysis-services.powerbi-modeling-mcp-*/server/powerbi-modeling-mcp.exe
```

## Step 2: Create `.mcp.json` in the Project Root

Create `.mcp.json` in the working directory. Use the **full Windows path** with double backslashes for the command value:

```json
{
  "mcpServers": {
    "powerbi-modeling": {
      "type": "stdio",
      "command": "C:\\Users\\<USERNAME>\\.vscode\\extensions\\analysis-services.powerbi-modeling-mcp-<VERSION>-win32-x64\\server\\powerbi-modeling-mcp.exe",
      "args": ["--start"]
    }
  }
}
```

Replace `<USERNAME>` and `<VERSION>` with the actual values found in Step 1.

## Step 3: Create `.claude/settings.local.json`

Create the `.claude` directory in the project root if it doesn't exist, then create `settings.local.json` inside it:

```json
{
  "enableAllProjectMcpServers": true
}
```

This tells Claude Code to start MCP servers defined in `.mcp.json`. Without this, the server config is ignored.

## Step 4: Tell the User to Restart Claude Code

After creating both files, tell the user:

> Run `/exit` to quit Claude Code, then relaunch it from this same directory. On restart, Claude Code will detect the new MCP server and prompt you to approve it. Say yes.

This restart is required. Claude Code reads `.mcp.json` at startup — it does not hot-reload MCP server configs. The user will see an approval prompt for the `powerbi-modeling` server on the first launch after setup.

## Summary of Files Created

```
project-root/
├── .mcp.json                      # Defines the MCP server (stdio, exe path, args)
└── .claude/
    └── settings.local.json        # Enables project MCP servers
```

That's it. After restart + approval, the Power BI tools are available via `ToolSearch`.
