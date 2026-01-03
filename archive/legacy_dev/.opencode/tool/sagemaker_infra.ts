/**
 * SageMaker Infrastructure Report Tool for opencode
 *
 * Generates comprehensive reports tracing AWS ML infrastructure:
 * API Gateway -> Lambda (with ENDPOINT_NAME) -> SageMaker Endpoint -> Config -> Model
 *
 * Includes autoscaling policies, instance types, and masked API keys.
 */

import { tool } from "@opencode-ai/plugin";

const PYTHON_SCRIPT = "scripts/sagemaker_infra_report.py";

/**
 * Generate SageMaker infrastructure report
 */
export const sagemaker_infra_report = tool({
  description:
    "Generate a comprehensive report tracing AWS ML infrastructure: " +
    "API Gateway -> Lambda -> SageMaker Endpoint -> Endpoint Config -> Model. " +
    "Includes autoscaling policies, instance types, API keys (masked), and identifies orphaned resources. " +
    "Outputs report to reports/aws_infra/<timestamp>/report.md",
  args: {
    region: tool.schema
      .string()
      .optional()
      .describe("AWS region to scan (default: eu-central-1)"),
    output_dir: tool.schema
      .string()
      .optional()
      .describe(
        "Custom output directory path (default: reports/aws_infra/<timestamp>)"
      ),
  },
  async execute(args) {
    const cmdArgs = ["python3", PYTHON_SCRIPT];

    if (args.region) {
      cmdArgs.push("--region", args.region);
    }
    if (args.output_dir) {
      cmdArgs.push("--output-dir", args.output_dir);
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

    // Combine stdout (report paths) and stderr (progress messages) for context
    const result = {
      status: exitCode === 0 ? "success" : "partial",
      output: output.trim(),
      progress: stderr.trim(),
    };

    return JSON.stringify(result, null, 2);
  },
});
