# Copyright 2026 Compart Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from compart._core import dependency_graph_build, dependency_graph_audit
except ImportError:
    dependency_graph_build = None
    dependency_graph_audit = None


@dataclass
class AtRiskItem:
    provider_name: str
    package_name: str
    current_version: str
    target_version: str
    breaking_change: str
    callsites_count: int = 0
    affected_files: List[str] = field(default_factory=list)
    is_auto_repairable: bool = True
    migration_guide_url: str = ""


@dataclass
class WatchlistItem:
    provider_name: str
    method_pattern: str
    deprecation_deadline: str
    days_remaining: Optional[int] = None
    callsite_count: int = 0
    documentation_url: str = ""


@dataclass
class HealthyItem:
    provider_name: str
    package_name: str
    current_version: str
    callsite_count: int = 0
    status_message: str = ""


@dataclass
class DependencyAuditSummary:
    total_providers_detected: int
    total_callsites_mapped: int
    at_risk: List[Dict[str, Any]]
    watchlist: List[Dict[str, Any]]
    healthy: List[Dict[str, Any]]
    total_auto_repairable: int


def build_dependency_graph(repo_root: str = ".") -> Dict[str, Any]:
    """Build the complete External-Change Dependency Graph for a repository."""
    if dependency_graph_build is None:
        return {"providers": [], "callsites": [], "edges": []}
    raw = dependency_graph_build(repo_root)
    return json.loads(raw)


def audit_dependency_graph(repo_root: str = ".") -> Dict[str, Any]:
    """Run an audit over the External-Change Dependency Graph and return risk summary."""
    if dependency_graph_audit is None:
        return {
            "total_providers_detected": 0,
            "total_callsites_mapped": 0,
            "at_risk": [],
            "watchlist": [],
            "healthy": [],
            "total_auto_repairable": 0,
        }
    raw = dependency_graph_audit(repo_root)
    return json.loads(raw)
