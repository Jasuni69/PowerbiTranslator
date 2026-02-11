#!/usr/bin/env python3
"""
MCP server for Power BI translation audit.

Scans .pbip report JSON files (visual.json) to find remaining English content.
Provides three tools for Claude Code translation verification workflow.
"""

import json
import sys
import glob
import os
import re
from typing import List, Dict, Set, Any


# English detection word list - common Power BI terms
ENGLISH_KEYWORDS = {
    "year", "month", "quarter", "week", "date", "amount", "cost", "name",
    "group", "type", "number", "total", "invoice", "customer", "counter",
    "account", "voucher", "description", "payment", "comment", "display",
    "header", "result", "report", "comparison", "forecast", "budget",
    "actual", "trend", "revenue", "opening", "chosen", "history", "churn",
    "sheet", "legal", "entity", "company", "project", "article", "overdue",
    "property", "column", "full", "count", "ratio", "profit", "balance",
    "invoiced", "development", "overview", "financial", "ledger", "actuals",
    "accumulated", "selected", "comparison", "previous"
}

# Swedish characters
SWEDISH_CHARS = set("åäöÅÄÖ")

# Language-neutral abbreviations to skip
NEUTRAL_ABBR = {
    "FC", "BU", "ACT", "PY", "VTB%", "VTC", "VTC%", "Var%", "YoY",
    "VTF", "VTF %", "FC/BU", "DynVTC", "DynVTC%", "R12M", "YTD", "FYTD",
    "R3M", "L12M", "SK", "VAT", "N/A", "SEK", "pp"
}


def is_suspected_english(text: str) -> bool:
    """
    Heuristic to detect if a string is likely English (not Swedish).

    Returns True if:
    - No Swedish characters AND matches English keywords/patterns
    - Skip internal/formatting values
    """
    if not text or not isinstance(text, str):
        return False

    text_stripped = text.strip().strip("'\"")

    # Skip empty, very short, or numeric-only
    if len(text_stripped) < 2 or text_stripped.isdigit():
        return False

    # Skip neutral abbreviations
    if text_stripped in NEUTRAL_ABBR:
        return False

    # Skip color codes, alignment, booleans
    if text_stripped.lower() in {"true", "false", "center", "left", "right", "top", "bottom"}:
        return False
    if text_stripped.startswith("#") or text_stripped.startswith("rgb"):
        return False

    # Skip internal measure names
    if any(x in text_stripped for x in ["Color ", "VAR ", "FontColorCode", "BackgroundColorCode", "IsInScope", "EnableExpansion"]):
        return False

    # Has Swedish characters? Probably Swedish
    if any(c in SWEDISH_CHARS for c in text_stripped):
        return False

    # Check for English keywords (case-insensitive)
    text_lower = text_stripped.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    # Multi-word phrases with English words
    if len(words) >= 2:
        english_word_count = sum(1 for w in words if w in ENGLISH_KEYWORDS)
        if english_word_count >= 1:
            return True

    # Single word match
    if len(words) == 1 and words[0] in ENGLISH_KEYWORDS:
        return True

    return False


def scan_visual_json(file_path: str) -> Dict[str, List[str]]:
    """
    Scan a single visual.json file for English content.

    Returns dict with keys:
    - title_text: list of suspected English titles
    - displayname_text: list of suspected English displayName values
    - textbox_text: list of suspected English textbox content
    - missing_displayname: list of nativeQueryRef values without displayName
    """
    results = {
        "title_text": [],
        "displayname_text": [],
        "textbox_text": [],
        "missing_displayname": []
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
        return results

    visual = data.get("visual", {})

    # Check title text
    vco = visual.get("visualContainerObjects", {})
    for title_obj in vco.get("title", []):
        text_expr = title_obj.get("properties", {}).get("text", {}).get("expr", {}).get("Literal", {}).get("Value")
        if text_expr:
            # Strip single quotes from literal strings
            clean_text = text_expr.strip("'")
            if is_suspected_english(clean_text):
                results["title_text"].append(clean_text)

    # Check subtitle
    for subtitle_obj in vco.get("subTitle", []):
        text_expr = subtitle_obj.get("properties", {}).get("text", {}).get("expr", {}).get("Literal", {}).get("Value")
        if text_expr:
            clean_text = text_expr.strip("'")
            if is_suspected_english(clean_text):
                results["title_text"].append(clean_text)

    # Check projections for displayName and nativeQueryRef
    query_state = visual.get("query", {}).get("queryState", {})
    for bucket in query_state.values():
        if isinstance(bucket, dict) and "projections" in bucket:
            for proj in bucket["projections"]:
                nqr = proj.get("nativeQueryRef")
                dn = proj.get("displayName")

                if nqr and not dn:
                    # Missing displayName - check if nqr looks English
                    if is_suspected_english(nqr):
                        results["missing_displayname"].append(nqr)
                elif dn:
                    # Has displayName - check if it's English
                    if is_suspected_english(dn):
                        results["displayname_text"].append(dn)

    # Check textbox content
    visual_type = data.get("visualType")
    if visual_type == "textbox":
        # Textbox paragraphs
        paragraphs = visual.get("paragraphs", [])
        for para in paragraphs:
            for text_run in para.get("textRuns", []):
                text_val = text_run.get("value")
                if text_val and is_suspected_english(text_val):
                    results["textbox_text"].append(text_val)

    return results


def scan_all_visuals(pages_dir: str) -> List[Dict[str, Any]]:
    """
    Scan all visual.json files in pages directory.

    Returns list of findings with file path and suspected English strings.
    """
    findings = []
    pattern = os.path.join(pages_dir, "**", "visual.json")

    for file_path in sorted(glob.glob(pattern, recursive=True)):
        result = scan_visual_json(file_path)

        # Only include files with findings
        if any(result.values()):
            rel_path = os.path.relpath(file_path, pages_dir)
            findings.append({
                "file": rel_path,
                "title_text": result["title_text"],
                "displayname_text": result["displayname_text"],
                "textbox_text": result["textbox_text"],
                "missing_displayname": result["missing_displayname"]
            })

    return findings


def format_findings_as_text(findings: List[Dict[str, Any]]) -> str:
    """Format findings as readable text report."""
    if not findings:
        return "No suspected English content found. Translation appears complete!"

    lines = ["ENGLISH CONTENT AUDIT", "=" * 50, ""]

    total_issues = sum(
        len(f["title_text"]) + len(f["displayname_text"]) +
        len(f["textbox_text"]) + len(f["missing_displayname"])
        for f in findings
    )

    lines.append(f"Found {total_issues} suspected English strings in {len(findings)} files")
    lines.append("")

    for finding in findings:
        lines.append(f"File: {finding['file']}")

        if finding["title_text"]:
            lines.append(f"  Title text ({len(finding['title_text'])}):")
            for txt in finding["title_text"]:
                lines.append(f"    - '{txt}'")

        if finding["displayname_text"]:
            lines.append(f"  DisplayName ({len(finding['displayname_text'])}):")
            for txt in finding["displayname_text"]:
                lines.append(f"    - '{txt}'")

        if finding["missing_displayname"]:
            lines.append(f"  Missing displayName ({len(finding['missing_displayname'])}):")
            for txt in finding["missing_displayname"]:
                lines.append(f"    - '{txt}' (nativeQueryRef without displayName override)")

        if finding["textbox_text"]:
            lines.append(f"  Textbox content ({len(finding['textbox_text'])}):")
            for txt in finding["textbox_text"]:
                lines.append(f"    - '{txt}'")

        lines.append("")

    return "\n".join(lines)


def scan_missing_displaynames_only(pages_dir: str) -> str:
    """
    Find projections with nativeQueryRef but no displayName.

    Returns formatted text report.
    """
    findings = []
    pattern = os.path.join(pages_dir, "**", "visual.json")

    for file_path in sorted(glob.glob(pattern, recursive=True)):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
            continue

        visual = data.get("visual", {})
        visual_type = data.get("visualType", "unknown")
        query_state = visual.get("query", {}).get("queryState", {})

        for bucket in query_state.values():
            if isinstance(bucket, dict) and "projections" in bucket:
                for proj in bucket["projections"]:
                    nqr = proj.get("nativeQueryRef")
                    dn = proj.get("displayName")

                    if nqr and not dn:
                        rel_path = os.path.relpath(file_path, pages_dir)
                        findings.append({
                            "file": rel_path,
                            "nativeQueryRef": nqr,
                            "visualType": visual_type,
                            "suspected_english": is_suspected_english(nqr)
                        })

    if not findings:
        return "All projections have displayName overrides. Good!"

    lines = [
        "MISSING DISPLAYNAME AUDIT",
        "=" * 50,
        "",
        f"Found {len(findings)} projections without displayName",
        ""
    ]

    # Group by suspected English vs not
    english_group = [f for f in findings if f["suspected_english"]]
    other_group = [f for f in findings if not f["suspected_english"]]

    if english_group:
        lines.append(f"SUSPECTED ENGLISH ({len(english_group)}):")
        for f in english_group:
            lines.append(f"  {f['file']}")
            lines.append(f"    nativeQueryRef: '{f['nativeQueryRef']}'")
            lines.append(f"    visualType: {f['visualType']}")
        lines.append("")

    if other_group:
        lines.append(f"OTHER (not suspected English, {len(other_group)}):")
        for f in other_group:
            lines.append(f"  {f['file']}")
            lines.append(f"    nativeQueryRef: '{f['nativeQueryRef']}'")
            lines.append(f"    visualType: {f['visualType']}")
        lines.append("")

    return "\n".join(lines)


def validate_translation_coverage(pages_dir: str) -> str:
    """
    Run all scans and produce summary verdict.

    Returns formatted report with PASS/FAIL verdict.
    """
    findings = scan_all_visuals(pages_dir)

    # Count totals
    total_title = sum(len(f["title_text"]) for f in findings)
    total_displayname = sum(len(f["displayname_text"]) for f in findings)
    total_textbox = sum(len(f["textbox_text"]) for f in findings)
    total_missing = sum(len(f["missing_displayname"]) for f in findings)

    # Count all projections
    total_projections = 0
    projections_with_dn = 0

    pattern = os.path.join(pages_dir, "**", "visual.json")
    for file_path in glob.glob(pattern, recursive=True):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            continue

        query_state = data.get("visual", {}).get("query", {}).get("queryState", {})
        for bucket in query_state.values():
            if isinstance(bucket, dict) and "projections" in bucket:
                for proj in bucket["projections"]:
                    if proj.get("nativeQueryRef"):
                        total_projections += 1
                        if "displayName" in proj:
                            projections_with_dn += 1

    total_issues = total_title + total_displayname + total_textbox + total_missing
    verdict = "PASS" if total_issues == 0 else "FAIL"

    coverage_pct = (projections_with_dn / total_projections * 100) if total_projections > 0 else 0

    lines = [
        "TRANSLATION COVERAGE VALIDATION",
        "=" * 50,
        "",
        f"Total projections: {total_projections}",
        f"Projections with displayName: {projections_with_dn} ({coverage_pct:.1f}%)",
        f"Projections without displayName: {total_projections - projections_with_dn}",
        "",
        "SUSPECTED ENGLISH CONTENT:",
        f"  Title text: {total_title}",
        f"  DisplayName values: {total_displayname}",
        f"  Missing displayName (English nativeQueryRef): {total_missing}",
        f"  Textbox content: {total_textbox}",
        "",
        f"Total suspected English strings: {total_issues}",
        "",
        f"VERDICT: {verdict}",
        ""
    ]

    if verdict == "FAIL":
        lines.append("Translation incomplete. Run scan_english_remaining for details.")
    else:
        lines.append("No suspected English content found. Translation appears complete!")

    return "\n".join(lines)


# MCP Protocol Implementation

def send_message(message: dict):
    """Send JSON-RPC message with Content-Length header."""
    content = json.dumps(message, ensure_ascii=False)
    content_bytes = content.encode('utf-8')
    header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
    sys.stdout.buffer.write(header.encode('utf-8'))
    sys.stdout.buffer.write(content_bytes)
    sys.stdout.buffer.flush()


def read_message() -> dict:
    """Read JSON-RPC message with Content-Length header."""
    # Read headers
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            raise EOFError("stdin closed")
        line = line.decode('utf-8')
        if line == '\r\n':
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()

    # Read content
    content_length = int(headers.get('Content-Length', 0))
    content = sys.stdin.buffer.read(content_length).decode('utf-8')
    return json.loads(content)


def handle_initialize(request: dict) -> dict:
    """Handle initialize request."""
    return {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "powerbi-translation-audit",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {}
            }
        }
    }


def handle_tools_list(request: dict) -> dict:
    """Handle tools/list request."""
    return {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {
            "tools": [
                {
                    "name": "scan_english_remaining",
                    "description": "Scan all visual.json files for suspected English content (titles, displayName values, textbox text)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "pages_dir": {
                                "type": "string",
                                "description": "Path to report's definition/pages folder"
                            }
                        },
                        "required": ["pages_dir"]
                    }
                },
                {
                    "name": "scan_missing_displaynames",
                    "description": "Find projections with nativeQueryRef but no displayName override",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "pages_dir": {
                                "type": "string",
                                "description": "Path to report's definition/pages folder"
                            }
                        },
                        "required": ["pages_dir"]
                    }
                },
                {
                    "name": "validate_translation_coverage",
                    "description": "Run all scans and produce summary report with PASS/FAIL verdict",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "pages_dir": {
                                "type": "string",
                                "description": "Path to report's definition/pages folder"
                            }
                        },
                        "required": ["pages_dir"]
                    }
                }
            ]
        }
    }


def handle_tools_call(request: dict) -> dict:
    """Handle tools/call request."""
    tool_name = request["params"]["name"]
    args = request["params"]["arguments"]

    try:
        if tool_name == "scan_english_remaining":
            pages_dir = args["pages_dir"]
            findings = scan_all_visuals(pages_dir)
            result_text = format_findings_as_text(findings)

        elif tool_name == "scan_missing_displaynames":
            pages_dir = args["pages_dir"]
            result_text = scan_missing_displaynames_only(pages_dir)

        elif tool_name == "validate_translation_coverage":
            pages_dir = args["pages_dir"]
            result_text = validate_translation_coverage(pages_dir)

        else:
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ]
            }
        }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {
                "code": -32603,
                "message": f"Tool execution error: {str(e)}"
            }
        }


def main():
    """Main MCP server loop."""
    while True:
        try:
            request = read_message()

            method = request.get("method")

            if method == "initialize":
                response = handle_initialize(request)
                send_message(response)

            elif method == "initialized":
                # Notification, no response
                pass

            elif method == "tools/list":
                response = handle_tools_list(request)
                send_message(response)

            elif method == "tools/call":
                response = handle_tools_call(request)
                send_message(response)

            else:
                # Unknown method
                if "id" in request:
                    send_message({
                        "jsonrpc": "2.0",
                        "id": request["id"],
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    })

        except EOFError:
            break
        except Exception as e:
            # Log error to stderr (not stdout which is protocol channel)
            print(f"Server error: {e}", file=sys.stderr)
            break


if __name__ == "__main__":
    main()
