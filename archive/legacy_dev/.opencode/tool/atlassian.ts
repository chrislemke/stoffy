/**
 * Atlassian Tools for opencode
 *
 * Consolidated access to JIRA and Confluence via atlassian-python-api.
 * Requires credentials in .env file at project root.
 *
 * JIRA: READ + limited WRITE (update description, add comment)
 * Confluence: READ-ONLY (search for context, never create/modify)
 */

import { tool } from "@opencode-ai/plugin";

const PYTHON_SCRIPT = "scripts/atlassian_client.py";

// ============================================================================
// JIRA Read Tools
// ============================================================================

/**
 * Get a JIRA issue by its key
 */
export const jira_get_issue = tool({
  description:
    "Get a JIRA issue by its key (e.g., DS-1123, FML-242, FLUG-17004). Returns issue details including summary, status, assignee, description, and labels.",
  args: {
    issue_key: tool.schema
      .string()
      .describe("JIRA issue key (e.g., DS-1123, FML-242)"),
    fields: tool.schema
      .string()
      .optional()
      .describe(
        "Optional: Comma-separated list of fields to return (e.g., 'summary,status,assignee')"
      ),
  },
  async execute(args) {
    // Use spawn with explicit args array for consistent handling
    const cmdArgs = ["python3", PYTHON_SCRIPT, "jira-issue", args.issue_key];
    if (args.fields) {
      cmdArgs.push(args.fields);
    }

    const proc = Bun.spawn(cmdArgs, {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

/**
 * Search JIRA issues using JQL
 */
export const jira_search = tool({
  description:
    "Search JIRA issues using JQL (JIRA Query Language). Examples: 'project = DS AND status = Open', 'assignee = currentUser() ORDER BY updated DESC', 'labels = ml-team AND created >= -7d'",
  args: {
    jql: tool.schema
      .string()
      .describe(
        "JQL query string (e.g., 'project = DS AND status != Closed ORDER BY updated DESC')"
      ),
    max_results: tool.schema
      .number()
      .optional()
      .describe("Maximum number of results to return (default: 20, max: 100)"),
  },
  async execute(args) {
    const maxResults = args.max_results ?? 20;
    // Use spawn with explicit args array to handle JQL queries with spaces/special chars
    const proc = Bun.spawn(["python3", PYTHON_SCRIPT, "jira-search", args.jql, String(maxResults)], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

/**
 * Get comments on a JIRA issue
 */
export const jira_get_comments = tool({
  description:
    "Get all comments on a JIRA issue. Returns comment author, creation date, and comment body.",
  args: {
    issue_key: tool.schema
      .string()
      .describe("JIRA issue key (e.g., DS-1123, FML-242)"),
  },
  async execute(args) {
    const proc = Bun.spawn(["python3", PYTHON_SCRIPT, "jira-comments", args.issue_key], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

/**
 * Get all issues under an epic
 */
export const jira_get_epic_children = tool({
  description:
    "Get all issues (stories, tasks, bugs) that are children of a specific epic. Returns list of issues with key, summary, status, and type.",
  args: {
    epic_key: tool.schema
      .string()
      .describe("Epic key (e.g., FML-100, FPRO-200)"),
    max_results: tool.schema
      .number()
      .optional()
      .describe("Maximum number of results to return (default: 50)"),
  },
  async execute(args) {
    const maxResults = args.max_results ?? 50;
    const proc = Bun.spawn(["python3", PYTHON_SCRIPT, "jira-epic-children", args.epic_key, String(maxResults)], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

/**
 * Get linked issues for a ticket
 */
export const jira_get_linked_issues = tool({
  description:
    "Get all issues linked to a specific ticket. Returns linked issues with their link types (blocks, is blocked by, relates to, duplicates, etc.).",
  args: {
    issue_key: tool.schema
      .string()
      .describe("JIRA issue key (e.g., DS-1123, FML-242)"),
  },
  async execute(args) {
    const proc = Bun.spawn(["python3", PYTHON_SCRIPT, "jira-linked-issues", args.issue_key], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

/**
 * Gather all context for a ticket
 */
export const jira_gather_context = tool({
  description:
    "Gather all relevant context for a JIRA ticket: ticket details, epic info, sibling tickets under same epic, linked issues, and optionally related Confluence pages. Use this before improving a ticket.",
  args: {
    ticket_id: tool.schema
      .string()
      .describe("JIRA ticket ID (e.g., FML-247, FPRO-896)"),
    include_confluence: tool.schema
      .boolean()
      .optional()
      .describe("Include Confluence search results for related pages (default: false)"),
  },
  async execute(args) {
    // Use spawn with explicit args array for consistent handling
    const cmdArgs = ["python3", PYTHON_SCRIPT, "jira-gather-context", args.ticket_id];
    if (args.include_confluence) {
      cmdArgs.push("--include-confluence");
    }

    const proc = Bun.spawn(cmdArgs, {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

// ============================================================================
// JIRA Write Tools
// ============================================================================

/**
 * Update JIRA ticket description
 */
export const jira_update_description = tool({
  description:
    "Update a JIRA ticket description by appending new content. Converts Markdown to Atlassian Document Format (ADF). Content must be provided via a file path to handle complex markdown with code blocks.",
  args: {
    ticket_id: tool.schema
      .string()
      .describe("JIRA ticket ID (e.g., FML-247)"),
    file: tool.schema
      .string()
      .describe("Path to file containing markdown content to append to the description"),
  },
  async execute(args) {
    // Use spawn with explicit args array to handle file paths with spaces
    const proc = Bun.spawn(["python3", PYTHON_SCRIPT, "jira-update-description", args.ticket_id, "--file", args.file], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

/**
 * Add a comment to a JIRA ticket
 */
export const jira_add_comment = tool({
  description:
    "Add a comment to a JIRA ticket. Supports basic wiki markup. Can provide content directly or via file path.",
  args: {
    ticket_id: tool.schema
      .string()
      .describe("JIRA ticket ID (e.g., FML-247)"),
    content: tool.schema
      .string()
      .optional()
      .describe("Comment text (for simple comments)"),
    file: tool.schema
      .string()
      .optional()
      .describe("Path to file containing comment (for complex content)"),
  },
  async execute(args) {
    if (!args.content && !args.file) {
      return JSON.stringify({ error: "Either content or file must be provided" });
    }

    // Use spawn with explicit args array to handle content with spaces/special chars
    const cmdArgs = ["python3", PYTHON_SCRIPT, "jira-add-comment", args.ticket_id];
    if (args.file) {
      cmdArgs.push("--file", args.file);
    } else {
      cmdArgs.push("--content", args.content!);
    }

    const proc = Bun.spawn(cmdArgs, {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

// ============================================================================
// Confluence Read Tools (READ-ONLY)
// ============================================================================

/**
 * Get a Confluence page by space key and title
 */
export const confluence_get_page = tool({
  description:
    "Get a Confluence page by its space key and title. Returns page content, version, and metadata. READ-ONLY.",
  args: {
    space: tool.schema
      .string()
      .describe("Confluence space key (e.g., 'TECH', 'ML', 'DOCS')"),
    title: tool.schema.string().describe("Page title (exact match required)"),
  },
  async execute(args) {
    // Use spawn with explicit args array to handle titles with spaces
    const proc = Bun.spawn(["python3", PYTHON_SCRIPT, "confluence-page", args.space, args.title], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

/**
 * Get a Confluence page by ID
 */
export const confluence_get_page_by_id = tool({
  description:
    "Get a Confluence page by its numeric ID. Returns page content, version, and metadata. READ-ONLY.",
  args: {
    page_id: tool.schema.string().describe("Confluence page ID (numeric)"),
  },
  async execute(args) {
    const proc = Bun.spawn(["python3", PYTHON_SCRIPT, "confluence-page-id", args.page_id], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

/**
 * Search Confluence using CQL
 */
export const confluence_search = tool({
  description:
    "Search Confluence using CQL (Confluence Query Language). Examples: 'type=page AND space=TECH', 'text ~ \"machine learning\"', 'title ~ \"API\" AND space IN (TECH, DOCS)'. READ-ONLY.",
  args: {
    cql: tool.schema
      .string()
      .describe(
        "CQL query string (e.g., 'type=page AND space=TECH AND text ~ \"deployment\"')"
      ),
    limit: tool.schema
      .number()
      .optional()
      .describe("Maximum number of results to return (default: 20)"),
  },
  async execute(args) {
    const limit = args.limit ?? 20;
    // Use spawn with explicit args array to handle CQL queries with spaces/special chars
    const proc = Bun.spawn(["python3", PYTHON_SCRIPT, "confluence-search", args.cql, String(limit)], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});

/**
 * List pages in a Confluence space
 */
export const confluence_list_space = tool({
  description:
    "List all pages in a Confluence space. Returns page titles, IDs, and URLs. READ-ONLY.",
  args: {
    space_key: tool.schema
      .string()
      .describe("Confluence space key (e.g., 'TECH', 'ML', 'DOCS')"),
    limit: tool.schema
      .number()
      .optional()
      .describe("Maximum number of pages to return (default: 50)"),
  },
  async execute(args) {
    const limit = args.limit ?? 50;
    const proc = Bun.spawn(["python3", PYTHON_SCRIPT, "confluence-space", args.space_key, String(limit)], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({ error: stderr || `Process exited with code ${exitCode}` });
    }
    return output.trim();
  },
});
