#!/usr/bin/env python3
"""
SageMaker Infrastructure Report Generator

Traces the full ML inference infrastructure chain:
API Gateway -> Lambda (with ENDPOINT_NAME) -> SageMaker Endpoint -> Config -> Model

Collects:
- All API Gateways (REST and HTTP) with URLs and masked API keys
- Lambda functions with ENDPOINT_NAME environment variable
- SageMaker endpoints, configs, models
- Autoscaling policies and instance details

Usage:
    python scripts/sagemaker_infra_report.py [--region REGION] [--output-dir DIR]

Prerequisites:
    - AWS SSO authentication configured and logged in
    - boto3 package installed
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

import boto3
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    UnauthorizedSSOTokenError,
)

# Configuration
DEFAULT_REGION = "eu-central-1"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class APIKeyInfo:
    """API Key with masked value."""

    name: str
    key_id: str
    masked_value: str


@dataclass
class LambdaIntegration:
    """Lambda function integrated with an API Gateway."""

    function_name: str
    function_arn: str
    resource_path: str
    http_method: str


@dataclass
class APIGatewayInfo:
    """API Gateway information."""

    api_id: str
    name: str
    api_type: str  # "REST" or "HTTP"
    endpoint_url: str
    api_keys: list[APIKeyInfo] = field(default_factory=list)
    lambda_integrations: list[LambdaIntegration] = field(default_factory=list)


@dataclass
class LambdaInfo:
    """Lambda function with ENDPOINT_NAME."""

    name: str
    arn: str
    runtime: str
    endpoint_name: str  # Value of ENDPOINT_NAME env var
    memory_size: int
    timeout: int
    triggered_by_apis: list[str] = field(default_factory=list)  # API Gateway names


@dataclass
class ModelInfo:
    """SageMaker model information."""

    name: str
    arn: str
    container_image: str
    model_data_url: str
    creation_time: datetime


@dataclass
class VariantInfo:
    """Production variant information."""

    name: str
    instance_type: str
    initial_instance_count: int
    current_instance_count: int
    model_name: str


@dataclass
class AutoscalingPolicy:
    """Autoscaling policy details."""

    policy_name: str
    policy_type: str
    target_value: float | None = None
    metric_name: str | None = None
    scale_in_cooldown: int | None = None
    scale_out_cooldown: int | None = None


@dataclass
class AutoscalingInfo:
    """Complete autoscaling configuration."""

    min_capacity: int
    max_capacity: int
    policies: list[AutoscalingPolicy] = field(default_factory=list)


@dataclass
class EndpointConfigInfo:
    """SageMaker endpoint configuration."""

    name: str
    arn: str
    creation_time: datetime
    variants: list[VariantInfo] = field(default_factory=list)


@dataclass
class SageMakerEndpointInfo:
    """Complete SageMaker endpoint information."""

    name: str
    arn: str
    status: str
    creation_time: datetime
    last_modified_time: datetime
    config: EndpointConfigInfo | None = None
    models: list[ModelInfo] = field(default_factory=list)
    autoscaling: AutoscalingInfo | None = None


@dataclass
class InfrastructureChain:
    """Complete trace from API Gateway to SageMaker Model."""

    api_gateway: APIGatewayInfo
    lambda_function: LambdaInfo
    sagemaker_endpoint: SageMakerEndpointInfo


# =============================================================================
# AWS Client Helpers
# =============================================================================


def get_client(service: str, region: str) -> Any:
    """Create boto3 client for a service."""
    try:
        client = boto3.client(service, region_name=region)
        # Test the client with a simple operation to catch SSO token errors early
        # We do this by accessing the credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            credentials.get_frozen_credentials()
        return client
    except NoCredentialsError:
        print(
            "Error: AWS credentials not found. "
            "Please authenticate via 'aws sso login'.",
            file=sys.stderr,
        )
        sys.exit(1)
    except UnauthorizedSSOTokenError:
        print(
            "Error: AWS SSO session has expired. "
            "Please run 'aws sso login' to refresh your session.",
            file=sys.stderr,
        )
        sys.exit(1)


def mask_api_key(key_value: str) -> str:
    """Mask API key showing only first 2 and last 2 characters."""
    if not key_value or len(key_value) <= 4:
        return "****"
    return f"{key_value[:2]}{'*' * (len(key_value) - 4)}{key_value[-2:]}"


def extract_lambda_name_from_arn(arn: str) -> str:
    """Extract Lambda function name from ARN."""
    # arn:aws:lambda:region:account:function:name
    match = re.search(r":function:([^:/]+)", arn)
    return match.group(1) if match else arn


def extract_lambda_name_from_uri(uri: str) -> str:
    """Extract Lambda function name from integration URI."""
    # arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:name/invocations
    match = re.search(r":function:([^:/]+)", uri)
    return match.group(1) if match else ""


# =============================================================================
# API Gateway Collection
# =============================================================================


def collect_rest_apis(region: str) -> list[APIGatewayInfo]:
    """Collect all REST API Gateways."""
    client = get_client("apigateway", region)
    apis: list[APIGatewayInfo] = []

    try:
        # List all REST APIs
        paginator = client.get_paginator("get_rest_apis")
        for page in paginator.paginate():
            for api in page.get("items", []):
                api_id = api["id"]
                api_name = api.get("name", "Unknown")

                # Build endpoint URL
                endpoint_url = f"https://{api_id}.execute-api.{region}.amazonaws.com"

                api_info = APIGatewayInfo(
                    api_id=api_id,
                    name=api_name,
                    api_type="REST",
                    endpoint_url=endpoint_url,
                )

                # Get Lambda integrations
                api_info.lambda_integrations = get_rest_api_lambda_integrations(
                    client, api_id
                )

                # Get API keys for this API
                api_info.api_keys = get_rest_api_keys(client, api_id)

                apis.append(api_info)

    except ClientError as e:
        print(f"Error listing REST APIs: {e}", file=sys.stderr)
    except UnauthorizedSSOTokenError:
        print(
            "Error: AWS SSO session has expired. "
            "Please run 'aws sso login' to refresh your session.",
            file=sys.stderr,
        )
        sys.exit(1)

    return apis


def get_rest_api_lambda_integrations(
    client: Any, api_id: str
) -> list[LambdaIntegration]:
    """Get Lambda integrations for a REST API."""
    integrations: list[LambdaIntegration] = []

    try:
        # Get all resources
        resources = []
        paginator = client.get_paginator("get_resources")
        for page in paginator.paginate(restApiId=api_id):
            resources.extend(page.get("items", []))

        # Check each resource for Lambda integrations
        for resource in resources:
            resource_id = resource["id"]
            resource_path = resource.get("path", "/")

            # Check each HTTP method
            for method_key in resource.get("resourceMethods", {}).keys():
                try:
                    method = client.get_method(
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod=method_key,
                    )

                    integration = method.get("methodIntegration", {})
                    integration_type = integration.get("type", "")
                    uri = integration.get("uri", "")

                    # Check if it's a Lambda integration
                    if integration_type in ("AWS", "AWS_PROXY") and "lambda" in uri:
                        function_name = extract_lambda_name_from_uri(uri)
                        if function_name:
                            # Extract full ARN from URI
                            arn_match = re.search(r"arn:aws:lambda:[^/]+", uri)
                            function_arn = arn_match.group(0) if arn_match else ""

                            integrations.append(
                                LambdaIntegration(
                                    function_name=function_name,
                                    function_arn=function_arn,
                                    resource_path=resource_path,
                                    http_method=method_key,
                                )
                            )

                except ClientError:
                    continue  # Method might not have integration

    except ClientError as e:
        print(f"Error getting integrations for REST API {api_id}: {e}", file=sys.stderr)

    return integrations


def get_rest_api_keys(client: Any, api_id: str) -> list[APIKeyInfo]:
    """Get API keys linked to a REST API through usage plans."""
    api_keys: list[APIKeyInfo] = []
    seen_key_ids: set[str] = set()

    try:
        # Get usage plans for this API
        usage_plans = []
        paginator = client.get_paginator("get_usage_plans")
        for page in paginator.paginate():
            for plan in page.get("items", []):
                # Check if this plan is associated with our API
                api_stages = plan.get("apiStages", [])
                if any(stage.get("apiId") == api_id for stage in api_stages):
                    usage_plans.append(plan)

        # Get API keys for each usage plan
        for plan in usage_plans:
            plan_id = plan["id"]
            key_paginator = client.get_paginator("get_usage_plan_keys")
            for page in key_paginator.paginate(usagePlanId=plan_id):
                for key_item in page.get("items", []):
                    key_id = key_item["id"]
                    if key_id in seen_key_ids:
                        continue
                    seen_key_ids.add(key_id)

                    # Get the actual key value
                    try:
                        key_detail = client.get_api_key(
                            apiKey=key_id, includeValue=True
                        )
                        key_value = key_detail.get("value", "")
                        api_keys.append(
                            APIKeyInfo(
                                name=key_detail.get("name", "Unknown"),
                                key_id=key_id,
                                masked_value=mask_api_key(key_value),
                            )
                        )
                    except ClientError:
                        api_keys.append(
                            APIKeyInfo(
                                name=key_item.get("name", "Unknown"),
                                key_id=key_id,
                                masked_value="****",
                            )
                        )

    except ClientError as e:
        print(f"Error getting API keys for REST API {api_id}: {e}", file=sys.stderr)

    return api_keys


def collect_http_apis(region: str) -> list[APIGatewayInfo]:
    """Collect all HTTP API Gateways."""
    client = get_client("apigatewayv2", region)
    apis: list[APIGatewayInfo] = []

    try:
        # List all HTTP APIs
        response = client.get_apis()
        for api in response.get("Items", []):
            # Only process HTTP APIs (not WebSocket)
            if api.get("ProtocolType") != "HTTP":
                continue

            api_id = api["ApiId"]
            api_name = api.get("Name", "Unknown")
            endpoint_url = api.get("ApiEndpoint", "")

            api_info = APIGatewayInfo(
                api_id=api_id,
                name=api_name,
                api_type="HTTP",
                endpoint_url=endpoint_url,
            )

            # Get Lambda integrations
            api_info.lambda_integrations = get_http_api_lambda_integrations(
                client, api_id
            )

            # HTTP APIs don't have traditional API keys like REST APIs
            # They use IAM, Lambda authorizers, or JWT authorizers

            apis.append(api_info)

    except ClientError as e:
        print(f"Error listing HTTP APIs: {e}", file=sys.stderr)

    return apis


def get_http_api_lambda_integrations(
    client: Any, api_id: str
) -> list[LambdaIntegration]:
    """Get Lambda integrations for an HTTP API."""
    integrations: list[LambdaIntegration] = []

    try:
        # Get all integrations
        integration_response = client.get_integrations(ApiId=api_id)
        integration_map: dict[str, LambdaIntegration] = {}

        for integration in integration_response.get("Items", []):
            integration_id = integration.get("IntegrationId", "")
            integration_type = integration.get("IntegrationType", "")
            uri = integration.get("IntegrationUri", "")

            # Check if it's a Lambda integration
            if integration_type == "AWS_PROXY" and "lambda" in uri.lower():
                function_name = extract_lambda_name_from_arn(uri)
                if function_name:
                    integration_map[integration_id] = LambdaIntegration(
                        function_name=function_name,
                        function_arn=uri,
                        resource_path="",  # Will be filled from routes
                        http_method="",
                    )

        # Get routes to map integrations to paths
        routes_response = client.get_routes(ApiId=api_id)
        for route in routes_response.get("Items", []):
            target = route.get("Target", "")
            route_key = route.get("RouteKey", "")

            # Target format: integrations/<integration_id>
            if target.startswith("integrations/"):
                integration_id = target.split("/")[1]
                if integration_id in integration_map:
                    # Parse route key (e.g., "POST /items" or "$default")
                    parts = route_key.split(" ", 1)
                    method = parts[0] if len(parts) > 0 else "ANY"
                    path = parts[1] if len(parts) > 1 else "/"

                    integration = integration_map[integration_id]
                    integrations.append(
                        LambdaIntegration(
                            function_name=integration.function_name,
                            function_arn=integration.function_arn,
                            resource_path=path,
                            http_method=method,
                        )
                    )

    except ClientError as e:
        print(f"Error getting integrations for HTTP API {api_id}: {e}", file=sys.stderr)

    return integrations


# =============================================================================
# Lambda Collection
# =============================================================================


def collect_lambdas_with_endpoint(region: str) -> list[LambdaInfo]:
    """Collect Lambda functions that have ENDPOINT_NAME environment variable."""
    client = get_client("lambda", region)
    lambdas: list[LambdaInfo] = []

    try:
        paginator = client.get_paginator("list_functions")
        for page in paginator.paginate():
            for func in page.get("Functions", []):
                env_vars = func.get("Environment", {}).get("Variables", {})
                endpoint_name = env_vars.get("ENDPOINT_NAME")

                if endpoint_name:
                    lambdas.append(
                        LambdaInfo(
                            name=func["FunctionName"],
                            arn=func["FunctionArn"],
                            runtime=func.get("Runtime", "Unknown"),
                            endpoint_name=endpoint_name,
                            memory_size=func.get("MemorySize", 0),
                            timeout=func.get("Timeout", 0),
                        )
                    )

    except ClientError as e:
        print(f"Error listing Lambda functions: {e}", file=sys.stderr)

    return lambdas


# =============================================================================
# SageMaker Collection
# =============================================================================


def collect_sagemaker_endpoint(
    region: str, endpoint_name: str
) -> SageMakerEndpointInfo | None:
    """Collect complete SageMaker endpoint information."""
    sm_client = get_client("sagemaker", region)
    as_client = get_client("application-autoscaling", region)

    try:
        # Describe endpoint
        endpoint = sm_client.describe_endpoint(EndpointName=endpoint_name)

        endpoint_info = SageMakerEndpointInfo(
            name=endpoint_name,
            arn=endpoint.get("EndpointArn", ""),
            status=endpoint.get("EndpointStatus", "Unknown"),
            creation_time=endpoint.get("CreationTime", datetime.now(UTC)),
            last_modified_time=endpoint.get("LastModifiedTime", datetime.now(UTC)),
        )

        # Get endpoint config
        config_name = endpoint.get("EndpointConfigName", "")
        if config_name:
            endpoint_info.config = get_endpoint_config(sm_client, config_name)

            # Get models from config
            if endpoint_info.config:
                for variant in endpoint_info.config.variants:
                    model = get_model_info(sm_client, variant.model_name)
                    if model:
                        endpoint_info.models.append(model)

        # Get autoscaling info
        endpoint_info.autoscaling = get_autoscaling_info(
            as_client, endpoint_name, endpoint_info.config
        )

        return endpoint_info

    except ClientError as e:
        if "ValidationException" in str(e) or "Could not find" in str(e):
            print(
                f"Warning: SageMaker endpoint '{endpoint_name}' not found",
                file=sys.stderr,
            )
        else:
            print(f"Error describing endpoint {endpoint_name}: {e}", file=sys.stderr)
        return None


def get_endpoint_config(client: Any, config_name: str) -> EndpointConfigInfo | None:
    """Get endpoint configuration details."""
    try:
        config = client.describe_endpoint_config(EndpointConfigName=config_name)

        config_info = EndpointConfigInfo(
            name=config_name,
            arn=config.get("EndpointConfigArn", ""),
            creation_time=config.get("CreationTime", datetime.now(UTC)),
        )

        # Extract production variants
        for variant in config.get("ProductionVariants", []):
            config_info.variants.append(
                VariantInfo(
                    name=variant.get("VariantName", ""),
                    instance_type=variant.get("InstanceType", "Unknown"),
                    initial_instance_count=variant.get("InitialInstanceCount", 0),
                    current_instance_count=variant.get("InitialInstanceCount", 0),
                    model_name=variant.get("ModelName", ""),
                )
            )

        return config_info

    except ClientError as e:
        print(f"Error getting endpoint config {config_name}: {e}", file=sys.stderr)
        return None


def get_model_info(client: Any, model_name: str) -> ModelInfo | None:
    """Get SageMaker model information."""
    try:
        model = client.describe_model(ModelName=model_name)

        # Get primary container info
        primary_container = model.get("PrimaryContainer", {})
        if not primary_container:
            containers = model.get("Containers", [])
            primary_container = containers[0] if containers else {}

        return ModelInfo(
            name=model_name,
            arn=model.get("ModelArn", ""),
            container_image=primary_container.get("Image", "Unknown"),
            model_data_url=primary_container.get("ModelDataUrl", "N/A"),
            creation_time=model.get("CreationTime", datetime.now(UTC)),
        )

    except ClientError as e:
        print(f"Error getting model {model_name}: {e}", file=sys.stderr)
        return None


def get_autoscaling_info(
    client: Any, endpoint_name: str, config: EndpointConfigInfo | None
) -> AutoscalingInfo | None:
    """Get autoscaling configuration for an endpoint."""
    if not config or not config.variants:
        return None

    # Try to get autoscaling for the first variant
    variant_name = config.variants[0].name
    resource_id = f"endpoint/{endpoint_name}/variant/{variant_name}"

    try:
        # Get scalable targets
        targets_response = client.describe_scalable_targets(
            ServiceNamespace="sagemaker",
            ResourceIds=[resource_id],
        )

        targets = targets_response.get("ScalableTargets", [])
        if not targets:
            return None

        target = targets[0]
        autoscaling = AutoscalingInfo(
            min_capacity=target.get("MinCapacity", 0),
            max_capacity=target.get("MaxCapacity", 0),
        )

        # Get scaling policies
        policies_response = client.describe_scaling_policies(
            ServiceNamespace="sagemaker",
            ResourceId=resource_id,
        )

        for policy in policies_response.get("ScalingPolicies", []):
            policy_info = AutoscalingPolicy(
                policy_name=policy.get("PolicyName", ""),
                policy_type=policy.get("PolicyType", ""),
            )

            # Extract target tracking config if present
            target_tracking = policy.get("TargetTrackingScalingPolicyConfiguration", {})
            if target_tracking:
                policy_info.target_value = target_tracking.get("TargetValue")
                policy_info.scale_in_cooldown = target_tracking.get("ScaleInCooldown")
                policy_info.scale_out_cooldown = target_tracking.get("ScaleOutCooldown")

                # Get metric name
                predefined = target_tracking.get("PredefinedMetricSpecification", {})
                if predefined:
                    policy_info.metric_name = predefined.get("PredefinedMetricType")
                else:
                    custom = target_tracking.get("CustomizedMetricSpecification", {})
                    policy_info.metric_name = custom.get("MetricName", "Custom")

            autoscaling.policies.append(policy_info)

        return autoscaling

    except ClientError as e:
        # No autoscaling configured is not an error
        if "ObjectNotFoundException" not in str(e):
            print(
                f"Error getting autoscaling for {endpoint_name}: {e}", file=sys.stderr
            )
        return None


# =============================================================================
# Infrastructure Chain Building
# =============================================================================


def build_infrastructure_chains(
    api_gateways: list[APIGatewayInfo],
    lambdas: list[LambdaInfo],
    region: str,
) -> tuple[list[InfrastructureChain], list[LambdaInfo], list[str]]:
    """
    Build complete infrastructure chains and identify orphaned resources.

    Returns:
        - Complete infrastructure chains
        - Orphaned lambdas (have ENDPOINT_NAME but no API Gateway trigger)
        - Orphaned endpoint names (not traceable from any Lambda)
    """
    chains: list[InfrastructureChain] = []

    # Build lookup: lambda_name -> LambdaInfo
    lambda_lookup: dict[str, LambdaInfo] = {l.name: l for l in lambdas}

    # Track which lambdas are connected
    connected_lambda_names: set[str] = set()

    # Track which endpoints we've collected
    collected_endpoints: dict[str, SageMakerEndpointInfo] = {}

    # Process each API Gateway
    for api in api_gateways:
        for integration in api.lambda_integrations:
            lambda_name = integration.function_name

            # Check if this Lambda has ENDPOINT_NAME
            if lambda_name in lambda_lookup:
                lambda_info = lambda_lookup[lambda_name]
                connected_lambda_names.add(lambda_name)

                # Track API Gateway triggers
                if api.name not in lambda_info.triggered_by_apis:
                    lambda_info.triggered_by_apis.append(api.name)

                # Get or collect SageMaker endpoint
                endpoint_name = lambda_info.endpoint_name
                if endpoint_name not in collected_endpoints:
                    endpoint_info = collect_sagemaker_endpoint(region, endpoint_name)
                    if endpoint_info:
                        collected_endpoints[endpoint_name] = endpoint_info

                # Create chain if we have the endpoint
                if endpoint_name in collected_endpoints:
                    chains.append(
                        InfrastructureChain(
                            api_gateway=api,
                            lambda_function=lambda_info,
                            sagemaker_endpoint=collected_endpoints[endpoint_name],
                        )
                    )

    # Find orphaned lambdas (have ENDPOINT_NAME but no API Gateway trigger)
    orphaned_lambdas = [l for l in lambdas if l.name not in connected_lambda_names]

    # Collect endpoints for orphaned lambdas too (for the report)
    orphaned_endpoint_names: list[str] = []
    for lambda_info in orphaned_lambdas:
        endpoint_name = lambda_info.endpoint_name
        if endpoint_name not in collected_endpoints:
            endpoint_info = collect_sagemaker_endpoint(region, endpoint_name)
            if endpoint_info:
                collected_endpoints[endpoint_name] = endpoint_info
            else:
                orphaned_endpoint_names.append(endpoint_name)

    return chains, orphaned_lambdas, orphaned_endpoint_names


# =============================================================================
# Report Generation
# =============================================================================


def generate_markdown_report(
    chains: list[InfrastructureChain],
    orphaned_lambdas: list[LambdaInfo],
    orphaned_endpoints: list[str],
    all_apis: list[APIGatewayInfo],
    region: str,
    output_path: Path,
) -> None:
    """Generate comprehensive markdown report."""
    now = datetime.now(UTC)
    date_str = now.strftime("%Y-%m-%d %H:%M UTC")

    # Count API types
    rest_count = sum(1 for api in all_apis if api.api_type == "REST")
    http_count = sum(1 for api in all_apis if api.api_type == "HTTP")

    # Count unique resources
    unique_lambdas = set()
    unique_endpoints = set()
    for chain in chains:
        unique_lambdas.add(chain.lambda_function.name)
        unique_endpoints.add(chain.sagemaker_endpoint.name)

    lines = [
        "# AWS ML Infrastructure Report",
        "",
        f"**Generated**: {date_str}  ",
        f"**Region**: {region}",
        "",
        "## Executive Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total API Gateways | {len(all_apis)} ({rest_count} REST, {http_count} HTTP) |",
        f"| API Gateways with ML Chain | {len(set(c.api_gateway.api_id for c in chains))} |",
        f"| Lambda Functions (with ENDPOINT_NAME) | {len(unique_lambdas)} |",
        f"| SageMaker Endpoints Traced | {len(unique_endpoints)} |",
        f"| Complete Infrastructure Chains | {len(chains)} |",
        f"| Orphaned Lambdas (no API trigger) | {len(orphaned_lambdas)} |",
        "",
    ]

    # Infrastructure Chains
    if chains:
        lines.extend(
            [
                "---",
                "",
                "## Infrastructure Chains",
                "",
            ]
        )

        # Group chains by API Gateway to avoid repetition
        chains_by_api: dict[str, list[InfrastructureChain]] = {}
        for chain in chains:
            api_id = chain.api_gateway.api_id
            if api_id not in chains_by_api:
                chains_by_api[api_id] = []
            chains_by_api[api_id].append(chain)

        chain_num = 0
        for api_id, api_chains in chains_by_api.items():
            api = api_chains[0].api_gateway
            chain_num += 1

            lines.extend(
                [
                    f"### Chain {chain_num}: {api.name}",
                    "",
                    "#### API Gateway",
                    "",
                    "| Property | Value |",
                    "|----------|-------|",
                    f"| **Type** | {api.api_type} |",
                    f"| **ID** | `{api.api_id}` |",
                    f"| **URL** | {api.endpoint_url} |",
                    "",
                ]
            )

            # API Keys
            if api.api_keys:
                lines.append("**API Keys**:")
                lines.append("")
                for key in api.api_keys:
                    lines.append(f"- `{key.name}`: `{key.masked_value}`")
                lines.append("")
            else:
                lines.append("**API Keys**: None configured")
                lines.append("")

            # Lambda integrations pointing to SageMaker
            lines.append("**Lambda Integrations**:")
            lines.append("")

            seen_lambdas: set[str] = set()
            for chain in api_chains:
                lambda_info = chain.lambda_function
                if lambda_info.name in seen_lambdas:
                    continue
                seen_lambdas.add(lambda_info.name)

                # Find the integration paths for this lambda
                paths = [
                    f"`{i.http_method} {i.resource_path}`"
                    for i in api.lambda_integrations
                    if i.function_name == lambda_info.name
                ]

                lines.extend(
                    [
                        f"##### Lambda: {lambda_info.name}",
                        "",
                        "| Property | Value |",
                        "|----------|-------|",
                        f"| **Runtime** | {lambda_info.runtime} |",
                        f"| **Memory** | {lambda_info.memory_size} MB |",
                        f"| **Timeout** | {lambda_info.timeout}s |",
                        f"| **Routes** | {', '.join(paths)} |",
                        f"| **ENDPOINT_NAME** | `{lambda_info.endpoint_name}` |",
                        "",
                    ]
                )

                # SageMaker Endpoint
                endpoint = chain.sagemaker_endpoint
                status_icon = "✅" if endpoint.status == "InService" else "⚠️"

                lines.extend(
                    [
                        f"###### SageMaker Endpoint: {endpoint.name} {status_icon}",
                        "",
                        "| Property | Value |",
                        "|----------|-------|",
                        f"| **Status** | {endpoint.status} |",
                        f"| **Created** | {endpoint.creation_time.strftime('%Y-%m-%d %H:%M UTC')} |",
                        f"| **Last Modified** | {endpoint.last_modified_time.strftime('%Y-%m-%d %H:%M UTC')} |",
                        "",
                    ]
                )

                # Endpoint Config
                if endpoint.config:
                    config = endpoint.config
                    lines.extend(
                        [
                            "**Endpoint Configuration**:",
                            "",
                            f"- **Config Name**: `{config.name}`",
                            f"- **Created**: {config.creation_time.strftime('%Y-%m-%d %H:%M UTC')}",
                            "",
                        ]
                    )

                    # Variants
                    if config.variants:
                        lines.append("**Production Variants**:")
                        lines.append("")
                        lines.append("| Variant | Instance Type | Count | Model |")
                        lines.append("|---------|---------------|-------|-------|")
                        for variant in config.variants:
                            lines.append(
                                f"| {variant.name} | `{variant.instance_type}` | "
                                f"{variant.initial_instance_count} | `{variant.model_name}` |"
                            )
                        lines.append("")

                # Models
                if endpoint.models:
                    lines.append("**Models**:")
                    lines.append("")
                    lines.append("| Model Name | Container Image | Data Location |")
                    lines.append("|------------|-----------------|---------------|")
                    for model in endpoint.models:
                        # Truncate long strings
                        image = (
                            model.container_image[:50] + "..."
                            if len(model.container_image) > 50
                            else model.container_image
                        )
                        data_url = (
                            model.model_data_url[:50] + "..."
                            if len(model.model_data_url) > 50
                            else model.model_data_url
                        )
                        lines.append(f"| `{model.name}` | `{image}` | `{data_url}` |")
                    lines.append("")

                # Autoscaling
                if endpoint.autoscaling:
                    autoscaling = endpoint.autoscaling
                    lines.extend(
                        [
                            "**Autoscaling Configuration**:",
                            "",
                            f"- **Min Capacity**: {autoscaling.min_capacity}",
                            f"- **Max Capacity**: {autoscaling.max_capacity}",
                            "",
                        ]
                    )

                    if autoscaling.policies:
                        lines.append("**Scaling Policies**:")
                        lines.append("")
                        for policy in autoscaling.policies:
                            lines.append(f"- **{policy.policy_name}**")
                            lines.append(f"  - Type: {policy.policy_type}")
                            if policy.metric_name:
                                lines.append(f"  - Metric: {policy.metric_name}")
                            if policy.target_value:
                                lines.append(f"  - Target Value: {policy.target_value}")
                            if policy.scale_in_cooldown:
                                lines.append(
                                    f"  - Scale-in Cooldown: {policy.scale_in_cooldown}s"
                                )
                            if policy.scale_out_cooldown:
                                lines.append(
                                    f"  - Scale-out Cooldown: {policy.scale_out_cooldown}s"
                                )
                        lines.append("")
                else:
                    lines.append("**Autoscaling**: Not configured")
                    lines.append("")

            lines.extend(["---", ""])

    # Orphaned Lambdas
    if orphaned_lambdas:
        lines.extend(
            [
                "## Orphaned Resources",
                "",
                "### Lambdas with ENDPOINT_NAME but no API Gateway Trigger",
                "",
                "| Lambda Name | Runtime | ENDPOINT_NAME |",
                "|-------------|---------|---------------|",
            ]
        )
        for lambda_info in orphaned_lambdas:
            lines.append(
                f"| `{lambda_info.name}` | {lambda_info.runtime} | "
                f"`{lambda_info.endpoint_name}` |"
            )
        lines.append("")

    # Orphaned Endpoints
    if orphaned_endpoints:
        lines.extend(
            [
                "### SageMaker Endpoints Not Found",
                "",
                "These endpoints are referenced in Lambda environment variables but were not found:",
                "",
            ]
        )
        for ep_name in orphaned_endpoints:
            lines.append(f"- `{ep_name}`")
        lines.append("")

    # Non-ML API Gateways
    ml_api_ids = set(c.api_gateway.api_id for c in chains)
    non_ml_apis = [api for api in all_apis if api.api_id not in ml_api_ids]

    if non_ml_apis:
        lines.extend(
            [
                "---",
                "",
                "## Appendix: API Gateways Not Connected to SageMaker",
                "",
                "| Name | Type | URL | Lambda Integrations |",
                "|------|------|-----|---------------------|",
            ]
        )
        for api in non_ml_apis:
            lambda_count = len(api.lambda_integrations)
            lines.append(
                f"| {api.name} | {api.api_type} | {api.endpoint_url} | {lambda_count} |"
            )
        lines.append("")

    # Write report
    output_path.write_text("\n".join(lines))


def save_raw_data(
    chains: list[InfrastructureChain],
    orphaned_lambdas: list[LambdaInfo],
    all_apis: list[APIGatewayInfo],
    output_path: Path,
) -> None:
    """Save raw data as JSON for debugging."""

    def serialize_datetime(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    data = {
        "chains": [
            {
                "api_gateway": {
                    "api_id": c.api_gateway.api_id,
                    "name": c.api_gateway.name,
                    "api_type": c.api_gateway.api_type,
                    "endpoint_url": c.api_gateway.endpoint_url,
                    "api_keys": [
                        {
                            "name": k.name,
                            "key_id": k.key_id,
                            "masked_value": k.masked_value,
                        }
                        for k in c.api_gateway.api_keys
                    ],
                },
                "lambda": {
                    "name": c.lambda_function.name,
                    "arn": c.lambda_function.arn,
                    "runtime": c.lambda_function.runtime,
                    "endpoint_name": c.lambda_function.endpoint_name,
                    "memory_size": c.lambda_function.memory_size,
                    "timeout": c.lambda_function.timeout,
                },
                "sagemaker_endpoint": {
                    "name": c.sagemaker_endpoint.name,
                    "arn": c.sagemaker_endpoint.arn,
                    "status": c.sagemaker_endpoint.status,
                    "creation_time": c.sagemaker_endpoint.creation_time,
                    "config": (
                        {
                            "name": c.sagemaker_endpoint.config.name,
                            "variants": [
                                {
                                    "name": v.name,
                                    "instance_type": v.instance_type,
                                    "instance_count": v.initial_instance_count,
                                    "model_name": v.model_name,
                                }
                                for v in c.sagemaker_endpoint.config.variants
                            ],
                        }
                        if c.sagemaker_endpoint.config
                        else None
                    ),
                    "models": [
                        {
                            "name": m.name,
                            "container_image": m.container_image,
                            "model_data_url": m.model_data_url,
                        }
                        for m in c.sagemaker_endpoint.models
                    ],
                    "autoscaling": (
                        {
                            "min_capacity": c.sagemaker_endpoint.autoscaling.min_capacity,
                            "max_capacity": c.sagemaker_endpoint.autoscaling.max_capacity,
                            "policies": [
                                {
                                    "name": p.policy_name,
                                    "type": p.policy_type,
                                    "target_value": p.target_value,
                                    "metric_name": p.metric_name,
                                }
                                for p in c.sagemaker_endpoint.autoscaling.policies
                            ],
                        }
                        if c.sagemaker_endpoint.autoscaling
                        else None
                    ),
                },
            }
            for c in chains
        ],
        "orphaned_lambdas": [
            {
                "name": l.name,
                "arn": l.arn,
                "endpoint_name": l.endpoint_name,
            }
            for l in orphaned_lambdas
        ],
        "all_api_gateways": [
            {
                "api_id": api.api_id,
                "name": api.name,
                "api_type": api.api_type,
                "endpoint_url": api.endpoint_url,
                "lambda_integrations": [
                    {
                        "function_name": i.function_name,
                        "resource_path": i.resource_path,
                        "http_method": i.http_method,
                    }
                    for i in api.lambda_integrations
                ],
            }
            for api in all_apis
        ],
    }

    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=serialize_datetime)
    )


# =============================================================================
# Main Entry Point
# =============================================================================


def generate_report(
    region: str = DEFAULT_REGION, output_dir: str | None = None
) -> Path:
    """Generate the complete infrastructure report."""
    # Create output directory
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

    if output_dir:
        report_dir = Path(output_dir)
    else:
        report_dir = Path("reports/aws_infra") / timestamp

    report_dir.mkdir(parents=True, exist_ok=True)

    print(f"Collecting AWS infrastructure data from {region}...", file=sys.stderr)

    # Phase 1: Collect API Gateways
    print("  Collecting REST APIs...", file=sys.stderr)
    rest_apis = collect_rest_apis(region)
    print(f"    Found {len(rest_apis)} REST APIs", file=sys.stderr)

    print("  Collecting HTTP APIs...", file=sys.stderr)
    http_apis = collect_http_apis(region)
    print(f"    Found {len(http_apis)} HTTP APIs", file=sys.stderr)

    all_apis = rest_apis + http_apis

    # Phase 2: Collect Lambdas with ENDPOINT_NAME
    print("  Collecting Lambda functions with ENDPOINT_NAME...", file=sys.stderr)
    lambdas = collect_lambdas_with_endpoint(region)
    print(f"    Found {len(lambdas)} Lambda functions", file=sys.stderr)

    # Phase 3: Build infrastructure chains
    print("  Building infrastructure chains...", file=sys.stderr)
    chains, orphaned_lambdas, orphaned_endpoints = build_infrastructure_chains(
        all_apis, lambdas, region
    )
    print(f"    Built {len(chains)} complete chains", file=sys.stderr)

    # Phase 4: Generate reports
    print("  Generating markdown report...", file=sys.stderr)
    generate_markdown_report(
        chains,
        orphaned_lambdas,
        orphaned_endpoints,
        all_apis,
        region,
        report_dir / "report.md",
    )

    print("  Saving raw data...", file=sys.stderr)
    save_raw_data(chains, orphaned_lambdas, all_apis, report_dir / "data.json")

    return report_dir


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate AWS ML infrastructure report tracing API Gateway -> Lambda -> SageMaker"
    )
    parser.add_argument(
        "--region",
        "-r",
        type=str,
        default=DEFAULT_REGION,
        help=f"AWS region (default: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        help="Output directory (default: reports/aws_infra/<timestamp>)",
    )
    args = parser.parse_args()

    report_dir = generate_report(region=args.region, output_dir=args.output_dir)

    print(f"\nReport generated: {report_dir}", file=sys.stderr)
    print(f"  - {report_dir / 'report.md'}")
    print(f"  - {report_dir / 'data.json'}")


if __name__ == "__main__":
    main()
