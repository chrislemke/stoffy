---
description: Generate a comprehensive deep-dive report for SageMaker endpoints with Plotly visualizations
agent: report_assistant
subtask: true
---

# SageMaker Endpoint Report Generator

This command generates a detailed analytical report on the status, configuration, and performance of SageMaker endpoints using a Python script with boto3.

## Instructions

1. Run the SageMaker report script:

```bash
python scripts/sagemaker_report.py --days 7
```

2. The script will:
   - Connect to AWS SageMaker (eu-central-1) via boto3
   - Fetch all endpoint configurations
   - Collect CloudWatch metrics (hourly granularity, last 7 days)
   - Classify endpoints (new, unused/ghost, error-prone, high-latency, high-traffic)
   - Generate Plotly visualizations (HTML files)
   - Create a comprehensive markdown report

3. Output location: `reports/sagemaker/<YYYY-MM-DD_HH-MM-SS>/`
   - `report.md` - Full markdown report
   - `latency_trends.html` - Interactive latency chart
   - `traffic_volume.html` - Invocations over time
   - `error_analysis.html` - 4XX/5XX error trends
   - `data.json` - Raw data for reference

4. After the script completes, provide a brief summary of the key findings to the user, highlighting:
   - Total endpoint count and health status
   - Any unused (ghost) endpoints that could be deleted
   - Endpoints with high error rates or latency issues
   - Traffic leaders

## Prerequisites

- AWS SSO authentication must be active (`aws sso login`)
- boto3 and plotly packages installed (included in environment.yml)

## Script Options

```
--days N       Number of days to look back (default: 7)
--output-dir   Custom output directory (default: reports/sagemaker/<timestamp>)
```
