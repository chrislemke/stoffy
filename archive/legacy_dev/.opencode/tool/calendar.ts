/**
 * Calendar Tools for opencode
 *
 * Provides calendar event management including listing, creating,
 * updating, and deleting events. Uses natural language date parsing
 * via the dateparser Python library.
 */

import { tool } from "@opencode-ai/plugin";

const PYTHON_SCRIPT = "scripts/calendar_helper.py";

// ============================================================================
// Calendar List Tool
// ============================================================================

/**
 * List calendar events within a date range
 */
export const calendar_list = tool({
  description:
    "List calendar events within a date range. Supports natural language like 'today', 'tomorrow', 'this week', 'next month', 'this year', or explicit dates like '2025-01-15' or '2025-01-01 to 2025-01-31'.",
  args: {
    range: tool.schema
      .string()
      .describe(
        "Date range: 'today', 'tomorrow', 'this week', 'next week', 'this month', 'next month', 'this year', or explicit dates"
      ),
    format: tool.schema
      .enum(["table", "calendar", "json"])
      .optional()
      .describe(
        "Output format: 'table' (default), 'calendar' (visual grid), or 'json'"
      ),
  },
  async execute(args) {
    const format = args.format ?? "table";
    const result =
      await Bun.$`python3 ${PYTHON_SCRIPT} list ${args.range} --format ${format}`.text();
    return result.trim();
  },
});

// ============================================================================
// Calendar Create Tool
// ============================================================================

/**
 * Create a new calendar event
 */
export const calendar_create = tool({
  description:
    "Create a new calendar event. For meeting-type events, automatically creates a meeting file in the appropriate location. IMPORTANT: Dates MUST be in ISO format (YYYY-MM-DD) and times in HH:MM format. The LLM must convert any natural language dates before calling this tool.",
  args: {
    title: tool.schema.string().describe("Event title"),
    date: tool.schema
      .string()
      .describe(
        "Event date in STRICT ISO format (YYYY-MM-DD). Natural language dates are NOT supported - convert them first. Example: '2025-12-15'"
      ),
    time: tool.schema
      .string()
      .optional()
      .describe("Event time in STRICT HH:MM format (24-hour). Example: '14:30' for 2:30 PM"),
    duration: tool.schema
      .string()
      .optional()
      .describe("Duration (e.g., '30m', '1h', '2h30m')"),
    type: tool.schema
      .enum([
        "meeting",
        "reminder",
        "deadline",
        "appointment",
        "personal",
        "holiday",
        "vacation",
        "blocked",
      ])
      .optional()
      .describe("Event type (default: 'appointment')"),
    location: tool.schema.string().optional().describe("Event location"),
    participants: tool.schema
      .string()
      .optional()
      .describe(
        "Comma-separated person slugs (e.g., 'alex_kumar,anna_kowalski')"
      ),
    project: tool.schema.string().optional().describe("Related project name"),
    ticket: tool.schema
      .string()
      .optional()
      .describe("Related ticket ID (e.g., 'FML-247')"),
    recurrence: tool.schema
      .enum(["daily", "weekly", "monthly", "yearly"])
      .optional()
      .describe("Recurrence pattern for recurring events"),
    description: tool.schema.string().optional().describe("Event description"),
  },
  async execute(args) {
    const cmdParts = [
      "python3",
      PYTHON_SCRIPT,
      "create",
      "--title",
      args.title,
      "--date",
      args.date,
    ];

    if (args.time) {
      cmdParts.push("--time", args.time);
    }
    if (args.duration) {
      cmdParts.push("--duration", args.duration);
    }
    if (args.type) {
      cmdParts.push("--type", args.type);
    }
    if (args.location) {
      cmdParts.push("--location", args.location);
    }
    if (args.participants) {
      cmdParts.push("--participants", args.participants);
    }
    if (args.project) {
      cmdParts.push("--project", args.project);
    }
    if (args.ticket) {
      cmdParts.push("--ticket", args.ticket);
    }
    if (args.recurrence) {
      cmdParts.push("--recurrence", args.recurrence);
    }
    if (args.description) {
      cmdParts.push("--description", args.description);
    }

    const result = await Bun.$`${cmdParts}`.text();
    return result.trim();
  },
});

// ============================================================================
// Calendar Get Tool
// ============================================================================

/**
 * Get details of a specific calendar event
 */
export const calendar_get = tool({
  description:
    "Get detailed information about a specific calendar event by its ID.",
  args: {
    event_id: tool.schema
      .string()
      .describe("Event ID (e.g., 'EVENT-001', '001', or 'E-001')"),
  },
  async execute(args) {
    const result =
      await Bun.$`python3 ${PYTHON_SCRIPT} get ${args.event_id}`.text();
    return result.trim();
  },
});

// ============================================================================
// Calendar Update Tool
// ============================================================================

/**
 * Update an existing calendar event
 */
export const calendar_update = tool({
  description:
    "Update an existing calendar event. Only specify the fields you want to change. IMPORTANT: Dates MUST be in ISO format (YYYY-MM-DD) and times in HH:MM format.",
  args: {
    event_id: tool.schema.string().describe("Event ID to update"),
    title: tool.schema.string().optional().describe("New title"),
    date: tool.schema.string().optional().describe("New date in STRICT ISO format (YYYY-MM-DD)"),
    time: tool.schema.string().optional().describe("New time in STRICT HH:MM format (24-hour)"),
    duration: tool.schema.string().optional().describe("New duration"),
    location: tool.schema.string().optional().describe("New location"),
    type: tool.schema
      .enum([
        "meeting",
        "reminder",
        "deadline",
        "appointment",
        "personal",
        "holiday",
        "vacation",
        "blocked",
      ])
      .optional()
      .describe("New type"),
    status: tool.schema
      .enum(["scheduled", "completed", "cancelled"])
      .optional()
      .describe("New status"),
    participants: tool.schema
      .string()
      .optional()
      .describe("New participants (comma-separated)"),
  },
  async execute(args) {
    const cmdParts = ["python3", PYTHON_SCRIPT, "update", args.event_id];

    if (args.title) {
      cmdParts.push("--title", args.title);
    }
    if (args.date) {
      cmdParts.push("--date", args.date);
    }
    if (args.time) {
      cmdParts.push("--time", args.time);
    }
    if (args.duration) {
      cmdParts.push("--duration", args.duration);
    }
    if (args.location) {
      cmdParts.push("--location", args.location);
    }
    if (args.type) {
      cmdParts.push("--type", args.type);
    }
    if (args.status) {
      cmdParts.push("--status", args.status);
    }
    if (args.participants) {
      cmdParts.push("--participants", args.participants);
    }

    const result = await Bun.$`${cmdParts}`.text();
    return result.trim();
  },
});

// ============================================================================
// Calendar Delete Tool
// ============================================================================

/**
 * Delete (cancel) a calendar event
 */
export const calendar_delete = tool({
  description:
    "Delete (mark as cancelled) a calendar event. The event file is preserved but marked as cancelled.",
  args: {
    event_id: tool.schema.string().describe("Event ID to delete/cancel"),
  },
  async execute(args) {
    const result =
      await Bun.$`python3 ${PYTHON_SCRIPT} delete ${args.event_id}`.text();
    return result.trim();
  },
});
