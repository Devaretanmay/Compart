# Copyright 2026 Compart Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
from typing import Any, Dict

from compart.graph import audit_dependency_graph, build_dependency_graph


def render_audit_cli(summary: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("         COMPART: EXTERNAL-CHANGE DEPENDENCY AUDIT & RISK REGISTER")
    lines.append("=" * 80)
    lines.append(f"Total External Providers Detected: {summary.get('total_providers_detected', 0)}")
    lines.append(f"Total AST Callsites Mapped:        {summary.get('total_callsites_mapped', 0)}")
    lines.append(f"Auto-Repairable Callsites:         {summary.get('total_auto_repairable', 0)}")
    lines.append("-" * 80)

    at_risk = summary.get("at_risk", [])
    if at_risk:
        lines.append("🔴 HIGH-RISK / BREAKING DRIFT (Immediate Action Required):")
        for item in at_risk:
            lines.append(f"  • Provider:         {item['provider_name']} ({item['package_name']} @ {item['current_version']} -> {item['target_version']})")
            lines.append(f"    Breaking Change:  {item['breaking_change']}")
            lines.append(f"    Active Callsites: {item['callsites_count']} callsites across {len(item['affected_files'])} files")
            lines.append(f"    Repair Status:    {'[MERGE_READY AUTO-PATCH]' if item.get('is_auto_repairable') else '[MANUAL REVIEW]'}")
            if item.get("migration_guide_url"):
                lines.append(f"    Vendor Guide:     {item['migration_guide_url']}")
            lines.append("")

    watchlist = summary.get("watchlist", [])
    if watchlist:
        lines.append("⚠️  UPCOMING DEPRECATION WATCHLIST:")
        for item in watchlist:
            lines.append(f"  • Provider:         {item['provider_name']} ({item['method_pattern']})")
            lines.append(f"    Deadline:         {item['deprecation_deadline']} (~{item.get('days_remaining', 60)} days remaining)")
            lines.append(f"    Active Callsites: {item['callsite_count']} mapped")
            if item.get("documentation_url"):
                lines.append(f"    Vendor Notice:    {item['documentation_url']}")
            lines.append("")

    healthy = summary.get("healthy", [])
    if healthy:
        lines.append("🟢 HEALTHY & UP-TO-DATE INTEGRATIONS:")
        for item in healthy:
            lines.append(f"  • Provider:         {item['provider_name']} ({item['package_name']} @ {item['current_version']})")
            lines.append(f"    Status:           {item['status_message']} ({item['callsite_count']} callsites)")
            lines.append("")

    lines.append("=" * 80)
    lines.append("Run `compart maintain <path> --provider <name>` to execute autonomous migration.")
    lines.append("=" * 80)
    return "\n".join(lines)


def render_audit_github_issue(summary: Dict[str, Any]) -> str:
    lines = []
    lines.append("# 🛡️ Compart: External Dependency Map & Risk Register\n")
    lines.append(f"Compart mapped **{summary.get('total_callsites_mapped', 0)} external API touchpoints** across **{summary.get('total_providers_detected', 0)} providers** in this repository.\n")

    at_risk = summary.get("at_risk", [])
    if at_risk:
        lines.append("### 🔴 Breaking Drift (Immediate Action Required)")
        lines.append("| Provider | Detected Package | Current -> Target | Active Callsites | Breaking Drift | Autonomous Action |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for item in at_risk:
            lines.append(f"| **{item['provider_name']}** | `{item['package_name']}` | `{item['current_version']}` -> `{item['target_version']}` | **{item['callsites_count']} callsites** ({len(item['affected_files'])} files) | {item['breaking_change']} | `compart maintain --provider {item['provider_name'].lower()}` [MERGE_READY] |")
        lines.append("")

    watchlist = summary.get("watchlist", [])
    if watchlist:
        lines.append("### ⚠️ Upcoming Deprecation Watchlist")
        lines.append("| Provider | Method / Pattern | Deprecation Deadline | Days Remaining | Documentation |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for item in watchlist:
            lines.append(f"| **{item['provider_name']}** | `{item['method_pattern']}` | **{item['deprecation_deadline']}** | ~{item.get('days_remaining', 60)} days | [Official Guide]({item['documentation_url']}) |")
        lines.append("")

    healthy = summary.get("healthy", [])
    if healthy:
        lines.append("### 🟢 Healthy & Up-to-Date Integrations")
        for item in healthy:
            lines.append(f"- **{item['provider_name']}** (`{item['package_name']}@{item['current_version']}`): {item['status_message']} ({item['callsite_count']} callsites mapped)")
        lines.append("")

    lines.append("---")
    lines.append("> *Generated automatically by Compart External-Change Intelligence.*")
    return "\n".join(lines)


def run_audit(repo_root: str = ".", output_format: str = "cli", write_graph: bool = False) -> str:
    summary = audit_dependency_graph(repo_root)

    if write_graph:
        graph = build_dependency_graph(repo_root)
        os.makedirs(os.path.join(repo_root, ".compart"), exist_ok=True)
        with open(os.path.join(repo_root, ".compart", "graph.json"), "w") as f:
            json.dump(graph, f, indent=2)

    if output_format == "json":
        return json.dumps(summary, indent=2)
    elif output_format in ("github-issue", "issue", "markdown", "md"):
        return render_audit_github_issue(summary)
    else:
        return render_audit_cli(summary)
