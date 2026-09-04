# Copyright 2026 Compart Authors
# SPDX-License-Identifier: Apache-2.0

"""
Compart GitHub App PR bot.

This is the first product milestone: install the app, open a PR, and Compart
automatically posts a verification result on that PR.

The PR bot is not a separate code path from the maintenance engine. It is an
event handler that constructs a TriggerContext and passes it to the shared
MaintenancePipeline.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional

from compart.github.client import GitHubAppClient
from compart.pipeline import (
    MaintenancePipeline,
    PipelinePolicy,
    TriggerContext,
    analyze_trigger_context,
)
from compart.github.pr_render import (
    render_verification_comment,
    render_maintenance_issue_comment,
)

_logger = logging.getLogger("compart.pr_bot")


# ── PR event handlers ──────────────────────────────────────────────────────

def handle_pull_request_event(
    payload: Dict[str, Any],
    event_type: str,
    client: GitHubAppClient,
    policy: Optional[PipelinePolicy] = None,
    workdir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handle a pull_request.* webhook event.

    Supported trigger types:

    * pull_request.opened
    * pull_request.synchronize
    * pull_request.reopened
    """
    policy = policy or PipelinePolicy()

    ppr = payload.get("pull_request")
    if not ppr:
        return {"success": False, "error": "No pull_request in payload"}

    repo = payload.get("repository", {}).get("full_name")
    if not repo:
        return {"success": False, "error": "No repository in payload"}

    number = ppr.get("number")
    action = payload.get("action", "")
    full_event = f"pull_request.{action}"

    ref = ppr.get("head", {}).get("ref")
    sha = ppr.get("head", {}).get("sha")
    base_ref = ppr.get("base", {}).get("ref")

    if not number or not ref or not sha:
        return {"success": False, "error": "Missing PR head info"}

    changed_files = _extract_changed_files(payload)
    ctx = TriggerContext.from_pull_request_event(payload, workdir=workdir, changed_files=changed_files)

    pipeline = MaintenancePipeline(client=client, policy=policy)
    result = pipeline.run(ctx)

    return {
        "success": True,
        "event_type": full_event,
        "repository": repo,
        "pr_number": number,
        "pipeline_status": result.status,
        "check_state": result.check_state,
        "check_description": result.status_description,
        "comment_posted": bool(result.comment_body),
        "comment_preview": _safe_preview(result.comment_body),
    }


def _extract_changed_files(payload: Dict[str, Any]) -> List[str]:
    """Try to extract changed file list from webhook payload or metadata."""
    ppr = payload.get("pull_request") or {}
    if ppr.get("files"):
        return [f.get("filename") for f in ppr.get("files") if f.get("filename")]

    meta = payload.get("compart", {})
    if isinstance(meta, dict):
        return meta.get("changed_files", [])
    return []


def _safe_preview(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()[:6]
    return "\n".join(lines)


# ── External-change event handler ──────────────────────────────────────────

def handle_external_change_event(
    payload: Dict[str, Any],
    client: GitHubAppClient,
    policy: Optional[PipelinePolicy] = None,
    workdir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handle an external-change event (provider version drift detected).

    The payload should contain:
        provider_name, from_version, to_version, repository, ref, sha, workdir
    """
    policy = policy or PipelinePolicy()

    repo = payload.get("repository")
    if not repo:
        return {"success": False, "error": "No repository in payload"}

    ctx = TriggerContext.from_external_change(
        provider_name=payload.get("provider_name", ""),
        from_version=payload.get("from_version", ""),
        to_version=payload.get("to_version", ""),
        repository=repo,
        ref=payload.get("ref", "main"),
        sha=payload.get("sha", ""),
        workdir=workdir,
        description=payload.get("description", ""),
    )

    pipeline = MaintenancePipeline(client=client, policy=policy)
    result = pipeline.run(ctx)

    return {
        "success": True,
        "event_type": "external.change.drift",
        "repository": repo,
        "pipeline_status": result.status,
        "check_state": result.check_state,
        "comment_posted": bool(result.comment_body),
    }


# ── Local / CI run helpers ─────────────────────────────────────────────────

def run_on_pr_locally(
    repo: str,
    pr_number: int,
    workdir: str,
    base_branch: str = "main",
    client: Optional[GitHubAppClient] = None,
    policy: Optional[PipelinePolicy] = None,
) -> Dict[str, Any]:
    """
    Run the PR bot against a local checkout of a PR.

    Useful for:
    * local development
    * CI check jobs that want Compart to post results
    """
    client = client or GitHubAppClient()
    changed_files = _diff_files_locally(workdir, base_branch)

    payload: Dict[str, Any] = {
        "action": "synchronize",
        "pull_request": {
            "number": pr_number,
            "title": "Local PR simulation",
            "body": "Compart local run",
            "head": {"ref": "pr-branch", "sha": "local-sha"},
            "base": {"ref": base_branch},
            "files": [{"filename": f} for f in changed_files],
        },
        "repository": {"full_name": repo},
        "compart": {"changed_files": changed_files},
    }

    return handle_pull_request_event(
        payload,
        "pull_request.synchronize",
        client,
        policy,
        workdir=workdir,
    )


def _diff_files_locally(workdir: str, base_branch: str) -> List[str]:
    """Return files changed in the current checkout relative to base_branch."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_branch],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
            return files
    except Exception as e:
        _logger.warning("git diff failed: %s", e)

    return []


# ── Webhook server attachment ──────────────────────────────────────────────

def make_pr_bot_handler(
    client: Optional[GitHubAppClient] = None,
    policy: Optional[PipelinePolicy] = None,
    workdir_fn: Optional[Callable[[Dict[str, Any]], str]] = None,
) -> Callable[[Dict[str, Any], str], Dict[str, Any]]:
    """
    Create a webhook handler function compatible with Compart's webhook server.

    Usage:

        server = WebhookServer(...)
        server.handler = make_pr_bot_handler(client=client, policy=policy)
    """
    client = client or GitHubAppClient()
    policy = policy or PipelinePolicy()

    def handler(payload: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        workdir = None
        if workdir_fn:
            workdir = workdir_fn(payload)

        if event_type.startswith("pull_request."):
            return handle_pull_request_event(
                payload,
                event_type,
                client,
                policy,
                workdir=workdir,
            )

        if event_type.startswith("external.change"):
            return handle_external_change_event(
                payload,
                client,
                policy,
                workdir=workdir,
            )

        return {
            "success": True,
            "event": event_type,
            "handled": False,
            "note": "Event type not handled by PR bot",
        }

    return handler
