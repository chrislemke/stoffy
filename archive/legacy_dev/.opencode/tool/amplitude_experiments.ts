/**
 * Amplitude Experiment Tools for opencode (EU)
 *
 * Read-only tools to:
 * - Search & inspect experiments via Management API (EU)
 * - Evaluate variants via Experiment Evaluation API (EU Residency Server) using the official SDK
 * - Fetch chart data (CSV) via Dashboard REST API (EU)
 */

import { tool } from "@opencode-ai/plugin";

const PYTHON_SCRIPT = "scripts/amplitude_experiments_client.py";

// ---------------------------------------------------------------------------
// Experiment Management tools
// ---------------------------------------------------------------------------

/**
 * Search experiments by name, key, or id.
 */
export const amplitude_experiments_search = tool({
  description:
    "Search Amplitude experiments (EU) by name, key, or id. Uses the Experiment Management API (EU).",
  args: {
    query: tool.schema
      .string()
      .describe("Free-text query (matches name, key, or id). Use empty string to list all."),
    projectId: tool.schema
      .string()
      .optional()
      .describe("Optional Amplitude projectId to filter experiments."),
    includeArchived: tool.schema
      .boolean()
      .optional()
      .describe("Include archived experiments (default: false)."),
  },
  async execute(args) {
    const projectIdArg = args.projectId ?? "";
    const includeArchivedArg = args.includeArchived === true ? "true" : "false";

    // Quote the query to handle spaces
    const queryArg = args.query ? `"${args.query}"` : '""';

    const result =
      await Bun.$`python3 ${PYTHON_SCRIPT} experiment-search ${queryArg} ${projectIdArg} ${includeArchivedArg}`.text();
    return result.trim();
  },
});

/**
 * Get configuration details for a single experiment.
 */
export const amplitude_experiments_get_details = tool({
  description:
    "Get configuration details for an Amplitude experiment (EU) by id, key, or exact name.",
  args: {
    identifier: tool.schema
      .string()
      .describe("Experiment id, key, or exact name (e.g. 'Best Offer Box (BOB) - V2')."),
  },
  async execute(args) {
    const identifierArg = `"${args.identifier}"`;
    const result =
      await Bun.$`python3 ${PYTHON_SCRIPT} experiment-details ${identifierArg}`.text();
    return result.trim();
  },
});

// ---------------------------------------------------------------------------
// Evaluation API (EU) – per-user variant evaluation
// ---------------------------------------------------------------------------

/**
 * Evaluate variant assignment for a user using the official Amplitude Experiment SDK (EU).
 */
export const amplitude_experiments_eval_user = tool({
  description:
    "Evaluate variant assignment for a user via Amplitude's Experiment Evaluation API (EU Residency Server).",
  args: {
    user_id: tool.schema
      .string()
      .optional()
      .describe("User id to evaluate (optional if device_id is provided)."),
    device_id: tool.schema
      .string()
      .optional()
      .describe("Device id to evaluate (optional if user_id is provided)."),
    flag_keys: tool.schema
      .string()
      .optional()
      .describe(
        "Comma-separated list of flag keys to evaluate (e.g. 'best-offer-box-v2'). If omitted, all flags for the deployment are evaluated."
      ),
    context_json: tool.schema
      .string()
      .optional()
      .describe(
        "Optional JSON string for user context, e.g. '{\"user_properties\":{\"country\":\"DE\"}}'."
      ),
  },
  async execute(args) {
    const userIdArg = args.user_id ? `"${args.user_id}"` : "-";
    const deviceIdArg = args.device_id ? `"${args.device_id}"` : "-";
    const flagKeysArg = args.flag_keys ? `"${args.flag_keys}"` : "-";
    const contextArg = args.context_json ? `"${args.context_json.replace(/"/g, '\\"')}"` : "-";

    const result =
      await Bun.$`python3 ${PYTHON_SCRIPT} eval-user ${userIdArg} ${deviceIdArg} ${flagKeysArg} ${contextArg}`.text();
    return result.trim();
  },
});

// ---------------------------------------------------------------------------
// Dashboard REST API (EU) – chart CSV
// ---------------------------------------------------------------------------

/**
 * Fetch CSV-backed data for a saved Amplitude chart (EU) and return as JSON rows.
 *
 * For experiments, point this at the Experiment Results chart for your experiment.
 */
export const amplitude_experiments_chart_csv = tool({
  description:
    "Fetch the CSV data for a saved Amplitude chart (EU) and return JSON rows. Use with experiment result charts to analyze performance & significance.",
  args: {
    chart_id: tool.schema
      .string()
      .describe(
        "Chart ID from the Amplitude URL (e.g. 'abc123' from https://analytics.eu.amplitude.com/.../chart/abc123)."
      ),
  },
  async execute(args) {
    const result =
      await Bun.$`python3 ${PYTHON_SCRIPT} chart-csv ${args.chart_id}`.text();
    return result.trim();
  },
});
