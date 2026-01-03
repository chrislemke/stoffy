#!/usr/bin/env python3
"""
Amplitude Experiment Tools for opencode (EU)

Read-only access to Amplitude Experiment & Analytics APIs in the EU region.

Usage (internal, via opencode tools):

  python amplitude_experiments_client.py experiment-search <query> [projectId] [includeArchived]
  python amplitude_experiments_client.py experiment-details <identifier>
  python amplitude_experiments_client.py eval-user <user_id_or_dash> <device_id_or_dash> <flag_keys_or_dash> <context_json_or_dash>
  python amplitude_experiments_client.py chart-csv <chart_id>
"""

from __future__ import annotations

import csv
from datetime import date
from io import StringIO
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

import requests
import yaml

# Try to import the SDK, but allow the script to run for other commands if missing
try:
    from amplitude_experiment import (
        Experiment,
        RemoteEvaluationConfig,
        ServerZone,
        User,
    )

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


# -----------------------------------------------------------------------------
# Env loading
# -----------------------------------------------------------------------------


def find_env_file() -> Path | None:
    """Find .env file by walking up directory tree from this script."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        # If we see opencode.jsonc or .opencode, assume project root here
        if (current / "opencode.jsonc").exists() or (current / ".opencode").exists():
            env_path = current / ".env"
            if env_path.exists():
                return env_path
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def load_env() -> dict[str, str]:
    """Load environment variables from .env (if present) and os.environ."""
    env_vars: dict[str, str] = {}

    env_file = find_env_file()
    if env_file and env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                value = value.strip().strip("'\"")
                env_vars[key.strip()] = value

    # Overlay with real environment variables (take precedence)
    for key, value in os.environ.items():
        env_vars[key] = value

    # Set sensible EU defaults if not provided
    env_vars.setdefault(
        "AMPLITUDE_ANALYTICS_BASE_URL",
        "https://analytics.eu.amplitude.com/api/2",
    )
    env_vars.setdefault(
        "AMPLITUDE_ANALYTICS_CHART_BASE_URL",
        "https://analytics.eu.amplitude.com/api/3",
    )
    env_vars.setdefault(
        "AMPLITUDE_EXPERIMENT_MGMT_BASE_URL",
        "https://experiment.eu.amplitude.com/api/1",
    )
    # SDK handles the evaluation URL via ServerZone.EU, but we keep this for reference
    env_vars.setdefault(
        "AMPLITUDE_EXPERIMENT_EVAL_BASE_URL",
        "https://api.lab.eu.amplitude.com/v1",
    )

    return env_vars


def require_env(env: dict[str, str], keys: List[str]) -> None:
    missing = [k for k in keys if not env.get(k)]
    if missing:
        print(
            json.dumps(
                {
                    "error": "Missing required environment variables",
                    "missing": missing,
                }
            )
        )
        sys.exit(1)


def http_get_json(
    url: str,
    *,
    headers: Dict[str, str] | None = None,
    params: Dict[str, Any] | None = None,
    auth: Any | None = None,
    timeout: int = 30,
) -> Any:
    resp = requests.get(url, headers=headers, params=params, auth=auth, timeout=timeout)
    if resp.status_code != 200:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        print(
            json.dumps(
                {
                    "error": "HTTP request failed",
                    "url": url,
                    "status": resp.status_code,
                    "body": body,
                },
                default=str,
            )
        )
        sys.exit(1)
    try:
        return resp.json()
    except Exception:
        print(
            json.dumps(
                {
                    "error": "Failed to parse JSON response",
                    "url": url,
                    "status": resp.status_code,
                    "body": resp.text[:1000],
                }
            )
        )
        sys.exit(1)


# -----------------------------------------------------------------------------
# Experiment Management (EU)
# -----------------------------------------------------------------------------


def get_management_api_key(env: dict[str, str]) -> str:
    """Get the Amplitude Management API key from environment, checking multiple possible names."""
    # Check multiple possible environment variable names
    possible_keys = [
        "AMPLITUDE_MANAGEMENT_API_KEY",
        "AMPLITUDE_EXPERIMENT_TOKEN",
        "AMPLITUDE_EXPERIMENT_API_KEY",
    ]
    for key in possible_keys:
        if env.get(key):
            return env[key]

    # None found - report error with all possible names
    print(
        json.dumps(
            {
                "error": "Missing Amplitude Management API key",
                "hint": f"Set one of: {', '.join(possible_keys)} in .env file",
            }
        )
    )
    sys.exit(1)


def list_experiments(
    env: dict[str, str],
    project_id: str | None = None,
    include_archived: bool = False,
) -> List[dict[str, Any]]:
    """List experiments via Management API."""
    api_key = get_management_api_key(env)
    base = env["AMPLITUDE_EXPERIMENT_MGMT_BASE_URL"].rstrip("/")
    url = f"{base}/experiments"

    params: Dict[str, Any] = {"limit": 1000}
    if project_id:
        params["projectId"] = project_id
    if include_archived:
        params["includeArchived"] = "true"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    data = http_get_json(url, headers=headers, params=params)
    return data.get("experiments", [])


def simplify_experiment(exp: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, readable experiment representation."""
    return {
        "id": exp.get("id"),
        "projectId": exp.get("projectId"),
        "key": exp.get("key"),
        "name": exp.get("name"),
        "state": exp.get("state"),
        "enabled": exp.get("enabled"),
        "evaluationMode": exp.get("evaluationMode"),
        "experimentType": exp.get("experimentType"),
        "rolloutPercentage": exp.get("rolloutPercentage"),
        "variants": [v.get("key") for v in exp.get("variants", [])],
        "deployments": exp.get("deployments", []),
        "tags": exp.get("tags", []),
        "startDate": exp.get("startDate"),
        "endDate": exp.get("endDate"),
        "createdAt": exp.get("createdAt"),
        "lastModifiedAt": exp.get("lastModifiedAt"),
    }


def cmd_experiment_search(args: List[str]) -> None:
    """Search experiments by name/key/id."""
    env = load_env()

    query = args[0] if args else ""
    project_id = args[1] if len(args) > 1 and args[1] else None
    include_archived = len(args) > 2 and args[2].strip().lower() == "true"

    experiments = list_experiments(
        env, project_id=project_id, include_archived=include_archived
    )

    if query:
        q = query.lower()
        filtered = [
            e
            for e in experiments
            if q in str(e.get("name", "")).lower()
            or q in str(e.get("key", "")).lower()
            or query == str(e.get("id", ""))
        ]
    else:
        filtered = experiments

    output = {
        "query": query or None,
        "projectId": project_id,
        "includeArchived": include_archived,
        "count": len(filtered),
        "experiments": [simplify_experiment(e) for e in filtered],
    }
    print(json.dumps(output, indent=2, default=str))


def cmd_experiment_details(args: List[str]) -> None:
    """Get experiment details for a given id/key/name."""
    if not args:
        print(
            json.dumps(
                {
                    "error": "Missing experiment identifier. Usage: experiment-details <id|key|name>"
                }
            )
        )
        sys.exit(1)

    identifier = args[0]
    env = load_env()
    experiments = list_experiments(env, include_archived=True)

    id_str = identifier
    id_lower = identifier.lower()

    # Prioritize exact id/key/name matches, then partial matches
    candidates: List[dict[str, Any]] = []
    seen_ids: set[Any] = set()

    def add_matches(match_list: List[dict[str, Any]]) -> None:
        for e in match_list:
            eid = e.get("id")
            if eid not in seen_ids:
                seen_ids.add(eid)
                candidates.append(e)

    add_matches([e for e in experiments if str(e.get("id")) == id_str])
    add_matches([e for e in experiments if str(e.get("key")) == id_str])
    add_matches([e for e in experiments if str(e.get("name")) == id_str])
    add_matches(
        [
            e
            for e in experiments
            if id_lower in str(e.get("name", "")).lower()
            or id_lower in str(e.get("key", "")).lower()
        ]
    )

    if not candidates:
        print(
            json.dumps(
                {
                    "identifier": identifier,
                    "error": "No experiments matched identifier",
                }
            )
        )
        sys.exit(1)

    selected = candidates[0]
    output = {
        "identifier": identifier,
        "selected": simplify_experiment(selected),
        "matches": [simplify_experiment(e) for e in candidates],
    }
    print(json.dumps(output, indent=2, default=str))


# -----------------------------------------------------------------------------
# Experiment Evaluation (via Official SDK)
# -----------------------------------------------------------------------------


def cmd_eval_user(args: List[str]) -> None:
    """Evaluate variant assignment for a user via amplitude-experiment SDK."""
    if not SDK_AVAILABLE:
        print(
            json.dumps(
                {
                    "error": "amplitude-experiment SDK not found. Install it with: pip install amplitude-experiment"
                }
            )
        )
        sys.exit(1)

    env = load_env()
    deployment_key = env.get("AMPLITUDE_EXPERIMENT_DEPLOYMENT_KEY_EU") or env.get(
        "AMPLITUDE_EXPERIMENT_DEPLOYMENT_KEY"
    )
    if not deployment_key:
        print(
            json.dumps(
                {
                    "error": "Missing deployment key. Set AMPLITUDE_EXPERIMENT_DEPLOYMENT_KEY_EU in .env"
                }
            )
        )
        sys.exit(1)

    user_id = args[0] if len(args) > 0 and args[0] not in ("-", "") else None
    device_id = args[1] if len(args) > 1 and args[1] not in ("-", "") else None
    flag_keys_arg = args[2] if len(args) > 2 and args[2] not in ("-", "") else None
    context_json = args[3] if len(args) > 3 and args[3] not in ("-", "") else None

    # Initialize SDK
    # config = RemoteEvaluationConfig(server_zone=ServerZone.EU)
    # Using EU server zone
    try:
        config = RemoteEvaluationConfig(server_zone=ServerZone.EU)
        client = Experiment.initialize(deployment_key, config)
    except Exception as e:
        print(json.dumps({"error": f"Failed to initialize Experiment SDK: {str(e)}"}))
        sys.exit(1)

    # Build User object
    user_kwargs = {}
    if user_id:
        user_kwargs["user_id"] = user_id
    if device_id:
        user_kwargs["device_id"] = device_id

    if context_json:
        try:
            ctx = json.loads(context_json)
            # Map known fields from context if present
            # The User class has fields like 'country', 'city', 'user_properties', etc.
            # We'll just pass user_properties and a few common ones if they are in the root of the JSON
            # or in a 'user_properties' sub-object.

            # If the user passed a context object, we can try to merge it.
            # Common pattern: context = {"user_properties": {...}, "country": "US"}

            # Direct mapping for known User fields
            known_fields = [
                "country",
                "city",
                "region",
                "dma",
                "language",
                "platform",
                "version",
                "os",
                "device_manufacturer",
                "device_brand",
                "device_model",
                "carrier",
                "library",
                "user_properties",
            ]

            for field in known_fields:
                if field in ctx:
                    user_kwargs[field] = ctx[field]

            # Special case: if user properties are at the root but not in 'user_properties'
            # (less common, but let's assume specific structure first)

        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid context_json. Must be valid JSON."}))
            sys.exit(1)

    user = User(**user_kwargs)

    flag_keys = None
    if flag_keys_arg:
        flag_keys = [k.strip() for k in flag_keys_arg.split(",") if k.strip()]

    try:
        # fetch(user) returns dict[str, Variant]
        # We can pass flag_keys to fetch specific flags if supported,
        # but the SDK 'fetch' method usually fetches all or based on specific options.
        # The python SDK fetch signature is `fetch(self, user: User, flag_keys: List[str] = None)`
        variants = client.fetch(user, flag_keys=flag_keys)

        # Convert variants to dict for output
        # Variant object has 'value', 'payload'
        output_variants = {}
        for key, variant in variants.items():
            output_variants[key] = {"value": variant.value, "payload": variant.payload}

        output = {
            "user_id": user_id,
            "device_id": device_id,
            "flag_keys": flag_keys,
            "variants": output_variants,
        }
        print(json.dumps(output, indent=2, default=str))

    except Exception as e:
        print(json.dumps({"error": f"Evaluation failed: {str(e)}"}))
        sys.exit(1)


# -----------------------------------------------------------------------------
# Dashboard REST API (EU) – chart CSV
# -----------------------------------------------------------------------------


def cmd_chart_csv(args: List[str]) -> None:
    """Fetch CSV for a saved chart and return as JSON rows."""
    if not args:
        print(json.dumps({"error": "Missing chart id. Usage: chart-csv <chart_id>"}))
        sys.exit(1)

    chart_id = args[0]
    env = load_env()
    require_env(env, ["AMPLITUDE_API_KEY_EU", "AMPLITUDE_SECRET_KEY_EU"])

    base = env["AMPLITUDE_ANALYTICS_CHART_BASE_URL"].rstrip("/")
    url = f"{base}/chart/{chart_id}/csv"

    # Basic auth: api key + secret
    api_key = env["AMPLITUDE_API_KEY_EU"]
    secret = env["AMPLITUDE_SECRET_KEY_EU"]
    auth = (api_key, secret)

    resp = requests.get(url, auth=auth, timeout=60)
    if resp.status_code != 200:
        print(
            json.dumps(
                {
                    "error": "Chart CSV request failed",
                    "status": resp.status_code,
                    "body": resp.text[:1000],
                }
            )
        )
        sys.exit(1)

    csv_text = resp.text
    reader = csv.reader(StringIO(csv_text))
    rows = list(reader)
    if not rows:
        print(
            json.dumps(
                {
                    "chart_id": chart_id,
                    "error": "Empty CSV response",
                }
            )
        )
        sys.exit(1)

    header = rows[0]
    data_rows = [
        {header[i]: row[i] for i in range(min(len(header), len(row)))}
        for row in rows[1:]
        if any(cell.strip() for cell in row)
    ]

    output = {
        "chart_id": chart_id,
        "columns": header,
        "rows": data_rows,
    }
    print(json.dumps(output, indent=2, default=str))


# -----------------------------------------------------------------------------
# Experiment Report Generation
# -----------------------------------------------------------------------------


def get_repo_root() -> Path:
    """Get the repository root directory."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "opencode.jsonc").exists() or (current / ".opencode").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    # Fallback: assume scripts/ is one level below root
    return Path(__file__).resolve().parent.parent


def load_projects_index() -> Dict[str, Any]:
    """Load the projects index for project inference."""
    repo_root = get_repo_root()
    index_path = repo_root / "indices" / "projects.yaml"
    if not index_path.exists():
        return {}
    with open(index_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def infer_project_from_experiment(
    experiment: Dict[str, Any],
    projects_index: Dict[str, Any],
) -> str | None:
    """
    Infer project name from experiment metadata using fuzzy matching.

    Returns the project key (folder name) or None if no match found.
    """
    exp_name = str(experiment.get("name", "")).lower()
    exp_key = str(experiment.get("key", "")).lower()
    exp_tags = [str(t).lower() for t in experiment.get("tags", [])]

    projects = projects_index.get("projects", {})

    # Define keyword mappings for known projects
    keyword_mappings: Dict[str, List[str]] = {
        "service_fee_optimization": [
            "service fee",
            "service-fee",
            "sfomi",
            "nsfomm",
            "service package",
            "service-package",
            "sp-",
            "se-",
        ],
        "conversational_ai_bot": [
            "conversational",
            "ai bot",
            "aipeter",
            "chat bot",
            "chatbot",
        ],
        "flight_recommender": [
            "flight recommend",
            "flight-recommend",
            "recommender",
        ],
        "internationalization": [
            "i18n",
            "international",
            "localization",
            "market entry",
        ],
        "galactic_roadmap": [
            "galactic",
            "mystic mercury",
            "platform",
        ],
    }

    # Check keyword mappings first (highest priority)
    combined_text = f"{exp_name} {exp_key} {' '.join(exp_tags)}"
    for project_key, keywords in keyword_mappings.items():
        if project_key in projects:
            for keyword in keywords:
                if keyword in combined_text:
                    return project_key

    # Fuzzy match against project names and descriptions
    for project_key, project_data in projects.items():
        project_desc = str(project_data.get("description", "")).lower()
        project_path = str(project_data.get("path", "")).lower()

        # Check if experiment name contains project key parts
        key_parts = project_key.replace("_", " ").split()
        if all(part in combined_text for part in key_parts if len(part) > 3):
            return project_key

        # Check if project description matches
        if project_desc and len(project_desc) > 10:
            desc_words = [w for w in project_desc.split() if len(w) > 4]
            if sum(1 for w in desc_words if w in combined_text) >= 2:
                return project_key

    return None


def generate_experiment_report_markdown(
    experiment: Dict[str, Any],
    project_name: str | None,
    report_date: date,
) -> str:
    """Generate markdown report content for an experiment."""
    exp_id = experiment.get("id", "unknown")
    exp_key = experiment.get("key", "unknown")
    exp_name = experiment.get("name", "Unknown Experiment")
    state = experiment.get("state", "unknown")
    enabled = experiment.get("enabled", False)
    eval_mode = experiment.get("evaluationMode", "unknown")
    exp_type = experiment.get("experimentType", "unknown")
    rollout = experiment.get("rolloutPercentage", 0)
    variants = experiment.get("variants", [])
    deployments = experiment.get("deployments", [])
    tags = experiment.get("tags", [])
    start_date = experiment.get("startDate", "N/A")
    end_date = experiment.get("endDate", "N/A")
    created_at = experiment.get("createdAt", "N/A")
    last_modified = experiment.get("lastModifiedAt", "N/A")

    # Format dates for display
    def format_date(d: Any) -> str:
        if not d or d == "N/A":
            return "N/A"
        if isinstance(d, str):
            # Truncate ISO datetime to date
            return d[:10] if len(d) >= 10 else d
        return str(d)

    # Build variants table
    variants_table = "| Variant Key | Description |\n|-------------|-------------|\n"
    if variants:
        for v in variants:
            v_key = v if isinstance(v, str) else v.get("key", "unknown")
            variants_table += f"| {v_key} | - |\n"
    else:
        variants_table += "| (no variants) | - |\n"

    # Build deployments list
    deployments_list = ""
    if deployments:
        for d in deployments:
            d_name = d if isinstance(d, str) else d.get("key", str(d))
            deployments_list += f"- {d_name}\n"
    else:
        deployments_list = "- (no deployments)\n"

    # Build tags list
    tags_str = ", ".join(tags) if tags else "(none)"

    # YAML frontmatter
    frontmatter = {
        "experiment_id": exp_id,
        "experiment_key": exp_key,
        "experiment_name": exp_name,
        "state": state,
        "enabled": enabled,
        "report_date": report_date.isoformat(),
        "source": "amplitude_management_api",
        "project": project_name or "unassigned",
    }

    yaml_str = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    report = f"""---
{yaml_str.strip()}
---

# Experiment Report: {exp_name}

**Generated**: {report_date.isoformat()}

## Overview

| Property | Value |
|----------|-------|
| ID | {exp_id} |
| Key | `{exp_key}` |
| State | {state} |
| Enabled | {enabled} |
| Type | {exp_type} |
| Evaluation Mode | {eval_mode} |
| Rollout % | {rollout}% |

## Variants

{variants_table}

## Timeline

| Event | Date |
|-------|------|
| Created | {format_date(created_at)} |
| Started | {format_date(start_date)} |
| Ended | {format_date(end_date)} |
| Last Modified | {format_date(last_modified)} |

## Deployments

{deployments_list}

## Tags

{tags_str}

## Notes

<!-- Add analysis notes, observations, or findings below -->

---
*Report generated by opencode Amplitude Experiment Tool*
"""
    return report


def save_experiment_report(
    report_content: str,
    experiment: Dict[str, Any],
    project_name: str | None,
    report_date: date,
) -> Path:
    """
    Save experiment report to appropriate location.

    Returns the path where the report was saved.
    """
    repo_root = get_repo_root()
    exp_key = experiment.get("key", "unknown")

    # Sanitize key for filename
    safe_key = re.sub(r"[^a-z0-9_-]", "_", exp_key.lower())

    # Determine output directory
    if project_name:
        output_dir = repo_root / "project_management" / project_name / "experiments"
    else:
        output_dir = repo_root / "reports" / "experiments"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Create filename with date
    filename = f"{safe_key}_{report_date.isoformat()}.md"
    output_path = output_dir / filename

    # Write report
    output_path.write_text(report_content, encoding="utf-8")

    return output_path


def cmd_generate_report(args: List[str]) -> None:
    """
    Generate a markdown report for an Amplitude experiment.

    Usage: generate-report <experiment_name_or_key> [--project <project_name>]
    """
    if not args:
        print(
            json.dumps(
                {
                    "error": "Missing experiment identifier. "
                    "Usage: generate-report <experiment_name_or_key> [--project <project_name>]"
                }
            )
        )
        sys.exit(1)

    # Parse arguments
    experiment_identifier = args[0]
    project_name: str | None = None

    # Check for --project flag
    if "--project" in args:
        idx = args.index("--project")
        if idx + 1 < len(args):
            project_name = args[idx + 1]

    env = load_env()

    # Get experiment details (reuse existing logic)
    experiments = list_experiments(env, include_archived=True)

    id_str = experiment_identifier
    id_lower = experiment_identifier.lower()

    # Find matching experiments (same logic as cmd_experiment_details)
    candidates: List[Dict[str, Any]] = []
    seen_ids: set[Any] = set()

    def add_matches(match_list: List[Dict[str, Any]]) -> None:
        for e in match_list:
            eid = e.get("id")
            if eid not in seen_ids:
                seen_ids.add(eid)
                candidates.append(e)

    add_matches([e for e in experiments if str(e.get("id")) == id_str])
    add_matches([e for e in experiments if str(e.get("key")) == id_str])
    add_matches([e for e in experiments if str(e.get("name")) == id_str])
    add_matches(
        [
            e
            for e in experiments
            if id_lower in str(e.get("name", "")).lower()
            or id_lower in str(e.get("key", "")).lower()
        ]
    )

    if not candidates:
        print(
            json.dumps(
                {
                    "identifier": experiment_identifier,
                    "error": "No experiments matched identifier",
                }
            )
        )
        sys.exit(1)

    # Use first match
    selected = candidates[0]
    simplified = simplify_experiment(selected)

    # Infer project if not specified
    if not project_name:
        projects_index = load_projects_index()
        project_name = infer_project_from_experiment(simplified, projects_index)

    # Generate report
    report_date = date.today()
    report_content = generate_experiment_report_markdown(
        simplified, project_name, report_date
    )

    # Save report
    output_path = save_experiment_report(
        report_content, simplified, project_name, report_date
    )

    # Get relative path for output
    repo_root = get_repo_root()
    try:
        relative_path = output_path.relative_to(repo_root)
    except ValueError:
        relative_path = output_path

    output = {
        "experiment_id": simplified.get("id"),
        "experiment_key": simplified.get("key"),
        "experiment_name": simplified.get("name"),
        "state": simplified.get("state"),
        "project": project_name or "unassigned",
        "project_inferred": project_name is not None and "--project" not in args,
        "report_date": report_date.isoformat(),
        "file_path": str(relative_path),
        "message": f"Report generated for '{simplified.get('name')}' -> {relative_path}",
        "matches_count": len(candidates),
    }

    if len(candidates) > 1:
        output["other_matches"] = [
            {"id": e.get("id"), "key": e.get("key"), "name": e.get("name")}
            for e in candidates[1:5]  # Show up to 4 other matches
        ]

    print(json.dumps(output, indent=2, default=str))


# -----------------------------------------------------------------------------
# Main dispatch
# -----------------------------------------------------------------------------


COMMANDS = {
    "experiment-search": cmd_experiment_search,
    "experiment-details": cmd_experiment_details,
    "eval-user": cmd_eval_user,
    "chart-csv": cmd_chart_csv,
    "generate-report": cmd_generate_report,
}


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable commands:", ", ".join(COMMANDS.keys()))
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command in ("--help", "-h", "help"):
        print(__doc__)
        sys.exit(0)

    if command not in COMMANDS:
        print(
            json.dumps(
                {
                    "error": f"Unknown command: {command}. "
                    f"Available: {', '.join(COMMANDS.keys())}"
                }
            )
        )
        sys.exit(1)

    COMMANDS[command](args)


if __name__ == "__main__":
    main()
