/**
 * Amplitude Experiment Report Tool for opencode
 *
 * Retrieves experiment data from Amplitude and generates a markdown report
 * saved to the appropriate project folder. Uses the Management API to fetch
 * experiment configuration and metadata.
 *
 * Features:
 * - Auto-infers project from experiment name/key
 * - Saves dated reports to project_management/{project}/experiments/
 * - Falls back to reports/experiments/ if no project match
 */

import { tool } from "@opencode-ai/plugin";

const PYTHON_SCRIPT = "scripts/amplitude_experiments_client.py";

/**
 * Generate an experiment report from Amplitude data
 */
export const amplitude_experiment_report = tool({
  description:
    "Retrieve Amplitude experiment data and generate a markdown report. " +
    "The report includes experiment configuration, variants, timeline, and deployments. " +
    "Auto-infers the target project from experiment name, or specify explicitly. " +
    "Reports are saved to project_management/{project}/experiments/ or reports/experiments/.",
  args: {
    experiment_name: tool.schema
      .string()
      .describe(
        "Experiment name, key, or ID to generate report for. " +
          "Supports partial matching (e.g., 'service fee', 'sfomi', 'best-offer-box')."
      ),
    project: tool.schema
      .string()
      .optional()
      .describe(
        "Target project folder name (e.g., 'service_fee_optimization'). " +
          "If not specified, the tool will attempt to auto-detect based on experiment name."
      ),
  },
  async execute(args) {
    const cmdArgs = [
      "python3",
      PYTHON_SCRIPT,
      "generate-report",
      args.experiment_name,
    ];

    if (args.project) {
      cmdArgs.push("--project", args.project);
    }

    const proc = Bun.spawn(cmdArgs, {
      stdout: "pipe",
      stderr: "pipe",
    });

    const output = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0 && !output.trim()) {
      return JSON.stringify({
        error: stderr || `Process exited with code ${exitCode}`,
      });
    }

    return output.trim();
  },
});
