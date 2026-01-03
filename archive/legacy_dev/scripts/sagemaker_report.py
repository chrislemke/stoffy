#!/usr/bin/env python3
"""
SageMaker Endpoint Report Generator

Collects endpoint configurations and CloudWatch metrics via boto3,
generates Plotly visualizations and a comprehensive markdown report.

This script replaces the MCP-based approach for significantly improved
token efficiency and faster execution.

Usage:
    python scripts/sagemaker_report.py [--days N] [--output-dir DIR] [--pretty]

Prerequisites:
    - AWS SSO authentication configured and logged in
    - boto3, plotly packages installed
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import plotly.graph_objects as go

# Configuration
AWS_REGION = "eu-central-1"
METRICS_NAMESPACE = "AWS/SageMaker"
METRICS_PERIOD_SECONDS = 3600  # Hourly granularity


@dataclass
class EndpointMetrics:
    """Container for CloudWatch metrics data."""

    timestamps: list[datetime] = field(default_factory=list)
    invocations: list[float] = field(default_factory=list)
    latency_avg: list[float] = field(default_factory=list)
    latency_p95: list[float] = field(default_factory=list)
    latency_max: list[float] = field(default_factory=list)
    errors_4xx: list[float] = field(default_factory=list)
    errors_5xx: list[float] = field(default_factory=list)
    disk_utilization: list[float] = field(default_factory=list)
    memory_utilization: list[float] = field(default_factory=list)

    @property
    def total_invocations(self) -> float:
        return sum(self.invocations)

    @property
    def total_4xx_errors(self) -> float:
        return sum(self.errors_4xx)

    @property
    def total_5xx_errors(self) -> float:
        return sum(self.errors_5xx)

    @property
    def total_errors(self) -> float:
        return self.total_4xx_errors + self.total_5xx_errors

    @property
    def error_rate(self) -> float:
        if self.total_invocations == 0:
            return 0.0
        return (self.total_errors / self.total_invocations) * 100

    @property
    def avg_latency(self) -> float:
        if not self.latency_avg:
            return 0.0
        valid = [x for x in self.latency_avg if x > 0]
        return sum(valid) / len(valid) if valid else 0.0

    @property
    def max_latency(self) -> float:
        if not self.latency_max:
            return 0.0
        return max(self.latency_max) if self.latency_max else 0.0

    @property
    def p95_latency(self) -> float:
        if not self.latency_p95:
            return 0.0
        valid = [x for x in self.latency_p95 if x > 0]
        return max(valid) if valid else 0.0


@dataclass
class EndpointData:
    """Complete data for a single SageMaker endpoint."""

    name: str
    arn: str
    status: str
    creation_time: datetime
    last_modified_time: datetime
    failure_reason: str | None
    variants: list[dict[str, Any]]
    metrics: EndpointMetrics
    tags: list[str] = field(default_factory=list)

    @property
    def is_new(self) -> bool:
        """Created within last 7 days."""
        return (datetime.now(UTC) - self.creation_time).days < 7

    @property
    def is_ghost(self) -> bool:
        """InService but no traffic in 7 days."""
        return self.status == "InService" and self.metrics.total_invocations == 0

    @property
    def is_error_prone(self) -> bool:
        """Error rate > 1%."""
        return self.metrics.error_rate > 1.0

    @property
    def has_latency_issues(self) -> bool:
        """Max latency > 2000ms."""
        return self.metrics.max_latency > 2000

    @property
    def primary_variant(self) -> dict[str, Any] | None:
        """Get the primary production variant."""
        if not self.variants:
            return None
        return self.variants[0]

    @property
    def instance_type(self) -> str:
        """Get instance type from primary variant."""
        variant = self.primary_variant
        if variant:
            return variant.get("InstanceType", "Unknown")
        return "Unknown"

    @property
    def instance_count(self) -> int:
        """Get instance count from primary variant."""
        variant = self.primary_variant
        if variant:
            return variant.get("CurrentInstanceCount", 0)
        return 0

    def get_status_icon(self) -> str:
        """Get appropriate status icon."""
        if self.status == "InService":
            return "✅"
        elif self.status == "Creating":
            return "🔄"
        elif self.status == "Updating":
            return "🔄"
        elif self.status == "Failed":
            return "❌"
        elif self.status == "Deleting":
            return "🗑️"
        return "⚪"


def get_sagemaker_client() -> Any:
    """Create boto3 SageMaker client for eu-central-1."""
    try:
        return boto3.client("sagemaker", region_name=AWS_REGION)
    except NoCredentialsError:
        print(
            "Error: AWS credentials not found. "
            "Please authenticate via 'aws sso login'.",
            file=sys.stderr,
        )
        sys.exit(1)


def get_cloudwatch_client() -> Any:
    """Create boto3 CloudWatch client for eu-central-1."""
    try:
        return boto3.client("cloudwatch", region_name=AWS_REGION)
    except NoCredentialsError:
        print(
            "Error: AWS credentials not found. "
            "Please authenticate via 'aws sso login'.",
            file=sys.stderr,
        )
        sys.exit(1)


def list_endpoints(sagemaker_client: Any) -> list[dict[str, Any]]:
    """Fetch all SageMaker endpoints."""
    endpoints = []
    paginator = sagemaker_client.get_paginator("list_endpoints")

    try:
        for page in paginator.paginate():
            endpoints.extend(page.get("Endpoints", []))
    except ClientError as e:
        print(f"Error listing endpoints: {e}", file=sys.stderr)
        return []

    return endpoints


def describe_endpoint(sagemaker_client: Any, endpoint_name: str) -> dict[str, Any]:
    """Get detailed configuration for an endpoint."""
    try:
        return sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
    except ClientError as e:
        print(f"Error describing endpoint {endpoint_name}: {e}", file=sys.stderr)
        return {}


def get_endpoint_metrics(
    cloudwatch_client: Any,
    endpoint_name: str,
    variant_name: str,
    days: int = 7,
) -> EndpointMetrics:
    """Fetch CloudWatch metrics for an endpoint variant with hourly granularity."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)

    metrics = EndpointMetrics()

    # Define the metrics to fetch
    metric_queries = [
        {
            "Id": "invocations",
            "MetricStat": {
                "Metric": {
                    "Namespace": METRICS_NAMESPACE,
                    "MetricName": "Invocations",
                    "Dimensions": [
                        {"Name": "EndpointName", "Value": endpoint_name},
                        {"Name": "VariantName", "Value": variant_name},
                    ],
                },
                "Period": METRICS_PERIOD_SECONDS,
                "Stat": "Sum",
            },
            "ReturnData": True,
        },
        {
            "Id": "latency_avg",
            "MetricStat": {
                "Metric": {
                    "Namespace": METRICS_NAMESPACE,
                    "MetricName": "ModelLatency",
                    "Dimensions": [
                        {"Name": "EndpointName", "Value": endpoint_name},
                        {"Name": "VariantName", "Value": variant_name},
                    ],
                },
                "Period": METRICS_PERIOD_SECONDS,
                "Stat": "Average",
            },
            "ReturnData": True,
        },
        {
            "Id": "latency_p95",
            "MetricStat": {
                "Metric": {
                    "Namespace": METRICS_NAMESPACE,
                    "MetricName": "ModelLatency",
                    "Dimensions": [
                        {"Name": "EndpointName", "Value": endpoint_name},
                        {"Name": "VariantName", "Value": variant_name},
                    ],
                },
                "Period": METRICS_PERIOD_SECONDS,
                "Stat": "p95",
            },
            "ReturnData": True,
        },
        {
            "Id": "latency_max",
            "MetricStat": {
                "Metric": {
                    "Namespace": METRICS_NAMESPACE,
                    "MetricName": "ModelLatency",
                    "Dimensions": [
                        {"Name": "EndpointName", "Value": endpoint_name},
                        {"Name": "VariantName", "Value": variant_name},
                    ],
                },
                "Period": METRICS_PERIOD_SECONDS,
                "Stat": "Maximum",
            },
            "ReturnData": True,
        },
        {
            "Id": "errors_4xx",
            "MetricStat": {
                "Metric": {
                    "Namespace": METRICS_NAMESPACE,
                    "MetricName": "Invocation4XXErrors",
                    "Dimensions": [
                        {"Name": "EndpointName", "Value": endpoint_name},
                        {"Name": "VariantName", "Value": variant_name},
                    ],
                },
                "Period": METRICS_PERIOD_SECONDS,
                "Stat": "Sum",
            },
            "ReturnData": True,
        },
        {
            "Id": "errors_5xx",
            "MetricStat": {
                "Metric": {
                    "Namespace": METRICS_NAMESPACE,
                    "MetricName": "Invocation5XXErrors",
                    "Dimensions": [
                        {"Name": "EndpointName", "Value": endpoint_name},
                        {"Name": "VariantName", "Value": variant_name},
                    ],
                },
                "Period": METRICS_PERIOD_SECONDS,
                "Stat": "Sum",
            },
            "ReturnData": True,
        },
        {
            "Id": "disk_util",
            "MetricStat": {
                "Metric": {
                    "Namespace": "/aws/sagemaker/Endpoints",
                    "MetricName": "DiskUtilization",
                    "Dimensions": [
                        {"Name": "EndpointName", "Value": endpoint_name},
                        {"Name": "VariantName", "Value": variant_name},
                    ],
                },
                "Period": METRICS_PERIOD_SECONDS,
                "Stat": "Average",
            },
            "ReturnData": True,
        },
        {
            "Id": "memory_util",
            "MetricStat": {
                "Metric": {
                    "Namespace": "/aws/sagemaker/Endpoints",
                    "MetricName": "MemoryUtilization",
                    "Dimensions": [
                        {"Name": "EndpointName", "Value": endpoint_name},
                        {"Name": "VariantName", "Value": variant_name},
                    ],
                },
                "Period": METRICS_PERIOD_SECONDS,
                "Stat": "Average",
            },
            "ReturnData": True,
        },
    ]

    try:
        response = cloudwatch_client.get_metric_data(
            MetricDataQueries=metric_queries,
            StartTime=start_time,
            EndTime=end_time,
            ScanBy="TimestampAscending",
        )

        # Process results
        for result in response.get("MetricDataResults", []):
            metric_id = result["Id"]
            timestamps = result.get("Timestamps", [])
            values = result.get("Values", [])

            # Store timestamps from the first metric with data
            if timestamps and not metrics.timestamps:
                metrics.timestamps = timestamps

            if metric_id == "invocations":
                metrics.invocations = values
            elif metric_id == "latency_avg":
                # Convert from microseconds to milliseconds
                metrics.latency_avg = [v / 1000 for v in values]
            elif metric_id == "latency_p95":
                metrics.latency_p95 = [v / 1000 for v in values]
            elif metric_id == "latency_max":
                metrics.latency_max = [v / 1000 for v in values]
            elif metric_id == "errors_4xx":
                metrics.errors_4xx = values
            elif metric_id == "errors_5xx":
                metrics.errors_5xx = values
            elif metric_id == "disk_util":
                metrics.disk_utilization = values
            elif metric_id == "memory_util":
                metrics.memory_utilization = values

    except ClientError as e:
        print(
            f"Error fetching metrics for {endpoint_name}/{variant_name}: {e}",
            file=sys.stderr,
        )

    return metrics


def collect_endpoint_data(
    sagemaker_client: Any,
    cloudwatch_client: Any,
    endpoint_summary: dict[str, Any],
    days: int = 7,
) -> EndpointData | None:
    """Collect complete data for a single endpoint."""
    endpoint_name = endpoint_summary["EndpointName"]

    # Get detailed endpoint info
    details = describe_endpoint(sagemaker_client, endpoint_name)
    if not details:
        return None

    # Extract variant information
    variants = []
    for variant in details.get("ProductionVariants", []):
        variants.append(
            {
                "VariantName": variant.get("VariantName", ""),
                "InstanceType": variant.get("CurrentInstanceCount", 0)
                and variant.get("InstanceType", "Unknown"),
                "CurrentInstanceCount": variant.get("CurrentInstanceCount", 0),
                "DesiredInstanceCount": variant.get("DesiredInstanceCount", 0),
                "CurrentWeight": variant.get("CurrentWeight", 0),
            }
        )

    # Also check deployment config for instance type
    for variant in details.get("ProductionVariants", []):
        for v in variants:
            if v["VariantName"] == variant.get("VariantName"):
                if "InstanceType" not in variant:
                    # Try to get from deployed images
                    deployed = variant.get("DeployedImages", [])
                    if deployed:
                        v["InstanceType"] = deployed[0].get(
                            "SpecifiedResolution", "Unknown"
                        )

    # Get the actual instance type from endpoint config
    try:
        config_name = details.get("EndpointConfigName", "")
        if config_name:
            config = sagemaker_client.describe_endpoint_config(
                EndpointConfigName=config_name
            )
            for pv in config.get("ProductionVariants", []):
                for v in variants:
                    if v["VariantName"] == pv.get("VariantName"):
                        v["InstanceType"] = pv.get("InstanceType", "Unknown")
    except ClientError:
        pass  # Config might not exist or be accessible

    # Get metrics for primary variant
    primary_variant_name = variants[0]["VariantName"] if variants else "AllTraffic"
    metrics = get_endpoint_metrics(
        cloudwatch_client, endpoint_name, primary_variant_name, days
    )

    # Build classification tags
    tags = []

    return EndpointData(
        name=endpoint_name,
        arn=details.get("EndpointArn", ""),
        status=details.get("EndpointStatus", "Unknown"),
        creation_time=details.get("CreationTime", datetime.now(UTC)),
        last_modified_time=details.get("LastModifiedTime", datetime.now(UTC)),
        failure_reason=details.get("FailureReason"),
        variants=variants,
        metrics=metrics,
        tags=tags,
    )


def classify_endpoints(
    endpoints: list[EndpointData],
) -> dict[str, list[EndpointData]]:
    """Classify endpoints into categories."""
    classifications = {
        "new": [],
        "ghost": [],
        "error_prone": [],
        "high_latency": [],
        "high_traffic": [],
        "healthy": [],
        "failed": [],
    }

    # Sort by invocations for high traffic detection
    sorted_by_traffic = sorted(
        [e for e in endpoints if e.status == "InService"],
        key=lambda x: x.metrics.total_invocations,
        reverse=True,
    )
    top_3_traffic = sorted_by_traffic[:3] if len(sorted_by_traffic) >= 3 else []

    for endpoint in endpoints:
        if endpoint.status == "Failed":
            classifications["failed"].append(endpoint)
            endpoint.tags.append("FAILED")
            continue

        if endpoint.is_new:
            classifications["new"].append(endpoint)
            endpoint.tags.append("NEW")

        if endpoint.is_ghost:
            classifications["ghost"].append(endpoint)
            endpoint.tags.append("UNUSED")

        if endpoint.is_error_prone:
            classifications["error_prone"].append(endpoint)
            endpoint.tags.append("ERROR_PRONE")

        if endpoint.has_latency_issues:
            classifications["high_latency"].append(endpoint)
            endpoint.tags.append("HIGH_LATENCY")

        if endpoint in top_3_traffic and endpoint.metrics.total_invocations > 0:
            classifications["high_traffic"].append(endpoint)
            endpoint.tags.append("HIGH_TRAFFIC")

        # If no issues, mark as healthy
        if (
            endpoint.status == "InService"
            and not endpoint.is_ghost
            and not endpoint.is_error_prone
            and not endpoint.has_latency_issues
        ):
            classifications["healthy"].append(endpoint)

    return classifications


def generate_latency_plot(endpoints: list[EndpointData], output_path: Path) -> None:
    """Generate latency trends plot."""
    fig = go.Figure()

    for endpoint in endpoints:
        if (
            endpoint.status != "InService"
            or not endpoint.metrics.timestamps
            or endpoint.metrics.total_invocations == 0
        ):
            continue

        # Average latency
        if endpoint.metrics.latency_avg:
            fig.add_trace(
                go.Scatter(
                    x=endpoint.metrics.timestamps,
                    y=endpoint.metrics.latency_avg,
                    mode="lines",
                    name=f"{endpoint.name} (Avg)",
                    line={"dash": "solid"},
                )
            )

        # P95 latency
        if endpoint.metrics.latency_p95:
            fig.add_trace(
                go.Scatter(
                    x=endpoint.metrics.timestamps,
                    y=endpoint.metrics.latency_p95,
                    mode="lines",
                    name=f"{endpoint.name} (p95)",
                    line={"dash": "dash"},
                )
            )

    fig.update_layout(
        title="SageMaker Endpoint Latency Trends (Last 7 Days)",
        xaxis_title="Time",
        yaxis_title="Latency (ms)",
        legend_title="Endpoint",
        hovermode="x unified",
        template="plotly_white",
    )

    fig.write_html(str(output_path))


def generate_traffic_plot(endpoints: list[EndpointData], output_path: Path) -> None:
    """Generate traffic volume plot."""
    fig = go.Figure()

    for endpoint in endpoints:
        if (
            endpoint.status != "InService"
            or not endpoint.metrics.timestamps
            or endpoint.metrics.total_invocations == 0
        ):
            continue

        fig.add_trace(
            go.Bar(
                x=endpoint.metrics.timestamps,
                y=endpoint.metrics.invocations,
                name=endpoint.name,
            )
        )

    fig.update_layout(
        title="SageMaker Endpoint Traffic Volume (Last 7 Days)",
        xaxis_title="Time",
        yaxis_title="Invocations",
        legend_title="Endpoint",
        barmode="group",
        hovermode="x unified",
        template="plotly_white",
    )

    fig.write_html(str(output_path))


def generate_error_plot(endpoints: list[EndpointData], output_path: Path) -> None:
    """Generate error analysis plot."""
    fig = go.Figure()

    has_errors = False

    for endpoint in endpoints:
        if endpoint.status != "InService" or not endpoint.metrics.timestamps:
            continue

        # 4XX errors
        if endpoint.metrics.errors_4xx and sum(endpoint.metrics.errors_4xx) > 0:
            has_errors = True
            fig.add_trace(
                go.Scatter(
                    x=endpoint.metrics.timestamps,
                    y=endpoint.metrics.errors_4xx,
                    mode="lines+markers",
                    name=f"{endpoint.name} (4XX)",
                    line={"color": "orange"},
                )
            )

        # 5XX errors
        if endpoint.metrics.errors_5xx and sum(endpoint.metrics.errors_5xx) > 0:
            has_errors = True
            fig.add_trace(
                go.Scatter(
                    x=endpoint.metrics.timestamps,
                    y=endpoint.metrics.errors_5xx,
                    mode="lines+markers",
                    name=f"{endpoint.name} (5XX)",
                    line={"color": "red"},
                )
            )

    if not has_errors:
        # Add annotation if no errors
        fig.add_annotation(
            text="No errors recorded in the last 7 days",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 16},
        )

    fig.update_layout(
        title="SageMaker Endpoint Error Analysis (Last 7 Days)",
        xaxis_title="Time",
        yaxis_title="Error Count",
        legend_title="Endpoint / Error Type",
        hovermode="x unified",
        template="plotly_white",
    )

    fig.write_html(str(output_path))


def generate_markdown_report(
    endpoints: list[EndpointData],
    classifications: dict[str, list[EndpointData]],
    output_path: Path,
    days: int,
) -> None:
    """Generate comprehensive markdown report."""
    now = datetime.now(UTC)
    date_str = now.strftime("%Y-%m-%d")

    # Count statuses
    in_service = sum(1 for e in endpoints if e.status == "InService")
    failed = sum(1 for e in endpoints if e.status == "Failed")
    other = len(endpoints) - in_service - failed

    # Build report
    lines = [
        f"# SageMaker Ecosystem Report: {date_str}",
        "",
        "## Executive Summary",
        "",
        f"* **Total Endpoints**: {len(endpoints)}",
        f"* **Health Status**: {in_service} Healthy, {other} Degraded, {failed} Failed",
        "* **Highlights**:",
        f"    * **New**: {len(classifications['new'])} endpoints created in the last {days} days.",
        f"    * **Unused**: {len(classifications['ghost'])} endpoints with zero traffic.",
        f"    * **Critical**: {len(classifications['error_prone'])} endpoints with errors > 1%.",
        "",
        "## Visualizations",
        "",
        "Interactive plots are available in this directory:",
        "",
        "* [Latency Trends](./latency_trends.html)",
        "* [Traffic Volume](./traffic_volume.html)",
        "* [Error Analysis](./error_analysis.html)",
        "",
    ]

    # Traffic leaders
    if classifications["high_traffic"]:
        lines.extend(
            [
                "## Traffic Leaders",
                "",
            ]
        )
        for i, endpoint in enumerate(classifications["high_traffic"][:3], 1):
            lines.append(
                f"{i}. **{endpoint.name}** - "
                f"{endpoint.metrics.total_invocations:,.0f} invocations, "
                f"{endpoint.instance_type}"
            )
        lines.append("")

    # Detailed analysis
    lines.extend(
        [
            "## Detailed Endpoint Analysis",
            "",
        ]
    )

    for endpoint in sorted(endpoints, key=lambda x: x.name):
        status_icon = endpoint.get_status_icon()
        tags_str = ", ".join(f"`[{t}]`" for t in endpoint.tags) if endpoint.tags else ""

        lines.extend(
            [
                f"### {endpoint.name} {status_icon}",
                "",
            ]
        )

        if tags_str:
            lines.append(f"* **Tags**: {tags_str}")

        # Configuration
        days_ago = (now - endpoint.creation_time).days
        created_str = endpoint.creation_time.strftime("%Y-%m-%d %H:%M UTC")

        lines.extend(
            [
                "* **Configuration**:",
                f"    * **Created**: {created_str} ({days_ago} days ago)",
                f"    * **Instance**: {endpoint.instance_type} x {endpoint.instance_count}",
            ]
        )

        if endpoint.variants:
            lines.append(f"    * **Variant**: {endpoint.variants[0]['VariantName']}")

        # Performance metrics
        lines.extend(
            [
                f"* **Performance (Last {days} Days)**:",
                f"    * **Traffic**: {endpoint.metrics.total_invocations:,.0f} invocations",
                f"    * **Latency**: Avg: {endpoint.metrics.avg_latency:.1f}ms | Max: {endpoint.metrics.max_latency:.1f}ms",
                "    * **Reliability**:",
                f"        * 4XX Errors: {endpoint.metrics.total_4xx_errors:,.0f}",
                f"        * 5XX Errors: {endpoint.metrics.total_5xx_errors:,.0f}",
                f"        * Error Rate: {endpoint.metrics.error_rate:.2f}%",
            ]
        )

        # Assessment
        assessment = generate_assessment(endpoint)
        lines.extend(
            [
                "* **Assessment**:",
                f"    * {assessment}",
                "",
                "---",
                "",
            ]
        )

    # Write report
    output_path.write_text("\n".join(lines))


def generate_assessment(endpoint: EndpointData) -> str:
    """Generate a brief assessment for an endpoint."""
    if endpoint.status == "Failed":
        reason = endpoint.failure_reason or "Unknown reason"
        return f"Endpoint failed: {reason}. Investigate and recreate if needed."

    if endpoint.is_ghost:
        return (
            "No traffic observed in the monitoring period. "
            "Consider scaling down or deleting to reduce costs."
        )

    if endpoint.is_error_prone and endpoint.has_latency_issues:
        return (
            "High error rate and latency issues detected. "
            "Urgent investigation recommended - check model performance and instance sizing."
        )

    if endpoint.is_error_prone:
        return (
            "Elevated error rate detected. "
            "Review CloudWatch logs and model behavior for root cause."
        )

    if endpoint.has_latency_issues:
        return (
            "Latency spikes detected. "
            "Consider scaling up instance type or adding more instances."
        )

    if endpoint.is_new:
        return (
            "Recently deployed endpoint. "
            "Monitor closely for the first few days to establish baseline metrics."
        )

    if endpoint.metrics.total_invocations > 10000:
        return "High-traffic endpoint with stable performance. Continue monitoring."

    return "Stable performance with acceptable latency and error rates."


def save_raw_data(endpoints: list[EndpointData], output_path: Path) -> None:
    """Save raw data as JSON for debugging/reference."""
    data = []
    for endpoint in endpoints:
        data.append(
            {
                "name": endpoint.name,
                "arn": endpoint.arn,
                "status": endpoint.status,
                "creation_time": endpoint.creation_time.isoformat(),
                "last_modified_time": endpoint.last_modified_time.isoformat(),
                "failure_reason": endpoint.failure_reason,
                "variants": endpoint.variants,
                "tags": endpoint.tags,
                "metrics": {
                    "total_invocations": endpoint.metrics.total_invocations,
                    "total_4xx_errors": endpoint.metrics.total_4xx_errors,
                    "total_5xx_errors": endpoint.metrics.total_5xx_errors,
                    "error_rate": endpoint.metrics.error_rate,
                    "avg_latency_ms": endpoint.metrics.avg_latency,
                    "max_latency_ms": endpoint.metrics.max_latency,
                    "p95_latency_ms": endpoint.metrics.p95_latency,
                },
            }
        )

    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def generate_report(days: int = 7, output_dir: str | None = None) -> Path:
    """Generate the complete SageMaker report."""
    # Create output directory
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

    if output_dir:
        report_dir = Path(output_dir)
    else:
        report_dir = Path("reports/sagemaker") / timestamp

    report_dir.mkdir(parents=True, exist_ok=True)

    print(f"Initializing AWS clients for {AWS_REGION}...", file=sys.stderr)
    sagemaker_client = get_sagemaker_client()
    cloudwatch_client = get_cloudwatch_client()

    print("Fetching SageMaker endpoints...", file=sys.stderr)
    endpoint_list = list_endpoints(sagemaker_client)
    print(f"Found {len(endpoint_list)} endpoints", file=sys.stderr)

    if not endpoint_list:
        print("No endpoints found. Creating empty report.", file=sys.stderr)
        # Create minimal report
        (report_dir / "report.md").write_text(
            f"# SageMaker Ecosystem Report: {now.strftime('%Y-%m-%d')}\n\n"
            "## Executive Summary\n\n"
            "* **Total Endpoints**: 0\n\n"
            "No SageMaker endpoints found in eu-central-1.\n"
        )
        return report_dir

    # Collect data for each endpoint
    endpoints: list[EndpointData] = []
    for i, ep_summary in enumerate(endpoint_list, 1):
        name = ep_summary["EndpointName"]
        print(f"Processing [{i}/{len(endpoint_list)}] {name}...", file=sys.stderr)

        endpoint_data = collect_endpoint_data(
            sagemaker_client, cloudwatch_client, ep_summary, days
        )
        if endpoint_data:
            endpoints.append(endpoint_data)

    # Classify endpoints
    print("Classifying endpoints...", file=sys.stderr)
    classifications = classify_endpoints(endpoints)

    # Generate visualizations
    print("Generating visualizations...", file=sys.stderr)
    generate_latency_plot(endpoints, report_dir / "latency_trends.html")
    generate_traffic_plot(endpoints, report_dir / "traffic_volume.html")
    generate_error_plot(endpoints, report_dir / "error_analysis.html")

    # Generate markdown report
    print("Generating markdown report...", file=sys.stderr)
    generate_markdown_report(endpoints, classifications, report_dir / "report.md", days)

    # Save raw data
    save_raw_data(endpoints, report_dir / "data.json")

    return report_dir


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate SageMaker endpoint report with visualizations"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for metrics (default: 7)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        help="Output directory (default: reports/sagemaker/<timestamp>)",
    )
    args = parser.parse_args()

    report_dir = generate_report(days=args.days, output_dir=args.output_dir)
    print(f"\nReport generated: {report_dir}", file=sys.stderr)
    print(f"  - {report_dir / 'report.md'}")
    print(f"  - {report_dir / 'latency_trends.html'}")
    print(f"  - {report_dir / 'traffic_volume.html'}")
    print(f"  - {report_dir / 'error_analysis.html'}")
    print(f"  - {report_dir / 'data.json'}")


if __name__ == "__main__":
    main()
