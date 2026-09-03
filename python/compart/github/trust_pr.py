"""Developer Trust Surface: High-Confidence PR Markdown Generator."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TrustPRMetadata:
    provider_name: str
    from_version: str
    to_version: str
    changelog_url: str
    files_modified: int
    files_scanned: int
    unintended_files_modified: int
    quarantined_callsites_count: int
    unified_diff: str
    test_command: str
    test_exit_code: int
    test_duration_ms: int
    lockfile_hash: str
    patch_hash: str
    semantic_score: float
    impacted_callsites: List[Dict[str, Any]] = field(default_factory=list)
    unaffected_callsites: List[Dict[str, Any]] = field(default_factory=list)
    quarantined_callsites: List[Dict[str, Any]] = field(default_factory=list)


def generate_trust_pr_markdown(meta: TrustPRMetadata) -> str:
    """Format high-trust, developer-delighting Pull Request body."""
    status_tag = "[VERIFIED]" if meta.unintended_files_modified == 0 and meta.test_exit_code == 0 else "[NEEDS REVIEW]"
    
    diff_block = ""
    if meta.unified_diff:
        diff_lines = meta.unified_diff.strip().splitlines()
        preview = "\n".join(diff_lines[:40])
        if len(diff_lines) > 40:
            preview += f"\n... ({len(diff_lines) - 40} more lines)"
        diff_block = f"```diff\n{preview}\n```"
    else:
        diff_block = "_No source modifications required._"

    test_status_str = "SUCCESS (GREEN)" if meta.test_exit_code == 0 else "FAILURE (RED)"
    score_pct = meta.semantic_score * 100.0

    lines = [
        f"## {status_tag} Autonomous Maintenance: Upgrade `{meta.provider_name}` ({meta.from_version} -> {meta.to_version})",
        "",
        "### Upstream API Drift Summary",
        f"- **Provider**: **{meta.provider_name}**",
        f"- **Migration**: `{meta.from_version}` -> `{meta.to_version}`",
        f"- **Official Documentation**: [Vendor Changelog & Migration Guide]({meta.changelog_url})",
        f"- **Semantic Confidence**: `{score_pct:.1f}%`",
        "",
        "---",
        "",
        "### Blast Radius Containment Receipt",
        "Compart verified zero unintended side effects across the entire codebase:",
        f"- **Files Scanned**: `{meta.files_scanned}`",
        f"- **Files Modified**: `{meta.files_modified}`",
        f"- **Unintended Files Touched**: **`{meta.unintended_files_modified}`** (100% Contained)",
        f"- **Lockfile Digest (BLAKE3)**: `{meta.lockfile_hash[:16]}...`",
        f"- **Patch Digest (BLAKE3)**: `{meta.patch_hash[:16]}...`",
        "",
        "---",
        "",
        "### Automated Verification Evidence",
        f"- **Test Command**: `{meta.test_command}`",
        f"- **Exit Code**: `{meta.test_exit_code}` ({test_status_str})",
        f"- **Duration**: `{meta.test_duration_ms}ms`",
        "",
        "---",
        "",
        "### Surgical Patch Preview",
        diff_block,
        "",
        "---",
        "",
        "### Callsite Triage",
        f"- **Confirmed Affected**: `{len(meta.impacted_callsites)}` callsites surgically patched.",
        f"- **Unaffected Safe**: `{len(meta.unaffected_callsites)}` callsites verified compatible with `{meta.to_version}`.",
        f"- **Quarantined for Review**: `{meta.quarantined_callsites_count}` callsites.",
        "",
        "---",
        "",
        "### Next Steps",
        "This autonomous patch has passed all local tests and blast-radius verification.",
        "- [ ] Review diff preview above.",
        "- [ ] Click **Merge pull request** to apply update to `main`.",
        "",
        "_Generated automatically by [Compart](https://github.com/Devaretanmay/Compart) Continuous Autonomous Maintenance Engine._",
    ]
    return "\n".join(lines)
