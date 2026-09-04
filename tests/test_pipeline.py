import pytest
from unittest.mock import MagicMock

from compart.config import PipelinePolicy
from compart.pipeline import (
    TriggerContext,
    DriftFinding,
    AnalysisResult,
    MaintenancePipeline,
    surface_result,
    analyze_trigger_context,
)


def test_trigger_context_from_pull_request_event():
    payload = {
        "action": "opened",
        "repository": {"full_name": "acme/repo"},
        "pull_request": {
            "number": 42,
            "title": "Upgrade deps",
            "body": "Bumping Stripe",
            "head": {"ref": "feature/upgrade", "sha": "abcdef123456"},
            "base": {"ref": "main"},
        },
    }
    ctx = TriggerContext.from_pull_request_event(payload, workdir="/tmp/fake")
    assert ctx.event_type == "pull_request.opened"
    assert ctx.repository == "acme/repo"
    assert ctx.pr_number == 42
    assert ctx.ref == "feature/upgrade"
    assert ctx.sha == "abcdef123456"
    assert ctx.base_ref == "main"
    assert ctx.workdir == "/tmp/fake"


def test_trigger_context_from_external_change():
    ctx = TriggerContext.from_external_change(
        provider_name="stripe",
        from_version="11.0.0",
        to_version="13.0.0",
        repository="acme/repo",
        ref="main",
        sha="11223344",
        workdir="/tmp/fake",
    )
    assert ctx.event_type == "external.change.stripe"
    assert ctx.provider_name == "stripe"
    assert ctx.from_version == "11.0.0"
    assert ctx.to_version == "13.0.0"
    assert ctx.repository == "acme/repo"


def test_pipeline_policy_auto_fix_rules():
    policy_default = PipelinePolicy()
    ctx_pr = TriggerContext(
        event_id="e1",
        event_type="pull_request.opened",
        repository="acme/repo",
        ref="main",
        sha="abc",
        workdir="/tmp",
        pr_number=1,
    )
    assert policy_default.auto_fix_enabled_for(ctx_pr) is False

    policy_pr_fix = PipelinePolicy(pr_auto_fix=True)
    assert policy_pr_fix.auto_fix_enabled_for(ctx_pr) is True

    policy_scoped = PipelinePolicy(pr_auto_fix=True, auto_fix_providers=["stripe"])
    ctx_stripe = TriggerContext(
        event_id="e2",
        event_type="pull_request.opened",
        repository="acme/repo",
        ref="main",
        sha="abc",
        workdir="/tmp",
        provider_name="stripe",
    )
    ctx_other = TriggerContext(
        event_id="e3",
        event_type="pull_request.opened",
        repository="acme/repo",
        ref="main",
        sha="abc",
        workdir="/tmp",
        provider_name="openai",
    )
    assert policy_scoped.auto_fix_enabled_for(ctx_stripe) is True
    assert policy_scoped.auto_fix_enabled_for(ctx_other) is False


def test_surface_result_clean_when_no_findings():
    ctx = TriggerContext(
        event_id="e1",
        event_type="pull_request.opened",
        repository="acme/repo",
        ref="main",
        sha="abc",
        workdir="/tmp",
        pr_number=10,
    )
    analysis = AnalysisResult(context=ctx, findings=[])
    client = MagicMock()
    policy = PipelinePolicy(always_report_clean=True)

    surface = surface_result(ctx, analysis, policy, client)
    assert surface.status_description == "Compart: no external contract impact detected"
    client.post_pr_comment.assert_called_once()
    assert "COMPART VERIFICATION" in surface.comment_body
    assert "[VERIFIED]" in surface.comment_body


def test_surface_result_with_drift_findings():
    ctx = TriggerContext(
        event_id="e1",
        event_type="pull_request.opened",
        repository="acme/repo",
        ref="main",
        sha="abc",
        workdir="/tmp",
        pr_number=10,
    )
    finding = DriftFinding(
        provider_name="stripe",
        display_name="Stripe Node SDK",
        package_name="stripe",
        current_version="11.0.0",
        target_version="13.0.0",
        breaking_change="v11 to v13 breaking changes",
        migration_guide_url="https://example.com",
        affected_files=["src/stripe.ts"],
        is_auto_repairable=True,
    )
    analysis = AnalysisResult(context=ctx, findings=[finding])
    client = MagicMock()
    policy = PipelinePolicy(inline_comments=False)

    surface = surface_result(ctx, analysis, policy, client)
    assert "Compart found 1 maintenance issue(s)" in surface.status_description
    client.post_pr_comment.assert_called_once()
    assert "COMPART FOUND A MAINTENANCE ISSUE" in surface.comment_body
