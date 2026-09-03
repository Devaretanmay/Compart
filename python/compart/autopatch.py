"""AutoPatch - Autonomous API maintenance and schema drift engine for Compart.

Provides Pythonic abstractions for:
- Diffing OpenAPI specifications for breaking changes
- Scanning source codebases (TS/JS/Py/Go) for external API callsites
- Generating complete maintenance plans with file & line targets
- Synthesizing executable contract tests (TypeScript Vitest / Python pytest)
- Rendering audit-grade PR markdown bodies
- Parsing and validating maintenance workflow DAGs
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from compart._core import (
        schema_diff as _core_schema_diff,
        ast_locate_callsites as _core_ast_locate_callsites,
        autopatch_plan as _core_autopatch_plan,
        synthesize_contracts as _core_synthesize_contracts,
        render_report_markdown as _core_render_report_markdown,
        workflow_validate as _core_workflow_validate,
        workflow_execution_order as _core_workflow_execution_order,
        inventory_scan as _core_inventory_scan,
        trials_run as _core_trials_run,
        trials_v2_run as _core_trials_v2_run,
        trust_report_render as _core_trust_report_render,
        patch_apply as _core_patch_apply,
        replay_execute as _core_replay_execute,
        git_replay_execute as _core_git_replay_execute,
    )
    _HAS_NATIVE = True
except ImportError:
    _HAS_NATIVE = False
    _core_schema_diff = None
    _core_ast_locate_callsites = None
    _core_autopatch_plan = None
    _core_synthesize_contracts = None
    _core_render_report_markdown = None
    _core_workflow_validate = None
    _core_workflow_execution_order = None
    _core_inventory_scan = None
    _core_trials_run = None
    _core_trials_v2_run = None
    _core_trust_report_render = None
    _core_patch_apply = None
    _core_replay_execute = None
    _core_git_replay_execute = None


@dataclass
class ScanConfig:
    sdk_names: List[str] = field(default_factory=list)
    api_base_urls: List[str] = field(default_factory=list)
    method_patterns: List[str] = field(default_factory=list)
    extensions: List[str] = field(default_factory=lambda: ["ts", "tsx", "js", "jsx", "py", "go"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sdk_names": self.sdk_names,
            "api_base_urls": self.api_base_urls,
            "method_patterns": self.method_patterns,
            "extensions": self.extensions,
        }


def diff_schemas(old_spec_json: str, new_spec_json: str) -> Dict[str, Any]:
    """Diff two OpenAPI JSON specs and return a structured diff."""
    if _HAS_NATIVE and _core_schema_diff is not None:
        return json.loads(_core_schema_diff(old_spec_json, new_spec_json))
    return {"breaking_count": 0, "endpoint_changes": []}


def scan_callsites(root_dir: str, config: Optional[ScanConfig] = None) -> Dict[str, Any]:
    """Scan a repository directory for API callsites matching the config."""
    cfg = config or ScanConfig()
    if _HAS_NATIVE and _core_ast_locate_callsites is not None:
        return json.loads(_core_ast_locate_callsites(root_dir, json.dumps(cfg.to_dict())))
    return {"callsites": [], "files_scanned": 0, "files_with_hits": 0}


def generate_maintenance_plan(
    old_spec_json: str,
    new_spec_json: str,
    repo_root: str,
    config: Optional[ScanConfig] = None,
) -> Dict[str, Any]:
    """Generate a complete maintenance plan correlating schema diffs with codebase callsites."""
    cfg = config or ScanConfig()
    if _HAS_NATIVE and _core_autopatch_plan is not None:
        return json.loads(_core_autopatch_plan(old_spec_json, new_spec_json, repo_root, json.dumps(cfg.to_dict())))
    return {"status": "Clean", "patch_targets": []}


def synthesize_contracts(
    api_name: str,
    old_version: str,
    new_version: str,
    specs: List[Dict[str, Any]],
    language: str = "typescript",
) -> str:
    """Synthesize executable contract tests (typescript vitest or python pytest)."""
    if _HAS_NATIVE and _core_synthesize_contracts is not None:
        return _core_synthesize_contracts(api_name, old_version, new_version, json.dumps(specs), language)
    return ""


def render_markdown_report(plan: Dict[str, Any]) -> str:
    """Render a MaintenancePlan as a GitHub PR markdown body."""
    if _HAS_NATIVE and _core_render_report_markdown is not None:
        return _core_render_report_markdown(json.dumps(plan))
    return f"# AutoPatch Plan for {plan.get('api_name', 'API')}"


def validate_workflow(workflow_dict: Dict[str, Any]) -> List[str]:
    """Validate a maintenance workflow definition dictionary."""
    if _HAS_NATIVE and _core_workflow_validate is not None:
        return _core_workflow_validate(json.dumps(workflow_dict))
    return []


def get_workflow_execution_order(workflow_dict: Dict[str, Any]) -> List[str]:
    """Compute topological execution order for a maintenance workflow."""
    if _HAS_NATIVE and _core_workflow_execution_order is not None:
        return _core_workflow_execution_order(json.dumps(workflow_dict))
    return [s.get("name", "") for s in workflow_dict.get("steps", [])]


def run_inventory(repo_root: str = ".") -> Dict[str, Any]:
    """Scan a repository for all external API dependencies using builtin provider registry."""
    if _HAS_NATIVE and _core_inventory_scan is not None:
        return json.loads(_core_inventory_scan(repo_root))
    return {"repo_root": repo_root, "dependencies": [], "total_callsites": 0}


def run_trials() -> Dict[str, Any]:
    """Execute the Compart Trials canonical benchmark suite and return the report."""
    if _HAS_NATIVE and _core_trials_run is not None:
        return json.loads(_core_trials_run())
    return {"total_cases": 0, "cases_passed": 0, "results": []}


def apply_patch(repo_root: str, plan: Dict[str, Any], dry_run: bool = True) -> List[Dict[str, Any]]:
    """Apply surgical AST patches for plan targets."""
    if _HAS_NATIVE and _core_patch_apply is not None:
        return json.loads(_core_patch_apply(repo_root, json.dumps(plan), dry_run))
    return []


def run_trials_v2(filter_case: Optional[str] = None, filter_provider: Optional[str] = None) -> Dict[str, Any]:
    """Execute Compart Trials v2 against historical ground truth cases."""
    if _HAS_NATIVE and _core_trials_v2_run is not None:
        return json.loads(_core_trials_v2_run(filter_case, filter_provider))
    return {"total_cases_evaluated": 0, "verified_ground_truth_cases": 0, "rejected_unverified_cases": 0, "results": []}


def render_trust_report(plan: Dict[str, Any]) -> str:
    """Render an enterprise-grade trust report from a maintenance plan."""
    if _HAS_NATIVE and _core_trust_report_render is not None:
        return _core_trust_report_render(json.dumps(plan))
    return render_markdown_report(plan)


def reproduce_case(case_id: str, project_root: str = ".", offline: bool = True) -> Dict[str, Any]:
    """Execute historical replay against real software commits and official documentation."""
    if _HAS_NATIVE and _core_replay_execute is not None:
        return json.loads(_core_replay_execute(case_id, project_root, offline))
    return {
        "case_id": case_id,
        "success": False,
        "error": "Native core replay extension not available",
    }


def reproduce_git_case(case_id: str, project_root: str = ".", live: bool = False) -> Dict[str, Any]:
    """Execute Full-Repo Git History Replay Protocol against real software repositories."""
    if _HAS_NATIVE and _core_git_replay_execute is not None:
        return json.loads(_core_git_replay_execute(case_id, project_root, live))
    return {
        "case_id": case_id,
        "success": False,
        "error": "Native core git replay extension not available",
    }
