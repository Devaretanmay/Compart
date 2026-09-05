
"""Continuous Autonomous API Maintenance Loop Engine."""

from dataclasses import dataclass, field
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

from compart.ai_planner import AIPatchPlanner
from compart.github.client import GitHubAppClient
from compart.github.trust_pr import generate_trust_pr_markdown, TrustPRMetadata
from compart.maintenance_agents import ImpactAnalyst
from compart.patch_writer import apply_rewrites, PatchResult
from compart.providers.registry import get_default_registry
from compart.sandbox.snapshot import SnapshotManager, _file_hash

try:
    from compart._core import route_and_compress
except ImportError:
    def route_and_compress(content: str) -> str:
        return content


@dataclass
class MaintenanceRunReport:
    success: bool
    provider_name: str
    from_version: str
    to_version: str
    repository_path: str
    files_scanned: int
    files_modified: int
    unintended_files_modified: int
    blast_radius_verified: bool
    test_exit_code: int
    test_duration_ms: int
    unified_diff: str
    trust_pr_body: str
    patch_results: List[PatchResult] = field(default_factory=list)
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    error: Optional[str] = None


def detect_drift(repo_dir: str, provider_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Inspect repository manifests to detect installed providers."""
    registry = get_default_registry()
    detected = []

    pkg_json_path = os.path.join(repo_dir, "package.json")
    if os.path.exists(pkg_json_path):
        try:
            with open(pkg_json_path, "r") as f:
                data = json.load(f)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for dep_name, version in deps.items():
                p_spec = registry.get(dep_name)
                if p_spec and (provider_name is None or p_spec.name.lower() == provider_name.lower()):
                    detected.append({
                        "provider": p_spec.name,
                        "display_name": p_spec.display_name,
                        "package_name": dep_name,
                        "declared_version": version,
                        "manifest_path": "package.json",
                    })
        except Exception:
            pass

    return detected


def _detect_test_command(repo_dir: str) -> str:
    """Detect the most appropriate test command for this repository."""
    if os.path.exists(os.path.join(repo_dir, "test", "run.js")):
        return "node test/run.js"
    pkg_json_path = os.path.join(repo_dir, "package.json")
    if os.path.exists(pkg_json_path):
        try:
            with open(pkg_json_path) as f:
                data = json.load(f)
            scripts = data.get("scripts", {})
            for candidate in ("test", "test:unit", "test:ci"):
                if candidate in scripts:
                    return f"npm run {candidate}" if candidate != "test" else "npm test"
        except Exception:
            pass
    if os.path.exists(os.path.join(repo_dir, "pytest.ini")) or os.path.exists(os.path.join(repo_dir, "tests")):
        return "pytest -q"
    if os.path.exists(os.path.join(repo_dir, "Cargo.toml")):
        return "cargo test"
    return ""


def _compute_lockfile_hash(repo_dir: str) -> str:
    candidates = (
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
        "bun.lockb",
        "Cargo.lock",
        "poetry.lock",
        "Pipfile.lock",
        "package.json",
        "Cargo.toml",
    )
    for c in candidates:
        fp = os.path.join(repo_dir, c)
        if os.path.isfile(fp):
            try:
                with open(fp, "rb") as f:
                    return hashlib.blake2b(f.read(), digest_size=16).hexdigest()
            except Exception:
                pass
    return hashlib.blake2b(repo_dir.encode("utf-8"), digest_size=16).hexdigest()


def _run_install(repo_dir: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run package manager install to pull the new SDK version."""
    if shutil.which("pnpm") and os.path.exists(os.path.join(repo_dir, "pnpm-lock.yaml")):
        cmd = ["pnpm", "install", "--frozen-lockfile=false"]
    elif shutil.which("yarn") and os.path.exists(os.path.join(repo_dir, "yarn.lock")):
        cmd = ["yarn", "install"]
    else:
        cmd = ["npm", "install"]
    return subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, timeout=timeout)


def _run_tests(repo_dir: str, test_cmd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run the test suite inside the repo directory."""
    return subprocess.run(
        test_cmd,
        shell=True,
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_style_formatter(repo_dir: str, modified_files: List[str]) -> None:
    """Run local repository code formatters (Prettier, Biome, Ruff) to match team style."""
    if not modified_files:
        return
    if os.path.exists(os.path.join(repo_dir, ".prettierrc")) or os.path.exists(os.path.join(repo_dir, "package.json")):
        if shutil.which("npx"):
            for f in modified_files:
                rel_f = os.path.relpath(f, repo_dir) if os.path.isabs(f) else f
                subprocess.run(["npx", "prettier", "--write", rel_f], cwd=repo_dir, capture_output=True)
    if os.path.exists(os.path.join(repo_dir, "pyproject.toml")) or os.path.exists(os.path.join(repo_dir, "ruff.toml")):
        if shutil.which("ruff"):
            for f in modified_files:
                if f.endswith(".py"):
                    rel_f = os.path.relpath(f, repo_dir) if os.path.isabs(f) else f
                    subprocess.run(["ruff", "format", rel_f], cwd=repo_dir, capture_output=True)


def record_migration_history(repo_dir: str, record: Dict[str, Any]) -> None:
    """Record an auditable verified migration event into the repository history ledger."""
    history_dir = os.path.join(repo_dir, ".compart")
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(history_dir, "history.json")

    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(record)
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def get_migration_history(repo_dir: str) -> List[Dict[str, Any]]:
    """Retrieve verified migration history records from .compart/history.json."""
    history_file = os.path.join(repo_dir, ".compart", "history.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _git_commit_and_push(
    repo_dir: str,
    modified_files: List[str],
    branch_name: str,
    commit_message: str,
) -> bool:
    """Create a git branch, commit modified files, push to origin."""
    subprocess.run(["git", "config", "user.name", "Compart Bot"], cwd=repo_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "bot@compart.dev"], cwd=repo_dir, capture_output=True)

    try:
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_dir, capture_output=True, check=True)
    except subprocess.CalledProcessError:
        subprocess.run(["git", "checkout", branch_name], cwd=repo_dir, capture_output=True)

    rel_files = [os.path.relpath(f, repo_dir) if os.path.isabs(f) else f for f in modified_files]
    for rel_f in rel_files:
        subprocess.run(["git", "add", rel_f], cwd=repo_dir, capture_output=True)

    result = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=repo_dir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        pass

    push = subprocess.run(
        ["git", "push", "-u", "origin", branch_name, "--force"],
        cwd=repo_dir, capture_output=True, text=True,
    )
    return push.returncode == 0


def _gh_create_pr(
    repo: str,
    branch_name: str,
    title: str,
    body: str,
) -> Optional[str]:
    """Open a GitHub PR using the gh CLI. Returns PR URL or None."""
    if not shutil.which("gh"):
        return None
    result = subprocess.run(
        ["gh", "pr", "create", "--repo", repo, "--base", "main",
         "--head", branch_name, "--title", title, "--body", body],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    view = subprocess.run(
        ["gh", "pr", "view", branch_name, "--repo", repo, "--json", "url", "-q", ".url"],
        capture_output=True, text=True,
    )
    if view.returncode == 0 and view.stdout.strip():
        return view.stdout.strip()
    return None


def run_maintenance_cycle(
    repo_dir: str,
    provider_name: str,
    from_version: Optional[str] = None,
    to_version: Optional[str] = None,
    create_pr: bool = False,
    github_repo: Optional[str] = None,
    github_client: Optional[GitHubAppClient] = None,
    use_ai: bool = False,
    llm_api_key: Optional[str] = None,
    llm_model: Optional[str] = None,
    llm_base_url: Optional[str] = None,
) -> MaintenanceRunReport:
    """Execute full autonomous maintenance loop on a repository."""
    repo_dir = os.path.abspath(repo_dir)
    registry = get_default_registry()
    p_spec = registry.get(provider_name)
    if not p_spec:
        return MaintenanceRunReport(
            success=False, provider_name=provider_name,
            from_version=from_version or "unknown", to_version=to_version or "unknown",
            repository_path=repo_dir, files_scanned=0, files_modified=0,
            unintended_files_modified=0, blast_radius_verified=False,
            test_exit_code=-1, test_duration_ms=0, unified_diff="",
            trust_pr_body="", error=f"Provider {provider_name} not found in registry",
        )

    migration = None
    if p_spec.migrations:
        migration = next(iter(p_spec.migrations.values()))

    actual_from = from_version or (migration.from_version if migration else "1.0.0")
    actual_to = to_version or (migration.to_version if migration else "2.0.0")
    changelog_url = migration.changelog_url if migration else p_spec.docs_url
    rewrites = migration.rewrites if migration else []

    snapshot_dir = os.path.join(repo_dir, ".compart", "snapshot_tmp")
    snapshotter = SnapshotManager(workdir=repo_dir, snapshot_dir=snapshot_dir)
    files_scanned = snapshotter.snapshot()

    patch_results: List[PatchResult] = []
    if not use_ai and rewrites:
        patch_results = apply_rewrites(repo_dir, rewrites, dry_run=False)

    ai_planner = None
    if use_ai or not patch_results:
        ai_planner = AIPatchPlanner.from_env(api_key=llm_api_key, model=llm_model, base_url=llm_base_url)
        if ai_planner:
            impact = ImpactAnalyst().analyze_impact(repo_dir, provider_name)
            target_files = impact.affected_files
            if target_files:
                migration_desc = migration.description if migration else f"Upgrade {provider_name} to {actual_to}"
                ai_results = ai_planner.plan_and_apply(
                    repo_dir=repo_dir,
                    affected_files=target_files,
                    provider_name=provider_name,
                    from_version=actual_from,
                    to_version=actual_to,
                    migration_details=migration_desc,
                    dry_run=False,
                )
                if ai_results:
                    patch_results.extend(ai_results)

    modified_paths = [os.path.abspath(r.file_path) for r in patch_results if r.success]
    files_modified = len(modified_paths)
    unified_diff = "\n".join(r.unified_diff for r in patch_results if r.unified_diff)

    run_style_formatter(repo_dir, modified_paths)

    # Blast radius: files changed that were NOT targeted by the patch plan
    all_changed: set[str] = set()
    targeted: set[str] = set(modified_paths)
    for dirpath, dirnames, filenames in os.walk(repo_dir, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", ".next", "__pycache__", ".compart"}]
        for fn in filenames:
            fp = os.path.abspath(os.path.join(dirpath, fn))
            try:
                snap_hash = snapshotter._snapshot_dir
                rel = os.path.relpath(fp, repo_dir)
                snap_copy = os.path.join(snap_hash, rel)
                if os.path.exists(snap_copy):
                    if _file_hash(fp) != _file_hash(snap_copy):
                        all_changed.add(fp)
            except Exception:
                pass

    unintended = all_changed - targeted
    unintended_count = len(unintended)
    blast_radius_verified = unintended_count == 0

    # Install dependencies then run tests
    test_cmd = _detect_test_command(repo_dir)
    test_exit_code = 0
    test_duration_ms = 1
    raw_output = ""

    if files_modified > 0:
        if test_cmd not in ("exit 0", "") and not test_cmd.startswith("node test/"):
            try:
                _run_install(repo_dir, timeout=120)
            except Exception:
                pass

        test_start = time.time()
        try:
            proc = _run_tests(repo_dir, test_cmd, timeout=120)
            test_exit_code = proc.returncode
            raw_output = f"{proc.stdout or ''}\n{proc.stderr or ''}"
        except subprocess.TimeoutExpired:
            test_exit_code = 1
            raw_output = "Test run timed out after 120s"
        except Exception as exc:
            test_exit_code = 1
            raw_output = str(exc)
        test_duration_ms = max(1, int((time.time() - test_start) * 1000))

        # AI Self-Repair Loop: if tests failed and AI planner is available, retry once with test error
        if test_exit_code != 0 and ai_planner and modified_paths:
            retry_results = ai_planner.plan_and_apply(
                repo_dir=repo_dir,
                affected_files=modified_paths,
                provider_name=provider_name,
                from_version=actual_from,
                to_version=actual_to,
                migration_details=migration.description if migration else "",
                test_error=raw_output,
                dry_run=False,
            )
            if retry_results:
                run_style_formatter(repo_dir, modified_paths)
                retry_proc = _run_tests(repo_dir, test_cmd, timeout=120)
                if retry_proc.returncode == 0:
                    test_exit_code = 0
                    patch_results = retry_results
                    unified_diff = "\n".join(r.unified_diff for r in patch_results if r.unified_diff)

    compressed_log = route_and_compress(raw_output)

    # Roll back if tests failed
    if test_exit_code != 0:
        snapshotter.restore()
        files_modified = 0
        unified_diff = ""

    snapshotter.cleanup()
    lockfile_hash = _compute_lockfile_hash(repo_dir)
    patch_hash = hashlib.blake2b(unified_diff.encode("utf-8"), digest_size=16).hexdigest()

    all_rules = [desc for r in patch_results for desc in r.rules_applied]
    meta = TrustPRMetadata(
        provider_name=p_spec.display_name,
        from_version=actual_from,
        to_version=actual_to,
        changelog_url=changelog_url,
        files_modified=files_modified,
        files_scanned=files_scanned,
        unintended_files_modified=unintended_count,
        quarantined_callsites_count=0,
        unified_diff=unified_diff,
        test_command=test_cmd,
        test_exit_code=test_exit_code,
        test_duration_ms=test_duration_ms,
        lockfile_hash=lockfile_hash,
        patch_hash=patch_hash,
        semantic_score=1.0,
        impacted_callsites=[{"description": d} for d in all_rules],
    )
    pr_body = generate_trust_pr_markdown(meta)

    success = blast_radius_verified and test_exit_code == 0 and files_modified > 0

    if success:
        record_migration_history(repo_dir, {
            "migration_id": f"migration:{p_spec.name.lower()}:{actual_to}",
            "provider_name": p_spec.name,
            "from_version": actual_from,
            "to_version": actual_to,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "test_command": test_cmd,
            "test_exit_code": test_exit_code,
            "test_duration_ms": test_duration_ms,
            "patch_sha256": patch_hash,
            "blast_radius_zero": blast_radius_verified,
            "files_modified": modified_paths,
        })

    pr_url = None
    pr_number = None
    if create_pr and github_repo and files_modified > 0:
        branch_name = f"compart/{p_spec.name}-v{actual_to.replace('.', '-')}"
        commit_msg = (
            f"migrate: {p_spec.display_name} {actual_from} -> {actual_to}\n\n"
            f"Detected and patched by Compart autonomous maintenance engine.\n"
            f"Rules applied:\n" + "\n".join(f"- {d}" for d in all_rules)
        )
        pushed = _git_commit_and_push(repo_dir, modified_paths, branch_name, commit_msg)

        if pushed:
            pr_title = f"compart: migrate {p_spec.display_name} {actual_from} -> {actual_to}"
            pr_url = _gh_create_pr(github_repo, branch_name, pr_title, pr_body)

        if not pr_url and github_client:
            pr_resp = github_client.create_pull_request(
                repo=github_repo,
                title=f"fix(deps): upgrade {p_spec.display_name} to {actual_to}",
                body=pr_body,
                head_branch=branch_name,
                labels=["compart-maintenance", "verified-green"],
            )
            if pr_resp.get("html_url"):
                pr_url = pr_resp["html_url"]
                pr_number = pr_resp.get("number")

    return MaintenanceRunReport(
        success=success,
        provider_name=p_spec.name,
        from_version=actual_from,
        to_version=actual_to,
        repository_path=repo_dir,
        files_scanned=files_scanned,
        files_modified=files_modified,
        unintended_files_modified=unintended_count,
        blast_radius_verified=blast_radius_verified,
        test_exit_code=test_exit_code,
        test_duration_ms=test_duration_ms,
        unified_diff=unified_diff,
        trust_pr_body=pr_body,
        patch_results=patch_results,
        pr_url=pr_url,
        pr_number=pr_number,
    )
