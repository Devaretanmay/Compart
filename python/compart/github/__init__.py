"""Compart GitHub App & Webhook Integration Module."""

from .client import (
    GitHubAppClient,
    verify_webhook_signature,
)
from .trust_pr import generate_trust_pr_markdown, TrustPRMetadata
from .webhook_server import WebhookServer, handle_webhook_payload

__all__ = [
    "GitHubAppClient",
    "verify_webhook_signature",
    "generate_trust_pr_markdown",
    "TrustPRMetadata",
    "WebhookServer",
    "handle_webhook_payload",
    "handle_pull_request_event",
    "handle_external_change_event",
    "handle_installation_event",
    "render_day0_onboarding_issue",
    "make_pr_bot_handler",
    "run_on_pr_locally",
]


def __getattr__(name: str):
    if name in (
        "handle_pull_request_event",
        "handle_external_change_event",
        "handle_installation_event",
        "render_day0_onboarding_issue",
        "make_pr_bot_handler",
        "run_on_pr_locally",
    ):
        from . import pr_bot
        return getattr(pr_bot, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
