---
description: Download Amplitude experiment data and save report to project folder
---

# Experiment Report

Download an Amplitude experiment by name and save a structured report to the appropriate project folder.

**Usage:**
```
/experiment-report <experiment name>
```

**Examples:**
```
/experiment-report New Recommender Model (NFRV) - V1
/experiment-report Best Offer Box (BOB) - V2
/experiment-report service-fee-v3
```

---

## Step 1: Parse Arguments

Extract the experiment name from `$ARGUMENTS`.

**Validation:**
- If `$ARGUMENTS` is empty, show usage and exit:
  ```
  Error: Missing experiment name.
  
  Usage: /experiment-report <experiment name>
  
  Examples:
    /experiment-report New Recommender Model (NFRV) - V1
    /experiment-report service-fee-v3
  ```

Store the full argument string as `$EXPERIMENT_NAME`.

---

## Step 2: Generate Experiment Report

Run the Python script to fetch experiment data and generate the report:

```bash
python scripts/amplitude_experiments_client.py generate-report "$EXPERIMENT_NAME"
```

**IMPORTANT:** Always use the Python script directly. Never use the MCP Amplitude tools (they are unreliable).

**Store the JSON output as `$REPORT_RESULT`.**

---

## Step 3: Handle Result

### Case A: Error - No experiment found

If `$REPORT_RESULT` contains `"error": "No experiments matched identifier"`:

```
Error: No experiment found matching "$EXPERIMENT_NAME"

Try:
- Check the exact name in Amplitude
- Use the experiment key (e.g., "nfrv1", "bob-v2")
- Search for experiments:
  python scripts/amplitude_experiments_client.py experiment-search "<partial name>"
```

Exit the command.

### Case B: Success

Parse the JSON output:
- `experiment_id` - Amplitude experiment ID
- `experiment_key` - Short key (e.g., "nfrv1")
- `experiment_name` - Full name
- `state` - Current state (running, decision-made, etc.)
- `project` - Inferred project name or "unassigned"
- `project_inferred` - Boolean, true if project was auto-detected
- `file_path` - Where the report was saved
- `matches_count` - Number of matching experiments

---

## Step 4: Display Experiment Details

Show the experiment details to the user:

```
══════════════════════════════════════════════════════════════════
EXPERIMENT REPORT
══════════════════════════════════════════════════════════════════

Experiment: $experiment_name
Key:        $experiment_key
ID:         $experiment_id
State:      $state

Project:    $project [if project_inferred: "(auto-detected)" else: ""]

══════════════════════════════════════════════════════════════════
```

---

## Step 5: Read and Display Report Summary

Read the generated report file to show key details:

```bash
cat $file_path
```

Extract and display from the report:
- **Type** (a-b-test, feature-flag, etc.)
- **Evaluation Mode** (remote, local)
- **Rollout %**
- **Variants** (list of variant keys)
- **Timeline** (created, started, ended dates)
- **Tags**

Display as:
```
Details:
  Type:       [experimentType]
  Eval Mode:  [evaluationMode]
  Rollout:    [rolloutPercentage]%
  Variants:   [variant1], [variant2], ...
  
Timeline:
  Created:    [createdAt]
  Started:    [startDate]
  Ended:      [endDate]
  
Tags: [tag1], [tag2], ...
```

---

## Step 6: Final Summary

```
══════════════════════════════════════════════════════════════════
✓ Report saved successfully!
══════════════════════════════════════════════════════════════════

File: $file_path

[if project == "unassigned"]
Note: Could not auto-detect project. Report saved to reports/experiments/.
To associate with a project, move the file to:
  project_management/<project_name>/experiments/
[endif]

[if matches_count > 1]
Note: Found $matches_count experiments matching "$EXPERIMENT_NAME".
Used the first match. Other matches may exist.
[endif]
```

---

## Error Handling

### Python Script Not Found
```
Error: Amplitude script not found at scripts/amplitude_experiments_client.py

Please ensure you're running this command from the repository root.
```

### API Authentication Error
```
Error: Amplitude API authentication failed.

Please check your .env file contains:
- AMPLITUDE_MANAGEMENT_API_KEY (or AMPLITUDE_EXPERIMENT_TOKEN)

For chart data, also ensure:
- AMPLITUDE_API_KEY_EU
- AMPLITUDE_SECRET_KEY_EU
```

### Network Error
```
Error: Failed to connect to Amplitude API.

Please check:
- Network connectivity
- Amplitude EU endpoints are accessible
```

---

## Notes

- This command uses the local Python script (`scripts/amplitude_experiments_client.py`), NOT the MCP Amplitude tools
- The script automatically infers the project based on experiment name, key, and tags
- If project inference fails, the report is saved to `reports/experiments/` instead
- Reports are saved as markdown with YAML frontmatter for easy parsing
- The filename format is: `<experiment_key>_<YYYY-MM-DD>.md`
