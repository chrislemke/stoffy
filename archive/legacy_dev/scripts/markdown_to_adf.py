"""
Markdown to Atlassian Document Format (ADF) Converter

Converts Markdown text to JIRA-compatible ADF JSON format.
This enables proper rendering of rich text content in JIRA Cloud ticket descriptions.

ADF Documentation: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/

Usage:
    from markdown_to_adf import markdown_to_adf

    adf_doc = markdown_to_adf("# Hello **world**")
    # Returns ADF JSON dict ready for JIRA API
"""

from __future__ import annotations

import re
from typing import Any

# Try to import mistune, fall back to basic parsing if not available
MISTUNE_AVAILABLE = False
_mistune_module: Any = None
try:
    import mistune  # type: ignore[import-not-found]

    _mistune_module = mistune
    MISTUNE_AVAILABLE = True
except ImportError:
    pass


def markdown_to_adf(markdown_text: str) -> dict[str, Any]:
    """
    Convert Markdown text to Atlassian Document Format (ADF).

    Args:
        markdown_text: Raw Markdown string

    Returns:
        ADF document as a dictionary ready for JIRA API
    """
    if MISTUNE_AVAILABLE:
        return _convert_with_mistune(markdown_text)
    else:
        return _convert_basic(markdown_text)


def _convert_with_mistune(markdown_text: str) -> dict[str, Any]:
    """Convert markdown to ADF using mistune parser."""
    if _mistune_module is None:
        raise ImportError("mistune is required but not installed")

    # Create AST parser with table plugin
    md = _mistune_module.create_markdown(
        renderer="ast", plugins=["table", "strikethrough"]
    )
    tokens = md(markdown_text)

    # Convert AST tokens to ADF
    content = _tokens_to_adf(tokens)

    return {
        "version": 1,
        "type": "doc",
        "content": content,
    }


def _tokens_to_adf(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert mistune AST tokens to ADF block nodes."""
    adf_content = []

    for token in tokens:
        token_type = token.get("type")

        if token_type == "heading":
            adf_content.append(_make_heading(token))
        elif token_type == "paragraph":
            adf_content.append(_make_paragraph(token))
        elif token_type == "block_code":
            adf_content.append(_make_code_block(token))
        elif token_type == "thematic_break":
            adf_content.append(_make_rule())
        elif token_type == "list":
            adf_content.append(_make_list(token))
        elif token_type == "table":
            adf_content.append(_make_table(token))
        elif token_type == "block_quote":
            adf_content.append(_make_blockquote(token))
        elif token_type == "blank_line":
            # Skip blank lines - they don't need representation in ADF
            pass
        else:
            # Fallback: treat as paragraph
            if token.get("children") or token.get("raw"):
                adf_content.append(_make_paragraph(token))

    return adf_content


# =============================================================================
# Block Node Builders
# =============================================================================


def _make_heading(token: dict[str, Any]) -> dict[str, Any]:
    """Create an ADF heading node."""
    level = token.get("attrs", {}).get("level", 1)
    # Clamp level to 1-6 as per ADF spec
    level = max(1, min(6, level))

    inline_content = _children_to_inline(token.get("children", []))

    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": inline_content,
    }


def _make_paragraph(token: dict[str, Any]) -> dict[str, Any]:
    """Create an ADF paragraph node."""
    children = token.get("children", [])

    # Handle case where token has raw text but no children
    if not children and token.get("raw"):
        children = [{"type": "text", "raw": token["raw"]}]

    inline_content = _children_to_inline(children)

    # Empty paragraph is valid in ADF
    return {
        "type": "paragraph",
        "content": inline_content if inline_content else [],
    }


def _make_code_block(token: dict[str, Any]) -> dict[str, Any]:
    """Create an ADF codeBlock node."""
    raw = token.get("raw", "")
    info = token.get("info") or token.get("attrs", {}).get("info")

    # Map common language names to Prism-supported names
    language_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "sh": "bash",
        "shell": "bash",
        "yml": "yaml",
        "dockerfile": "docker",
    }

    if info:
        # Extract first word as language identifier
        lang = info.split()[0].lower()
        lang = language_map.get(lang, lang)
    else:
        lang = None

    node: dict[str, Any] = {
        "type": "codeBlock",
        "content": [{"type": "text", "text": raw}] if raw else [],
    }

    if lang:
        node["attrs"] = {"language": lang}

    return node


def _make_rule() -> dict[str, Any]:
    """Create an ADF rule (horizontal line) node."""
    return {"type": "rule"}


def _make_list(token: dict[str, Any]) -> dict[str, Any]:
    """Create an ADF bulletList or orderedList node."""
    ordered = token.get("attrs", {}).get("ordered", False)
    list_type = "orderedList" if ordered else "bulletList"

    items = []
    for child in token.get("children", []):
        if child.get("type") == "list_item":
            items.append(_make_list_item(child))

    node: dict[str, Any] = {"type": list_type, "content": items}

    # Add start number for ordered lists if not 1
    if ordered:
        start = token.get("attrs", {}).get("start", 1)
        if start != 1:
            node["attrs"] = {"order": start}

    return node


def _make_list_item(token: dict[str, Any]) -> dict[str, Any]:
    """Create an ADF listItem node."""
    # List items contain block-level content (paragraphs, nested lists, etc.)
    content = []

    for child in token.get("children", []):
        child_type = child.get("type")
        if child_type == "paragraph":
            content.append(_make_paragraph(child))
        elif child_type == "list":
            content.append(_make_list(child))
        elif child_type == "block_text":
            # Convert block_text to paragraph
            content.append(_make_paragraph(child))
        else:
            # Wrap inline content in paragraph
            content.append(_make_paragraph(child))

    # If no content, add empty paragraph
    if not content:
        content = [{"type": "paragraph", "content": []}]

    return {"type": "listItem", "content": content}


def _make_table(token: dict[str, Any]) -> dict[str, Any]:
    """Create an ADF table node."""
    rows = []

    for child in token.get("children", []):
        child_type = child.get("type")
        if child_type == "table_head":
            rows.extend(_make_table_rows(child, is_header=True))
        elif child_type == "table_body":
            rows.extend(_make_table_rows(child, is_header=False))

    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "center"},
        "content": rows,
    }


def _make_table_rows(
    section: dict[str, Any], is_header: bool = False
) -> list[dict[str, Any]]:
    """Create ADF tableRow nodes from table head or body."""
    rows = []

    for row in section.get("children", []):
        if row.get("type") == "table_row":
            cells = []
            for cell in row.get("children", []):
                if cell.get("type") == "table_cell":
                    cells.append(_make_table_cell(cell, is_header=is_header))
            if cells:
                rows.append({"type": "tableRow", "content": cells})

    return rows


def _make_table_cell(token: dict[str, Any], is_header: bool = False) -> dict[str, Any]:
    """Create an ADF tableCell or tableHeader node."""
    cell_type = "tableHeader" if is_header else "tableCell"

    # Table cells contain block content (paragraphs)
    inline_content = _children_to_inline(token.get("children", []))

    return {
        "type": cell_type,
        "attrs": {},
        "content": [{"type": "paragraph", "content": inline_content}],
    }


def _make_blockquote(token: dict[str, Any]) -> dict[str, Any]:
    """Create an ADF blockquote node."""
    content = _tokens_to_adf(token.get("children", []))

    return {"type": "blockquote", "content": content}


# =============================================================================
# Inline Node Builders
# =============================================================================


def _children_to_inline(children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert mistune children tokens to ADF inline nodes."""
    inline_content = []

    for child in children:
        inline_nodes = _token_to_inline(child)
        inline_content.extend(inline_nodes)

    return inline_content


def _token_to_inline(token: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a single mistune token to ADF inline node(s)."""
    token_type = token.get("type")

    if token_type == "text":
        text = token.get("raw", "")
        if text:
            return [{"type": "text", "text": text}]
        return []

    elif token_type == "strong":
        # Bold text
        children = _children_to_inline(token.get("children", []))
        return _apply_mark_to_children(children, {"type": "strong"})

    elif token_type == "emphasis":
        # Italic text
        children = _children_to_inline(token.get("children", []))
        return _apply_mark_to_children(children, {"type": "em"})

    elif token_type == "strikethrough":
        # Strikethrough text
        children = _children_to_inline(token.get("children", []))
        return _apply_mark_to_children(children, {"type": "strike"})

    elif token_type == "codespan":
        # Inline code
        raw = token.get("raw", "")
        if raw:
            return [{"type": "text", "text": raw, "marks": [{"type": "code"}]}]
        return []

    elif token_type == "link":
        # Hyperlink
        children = token.get("children", [])
        url = token.get("attrs", {}).get("url", "")
        title = token.get("attrs", {}).get("title")

        inline_children = _children_to_inline(children)
        mark: dict[str, Any] = {"type": "link", "attrs": {"href": url}}
        if title:
            mark["attrs"]["title"] = title

        return _apply_mark_to_children(inline_children, mark)

    elif token_type == "image":
        # Images are complex in ADF - convert to link with alt text
        alt = token.get("attrs", {}).get("alt", "")
        url = token.get("attrs", {}).get("url", "")
        text = alt or url
        return [
            {
                "type": "text",
                "text": f"[Image: {text}]",
                "marks": [{"type": "link", "attrs": {"href": url}}],
            }
        ]

    elif token_type == "softbreak":
        # Soft line break - just a space
        return [{"type": "text", "text": " "}]

    elif token_type == "linebreak":
        # Hard line break
        return [{"type": "hardBreak"}]

    else:
        # Unknown inline type - try to extract raw text
        raw = token.get("raw", "")
        if raw:
            return [{"type": "text", "text": raw}]
        # Try children
        children = token.get("children", [])
        if children:
            return _children_to_inline(children)
        return []


def _apply_mark_to_children(
    children: list[dict[str, Any]], mark: dict[str, Any]
) -> list[dict[str, Any]]:
    """Apply a mark to all text nodes in children."""
    result = []
    for child in children:
        if child.get("type") == "text":
            # Add mark to existing marks
            marks = child.get("marks", [])
            new_marks = marks + [mark]
            result.append({**child, "marks": new_marks})
        elif child.get("type") == "hardBreak":
            # hardBreak nodes don't take marks
            result.append(child)
        else:
            # Pass through other node types
            result.append(child)
    return result


# =============================================================================
# Basic Fallback Parser (no dependencies)
# =============================================================================


def _convert_basic(markdown_text: str) -> dict[str, Any]:
    """
    Basic markdown to ADF converter without external dependencies.

    This is a fallback when mistune is not available.
    Handles: headings, paragraphs, code blocks, horizontal rules, bold, italic, inline code.
    """
    lines = markdown_text.split("\n")
    content = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Code block (fenced)
        if line.startswith("```"):
            lang_match = re.match(r"```(\w*)", line)
            lang = lang_match.group(1) if lang_match else None
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code = "\n".join(code_lines)
            node: dict[str, Any] = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": code}] if code else [],
            }
            if lang:
                node["attrs"] = {"language": lang}
            content.append(node)
            i += 1  # Skip closing ```
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            inline = _parse_inline_basic(text)
            content.append(
                {
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": inline,
                }
            )
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            content.append({"type": "rule"})
            i += 1
            continue

        # Blank line
        if not line.strip():
            i += 1
            continue

        # Bullet list
        if re.match(r"^[\-\*\+]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^[\-\*\+]\s+", lines[i]):
                item_text = re.sub(r"^[\-\*\+]\s+", "", lines[i])
                inline = _parse_inline_basic(item_text)
                items.append(
                    {
                        "type": "listItem",
                        "content": [{"type": "paragraph", "content": inline}],
                    }
                )
                i += 1
            content.append({"type": "bulletList", "content": items})
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i])
                inline = _parse_inline_basic(item_text)
                items.append(
                    {
                        "type": "listItem",
                        "content": [{"type": "paragraph", "content": inline}],
                    }
                )
                i += 1
            content.append({"type": "orderedList", "content": items})
            continue

        # Regular paragraph
        para_lines = []
        while i < len(lines) and lines[i].strip() and not _is_block_start(lines[i]):
            para_lines.append(lines[i])
            i += 1

        if para_lines:
            para_text = " ".join(para_lines)
            inline = _parse_inline_basic(para_text)
            content.append({"type": "paragraph", "content": inline})

    return {
        "version": 1,
        "type": "doc",
        "content": content,
    }


def _is_block_start(line: str) -> bool:
    """Check if line starts a block element."""
    if line.startswith("#"):
        return True
    if line.startswith("```"):
        return True
    if re.match(r"^[-*_]{3,}\s*$", line):
        return True
    if re.match(r"^[\-\*\+]\s+", line):
        return True
    if re.match(r"^\d+\.\s+", line):
        return True
    return False


def _parse_inline_basic(text: str) -> list[dict[str, Any]]:
    """Parse inline formatting in basic mode."""
    result = []

    # Pattern for inline elements: **bold**, *italic*, `code`, [link](url)
    pattern = r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|[^*`\[]+)"

    for match in re.finditer(pattern, text):
        part = match.group(0)

        # Bold
        if part.startswith("**") and part.endswith("**"):
            inner = part[2:-2]
            result.append(
                {
                    "type": "text",
                    "text": inner,
                    "marks": [{"type": "strong"}],
                }
            )
        # Italic
        elif part.startswith("*") and part.endswith("*"):
            inner = part[1:-1]
            result.append(
                {
                    "type": "text",
                    "text": inner,
                    "marks": [{"type": "em"}],
                }
            )
        # Inline code
        elif part.startswith("`") and part.endswith("`"):
            inner = part[1:-1]
            result.append(
                {
                    "type": "text",
                    "text": inner,
                    "marks": [{"type": "code"}],
                }
            )
        # Link
        elif part.startswith("["):
            link_match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", part)
            if link_match:
                link_text = link_match.group(1)
                link_url = link_match.group(2)
                result.append(
                    {
                        "type": "text",
                        "text": link_text,
                        "marks": [{"type": "link", "attrs": {"href": link_url}}],
                    }
                )
        # Plain text
        elif part.strip():
            result.append({"type": "text", "text": part})

    return result


# =============================================================================
# Utility Functions
# =============================================================================


def merge_adf_documents(
    base_adf: dict[str, Any] | None, new_adf: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge two ADF documents, appending new_adf content to base_adf.

    Args:
        base_adf: Existing ADF document (or None)
        new_adf: New ADF content to append

    Returns:
        Merged ADF document
    """
    if base_adf is None:
        return new_adf

    base_content = base_adf.get("content", [])
    new_content = new_adf.get("content", [])

    return {
        "version": 1,
        "type": "doc",
        "content": base_content + new_content,
    }


def create_adf_separator() -> dict[str, Any]:
    """Create an ADF rule node (horizontal separator)."""
    return {"type": "rule"}


if __name__ == "__main__":
    # Simple test
    import json

    test_md = """# LLM Implementation Guide

**Generated:** 2025-12-10
**Epic:** [FPRO-1060](https://invia.atlassian.net/browse/FPRO-1060)
**Repository:** invia-flights/invia-flights-conversational-ai-bot

---

## Summary

Replace the current AWS Bedrock Guardrails implementation with CrewAI's native Task `guardrail` parameter.

## Background & Current State

**Current Implementation:**

- AWS Bedrock Guardrails are applied in `orchestrator_flow.py` during the `route()` step
- Guardrails are called via `apply_guardrails()` from `src/conversational_ai_bot/guardrails/aws_guardrails.py`

## Implementation Steps

1. **Create custom guardrail functions**
   - File: `src/conversational_ai_bot/guardrails/crewai_guardrails.py`
   - Define functions with signature: `(result: TaskOutput) -> Tuple[bool, Any]`

2. **Update task definitions**
   - Add `guardrail` parameter to relevant tasks

```python
def pii_guardrail(result: TaskOutput) -> Tuple[bool, Any]:
    \"\"\"Check for PII in task output.\"\"\"
    # Implementation here
    return (True, result)
```

## Key Dependencies

| Package | Relevance |
|---------|-----------|
| crewai | Agent pipeline orchestration |
| langchain | LLM interactions |

## Verification

- [ ] Run `pytest` - all tests pass
- [ ] Manual test: Send a query with PII
"""

    result = markdown_to_adf(test_md)
    print(json.dumps(result, indent=2))
