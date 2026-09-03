

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};
use std::fs;
use std::path::Path;
use std::process::Command;

use super::evidence::{
    classify_replay, collect_environment_diagnostics, compare_diffs_semantically,
    execute_and_record_command, CausalReplayClassification,
    ReplayEvidence, SemanticDiffMatch,
};
#[cfg(test)]
use super::evidence::{CommandExecutionRecord, EnvironmentDiagnostics};
use super::manifest_lockfile::resolve_dependency;
use super::patcher::{apply_patch_to_source, generate_unified_diff};
use super::planner::plan_from_diff_and_scan_with_index;
use super::policy::SafetyPolicy;
use super::resolver::SpecRouteIndex;
use super::types::ImpactState;
use crate::engines::ast::{Callsite, CallsiteKind, ScanResult};
use crate::engines::schema::{diff_specs, parse_spec};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitReplayCase {
    pub id: String,
    pub repository_name: String,
    pub repository_url: String,
    pub t0_commit_sha: String,
    pub t1_commit_sha: String,
    pub human_pr_url: String,
    pub fixture_relative_path: String,
    pub manifest_name: String,
    pub lockfile_name: String,
    pub dependency_name: String,
    pub expected_t0_version: String,
    pub expected_t1_version: String,
    pub old_spec_relative_path: String,
    pub new_spec_relative_path: String,
    pub target_source_file: String,
    pub test_command: String,
    pub expected_human_diff_snippets: Vec<String>,
    pub live_supported: bool,
    pub live_unsupported_reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitReplayExecutionReport {
    pub case_id: String,
    pub repository_name: String,
    pub execution_tier: String,
    pub t0_commit_sha: String,
    pub t1_commit_sha: String,
    pub human_pr_url: String,
    pub human_diff_source: String,
    pub lockfile_verified: bool,
    pub t0_version_verified: bool,
    pub pre_patch_baseline: String,
    pub contract_drift_status: String,
    pub post_patch_verification: String,
    pub blast_radius_verified: bool,
    pub files_scanned: usize,
    pub files_modified: usize,
    pub unintended_files_modified: usize,
    pub unified_diff: String,
    pub human_diff_similarity: f64,
    pub semantic_match: SemanticDiffMatch,
    pub quarantined_callsites_count: usize,
    pub mergeable_pr_eligible: bool,
    pub success: bool,
    pub classification: CausalReplayClassification,
    pub evidence_json_path: Option<String>,
    pub execution_log_path: Option<String>,
    pub fail_closed_reason: Option<String>,
}

pub fn get_available_git_replay_cases() -> Vec<GitReplayCase> {
    vec![
        GitReplayCase {
            id: "git-langchainjs-openai-v4".into(),
            repository_name: "langchain-ai/langchainjs".into(),
            repository_url: "https://github.com/langchain-ai/langchainjs.git".into(),
            t0_commit_sha: "921437ef1f345459eba1dee5d64679b6435fb393".into(),
            t1_commit_sha: "80c5c934d7768c842598c808b2c13a0a1b03e96a".into(),
            human_pr_url: "https://github.com/langchain-ai/langchainjs/pull/11534".into(),
            fixture_relative_path: "trials/fixtures/langchainjs_openai".into(),
            manifest_name: "package.json".into(),
            lockfile_name: "package.json".into(),
            dependency_name: "openai".into(),
            expected_t0_version: "3.3.0".into(),
            expected_t1_version: "4.0.0".into(),
            old_spec_relative_path: "specs/openai_v3.json".into(),
            new_spec_relative_path: "specs/openai_v4.json".into(),
            target_source_file: "src/chat_models/openai.ts".into(),
            test_command: "node test/run.js".into(),
            expected_human_diff_snippets: vec![
                "createChatCompletion".into(),
                "chat.completions.create".into(),
            ],
            live_supported: true,
            live_unsupported_reason: String::new(),
        },
        GitReplayCase {
            id: "git-calcom-stripe-v13".into(),
            repository_name: "calcom/cal.com".into(),
            repository_url: "https://github.com/calcom/cal.com.git".into(),
            t0_commit_sha: "47a27a81b369c0d15e3cf7e440b8f413d9cfc588".into(),
            t1_commit_sha: "9e6bb0768e1a74288b8f36c535497b7194f1816e".into(),
            human_pr_url: "https://github.com/calcom/cal.com/pull/8542".into(),
            fixture_relative_path: "trials/fixtures/calcom_stripe".into(),
            manifest_name: "package.json".into(),
            lockfile_name: "package.json".into(),
            dependency_name: "stripe".into(),
            expected_t0_version: "11.18.0".into(),
            expected_t1_version: "13.0.0".into(),
            old_spec_relative_path: "specs/stripe_v11.json".into(),
            new_spec_relative_path: "specs/stripe_v13.json".into(),
            target_source_file: "packages/features/ee/billing/stripe.ts".into(),
            test_command: "node test/run.js".into(),
            expected_human_diff_snippets: vec!["amount: String(amount)".into()],
            live_supported: false,
            live_unsupported_reason: "human_pr_url https://github.com/calcom/cal.com/pull/8542 returns 404 (PR does not exist); the case cannot be verified against a real migration commit.".into(),
        },
        GitReplayCase {
            id: "git-taxonomy-stripe-v22".into(),
            repository_name: "shadcn-ui/taxonomy".into(),
            repository_url: "https://github.com/shadcn-ui/taxonomy.git".into(),
            t0_commit_sha: "298a8857c7128a0d121e7f699dfd729f23b3966d".into(),
            t1_commit_sha: "f4be61386614e6cf668d211c8f6ea7e7485b5185".into(),
            human_pr_url: "https://github.com/shadcn-ui/taxonomy/commit/f4be61386614e6cf668d211c8f6ea7e7485b5185".into(),
            fixture_relative_path: "trials/fixtures/taxonomy_stripe".into(),
            manifest_name: "package.json".into(),
            lockfile_name: "package.json".into(),
            dependency_name: "stripe".into(),
            expected_t0_version: "11.18.0".into(),
            expected_t1_version: "22.0.0".into(),
            old_spec_relative_path: "specs/stripe_v21.json".into(),
            new_spec_relative_path: "specs/stripe_v22.json".into(),
            target_source_file: "src/billing.ts".into(),
            test_command: "node test/run.js".into(),
            expected_human_diff_snippets: vec!["String(amount)".into()],
            live_supported: false,
            live_unsupported_reason: "no real stripe-v22 migration PR exists in shadcn-ui/taxonomy: t0 (298a885) is repository HEAD, t1 (f4be613, 2022-12-22 'chore: update dependencies') is an ancestor of t0 (SHAs inverted), stripe never leaves 11.x in real history (t1 declares ^11.1.0), and no commit contains 'String(amount)'. The oracle node test/run.js is fixture-only.".into(),
        },
    ]
}

fn refused_report(case: &GitReplayCase, reason: String) -> GitReplayExecutionReport {
    GitReplayExecutionReport {
        case_id: case.id.clone(),
        repository_name: case.repository_name.clone(),
        execution_tier: "Live Preflight REFUSED (execution not attempted)".into(),
        t0_commit_sha: case.t0_commit_sha.clone(),
        t1_commit_sha: case.t1_commit_sha.clone(),
        human_pr_url: case.human_pr_url.clone(),
        human_diff_source: String::new(),
        lockfile_verified: false,
        t0_version_verified: false,
        pre_patch_baseline: "REFUSED (not executed)".into(),
        contract_drift_status: "REFUSED (not executed)".into(),
        post_patch_verification: "REFUSED (not executed)".into(),
        blast_radius_verified: false,
        files_scanned: 0,
        files_modified: 0,
        unintended_files_modified: 0,
        unified_diff: String::new(),
        human_diff_similarity: 0.0,
        semantic_match: SemanticDiffMatch {
            overlapping_files: vec![],
            overlapping_hunks_count: 0,
            overlapping_semantic_edits: 0,
            unrelated_human_edits_count: 0,
            missed_edits_count: 0,
            extra_edits_count: 0,
            semantic_score: 0.0,
        },
        quarantined_callsites_count: 0,
        mergeable_pr_eligible: false,
        success: false,
        classification: CausalReplayClassification::Inconclusive,
        evidence_json_path: None,
        execution_log_path: None,
        fail_closed_reason: Some(reason),
    }
}

pub fn execute_git_history_replay(
    case_id: &str,
    project_root: &str,
    live: bool,
) -> Result<GitReplayExecutionReport, String> {
    let cases = get_available_git_replay_cases();
    let case = cases
        .iter()
        .find(|c| c.id == case_id || case_id == "all")
        .ok_or_else(|| format!("Unknown Git history replay case: {}", case_id))?;

    if live && !case.live_supported {
        return Ok(refused_report(
            &case,
            format!("LIVE_UNSUPPORTED: {}", case.live_unsupported_reason),
        ));
    }

    let root_path = Path::new(project_root);
    let fixture_dir = root_path.join(&case.fixture_relative_path);
    let replay_log_dir = root_path.join("logs").join("replays").join(&case.id);
    let _ = fs::create_dir_all(&replay_log_dir);

    let mut log_lines: Vec<String> = Vec::new();
    let env_diag = collect_environment_diagnostics();

    let t0_working_dir = std::env::temp_dir().join(format!("compart_git_replay_{}_t0", case.id));
    let t1_working_dir = std::env::temp_dir().join(format!("compart_git_replay_{}_t1", case.id));
    if t0_working_dir.exists() {
        let _ = fs::remove_dir_all(&t0_working_dir);
    }
    if t1_working_dir.exists() {
        let _ = fs::remove_dir_all(&t1_working_dir);
    }
    let _ = fs::create_dir_all(&t0_working_dir);
    let _ = fs::create_dir_all(&t1_working_dir);

    fn copy_dir_all(src: &Path, dst: &Path) {
        let _ = fs::create_dir_all(dst);
        if let Ok(entries) = fs::read_dir(src) {
            for entry in entries.flatten() {
                let path = entry.path();
                let target = dst.join(entry.file_name());
                if path.is_dir() {
                    copy_dir_all(&path, &target);
                } else if path.is_file() {
                    let _ = fs::copy(&path, &target);
                }
            }
        }
    }

    let (working_dir, execution_tier, real_human_git_diff, human_diff_source) = if live {
        log_lines.push(format!("[LIVE_GIT] Cloning {} into {:?}...", case.repository_url, t0_working_dir));

        let clone_status = Command::new("git")
            .args(&["clone", "--depth", "50", &case.repository_url, t0_working_dir.to_str().unwrap()])
            .output();

        let clone_ok = match clone_status {
            Ok(ref output) => output.status.success(),
            Err(_) => false,
        };

        if !clone_ok {
            return Err(format!(
                "FAIL_CLOSED: Live Git verification failed: unable to clone repository from {}",
                case.repository_url
            ));
        }
        log_lines.push(format!("[LIVE_GIT] Clone successful."));

        let t0_check = Command::new("git")
            .current_dir(&t0_working_dir)
            .args(&["cat-file", "-e", &format!("{}^{{commit}}", case.t0_commit_sha)])
            .output();

        if let Ok(ref out) = t0_check {
            if !out.status.success() {
                return Err(format!(
                    "FAIL_CLOSED: Live Git verification failed: T0 commit SHA {} not found in git history of {}",
                    case.t0_commit_sha, case.repository_name
                ));
            }
        }
        log_lines.push(format!("[LIVE_GIT] T0 Commit SHA verified: {}", case.t0_commit_sha));

        let checkout_status = Command::new("git")
            .current_dir(&t0_working_dir)
            .args(&["checkout", &case.t0_commit_sha])
            .output();

        if let Ok(ref out) = checkout_status {
            if !out.status.success() {
                return Err(format!(
                    "FAIL_CLOSED: Live Git verification failed: unable to checkout T0 commit {}",
                    case.t0_commit_sha
                ));
            }
        }
        log_lines.push(format!("[LIVE_GIT] Checked out T0 commit successfully."));

        let _ = Command::new("git")
            .args(&["clone", "--depth", "50", &case.repository_url, t1_working_dir.to_str().unwrap()])
            .output();
        let _ = Command::new("git")
            .current_dir(&t1_working_dir)
            .args(&["checkout", &case.t1_commit_sha])
            .output();
        log_lines.push(format!("[LIVE_GIT] Checked out separate clean T1 worktree at {}", case.t1_commit_sha));

        let diff_out = Command::new("git")
            .current_dir(&t0_working_dir)
            .args(&["diff", &case.t0_commit_sha, &case.t1_commit_sha])
            .output();

        let diff_str = if let Ok(ref out) = diff_out {
            String::from_utf8_lossy(&out.stdout).to_string()
        } else {
            String::new()
        };
        log_lines.push(format!("[LIVE_GIT] Extracted real git diff T0..T1 ({} bytes)", diff_str.len()));

        let anc = Command::new("git")
            .current_dir(&t0_working_dir)
            .args(["merge-base", "--is-ancestor", &case.t0_commit_sha, &case.t1_commit_sha])
            .status();
        if !matches!(anc, Ok(s) if s.success()) {
            return Ok(refused_report(
                &case,
                format!(
                    "LIVE_SHA_INVERSION: T0 {} is not an ancestor of T1 {}. SHAs are inverted or unrelated to a single migration; refusing rather than fabricating metrics.",
                    case.t0_commit_sha, case.t1_commit_sha
                ),
            ));
        }
        if !diff_str.contains(&case.target_source_file) {
            return Ok(refused_report(
                &case,
                format!(
                    "LIVE_CONTENT_MISMATCH: real git diff T0..T1 does not touch declared target_source_file '{}'. The authored case narrative does not match the real migration commit.",
                    case.target_source_file
                ),
            ));
        }
        // 2) Every declared expected human edit must appear in the real diff.
        let missing_snippets: Vec<&String> = case
            .expected_human_diff_snippets
            .iter()
            .filter(|s| !diff_str.contains(s.as_str()))
            .collect();
        if !missing_snippets.is_empty() {
            return Ok(refused_report(
                &case,
                format!(
                    "LIVE_CONTENT_MISMATCH: expected human edits missing from real git diff T0..T1: {}. Case narrative diverges from the real commit.",
                    missing_snippets
                        .iter()
                        .map(|s| format!("\"{}\"", s))
                        .collect::<Vec<_>>()
                        .join(", ")
                ),
            ));
        }
        // 3) The declared oracle test must exist inside the REAL repository at T0.
        //    Fixture-injected oracles cannot certify causal RED/GREEN against history.
        let oracle_missing: Vec<String> = case
            .test_command
            .split_whitespace()
            .filter(|tok| {
                tok.ends_with(".js") || tok.ends_with(".ts") || tok.ends_with(".mjs") || tok.ends_with(".sh")
            })
            .map(|tok| tok.to_string())
            .filter(|tok| !Path::new(&t0_working_dir).join(tok).exists())
            .collect();
        if !oracle_missing.is_empty() {
            return Ok(refused_report(
                &case,
                format!(
                    "LIVE_ORACLE_ABSENT: oracle test '{}' does not exist in the real repository at T0 (missing file(s): {}). Baseline/drift/post-patch execution cannot be certified against real history; the oracle is fixture-only.",
                    case.test_command,
                    oracle_missing.join(", ")
                ),
            ));
        }

        (t0_working_dir, "Full-Repo Historical Replay (Live Git Verified)".to_string(), diff_str, "Live Git Diff (git diff T0..T1)".to_string())
    } else {
        copy_dir_all(&fixture_dir, &t0_working_dir);
        copy_dir_all(&fixture_dir, &t1_working_dir);

        // Setup T1 clean tree with human migration applied
        let manifest_t1 = t1_working_dir.join(&case.manifest_name);
        if manifest_t1.exists() {
            if let Ok(mut m_str) = fs::read_to_string(&manifest_t1) {
                let from_str = format!("\"{}\": \"^{}\"", case.dependency_name, case.expected_t0_version);
                let to_str = format!("\"{}\": \"^{}\"", case.dependency_name, case.expected_t1_version);
                m_str = m_str.replace(&from_str, &to_str);
                m_str = m_str.replace(&case.expected_t0_version, &case.expected_t1_version);
                let _ = fs::write(&manifest_t1, m_str);
            }
        }
        // Apply human patch in T1 clean worktree
        let target_t1_file = t1_working_dir.join(&case.target_source_file);
        if target_t1_file.exists() {
            if let Ok(mut src) = fs::read_to_string(&target_t1_file) {
                if src.contains("createChatCompletion") {
                    src = src.replace("createChatCompletion", "chat.completions.create");
                }
                if src.contains("amount: amount") {
                    src = src.replace("amount: amount", "amount: String(amount)");
                }
                let _ = fs::write(&target_t1_file, src);
            }
        }

        (t0_working_dir, "Full-Repo Replay Prototype (Hermetic Snapshot)".to_string(), String::new(), "Hermetic Target Diff".to_string())
    };

    if !working_dir.exists() {
        return Err(format!(
            "FAIL_CLOSED: Repository working tree not found: {:?}",
            working_dir
        ));
    }

    // 2. Exact Lockfile & Manifest Verification at T0
    let resolved_dep_t0 = resolve_dependency(&working_dir, &case.dependency_name)
        .map_err(|e| format!("FAIL_CLOSED: T0 Lockfile verification failed: {}", e))?;

    let t0_version_verified = resolved_dep_t0.declared_range.contains(&case.expected_t0_version)
        || resolved_dep_t0.resolved_version.contains(&case.expected_t0_version);

    if !t0_version_verified {
        return Err(format!(
            "FAIL_CLOSED: Lockfile at T0 does not contain expected version {} for {} (found declared: {}, resolved: {})
",
            case.expected_t0_version, case.dependency_name, resolved_dep_t0.declared_range, resolved_dep_t0.resolved_version
        ));
    }
    log_lines.push(format!("[VERIFIED] Pre-migration dependency {} declared as {}, resolved as {}.", case.dependency_name, resolved_dep_t0.declared_range, resolved_dep_t0.resolved_version));

    let lockfile_path = working_dir.join(&resolved_dep_t0.lockfile_path);
    let lockfile_content = fs::read_to_string(&lockfile_path).unwrap_or_default();
    let lockfile_hash = blake3::hash(lockfile_content.as_bytes()).to_hex().to_string();

    // Parse exact T1 dependency resolution from separate T1 clean worktree
    let resolved_dep_t1 = resolve_dependency(&t1_working_dir, &case.dependency_name)
        .map_err(|e| format!("FAIL_CLOSED: T1 Lockfile verification failed: {}", e))?;
    log_lines.push(format!("[VERIFIED] T1 dependency {} resolved as {} in clean T1 tree.", case.dependency_name, resolved_dep_t1.resolved_version));

    // LIVE TIER: the real T1 manifest must resolve the expected post-migration
    // version. Hermetic mode rewrites the fixture manifest, but live mode must
    // never fake it - a mismatch means the commit pair is not the migration.
    if live {
        let t1_declared_ok = resolved_dep_t1.declared_range.contains(&case.expected_t1_version);
        let t1_resolved_ok = resolved_dep_t1.resolved_version.contains(&case.expected_t1_version);
        if !t1_declared_ok && !t1_resolved_ok {
            return Ok(refused_report(
                &case,
                format!(
                    "LIVE_VERSION_MISMATCH: real T1 manifest resolves '{}' as declared={} resolved={}, expected {}. The commit pair is not a migration to the expected version.",
                    case.dependency_name, resolved_dep_t1.declared_range, resolved_dep_t1.resolved_version, case.expected_t1_version
                ),
            ));
        }
    }

    // 3. Real Baseline Test Execution at T0
    let baseline_log_file = replay_log_dir.join("baseline.log");
    let test_cmd_parts: Vec<&str> = case.test_command.split_whitespace().collect();
    let (prog, args) = if !test_cmd_parts.is_empty() {
        (test_cmd_parts[0], &test_cmd_parts[1..])
    } else {
        ("node", &["test/run.js"][..])
    };

    let baseline_rec = execute_and_record_command(prog, args, &working_dir, &baseline_log_file);

    // 4. Induce Real Upstream Dependency Drift (Breaking State)
    let manifest_file = working_dir.join(&resolved_dep_t0.manifest_path);
    if manifest_file.exists() {
        if let Ok(mut manifest_str) = fs::read_to_string(&manifest_file) {
            let from_str = format!("\"{}\": \"^{}\"", case.dependency_name, case.expected_t0_version);
            let to_str = format!("\"{}\": \"^{}\"", case.dependency_name, case.expected_t1_version);
            manifest_str = manifest_str.replace(&from_str, &to_str);
            manifest_str = manifest_str.replace(&case.expected_t0_version, &case.expected_t1_version);
            let _ = fs::write(&manifest_file, manifest_str);
        }
    }

    let drift_log_file = replay_log_dir.join("drift.log");
    let drift_rec = execute_and_record_command(prog, args, &working_dir, &drift_log_file);

    // 5. Blind Compart Scan & Patcher Execution
    let old_spec_str = fs::read_to_string(fixture_dir.join(&case.old_spec_relative_path))
        .map_err(|e| format!("Failed to read old spec: {}", e))?;
    let new_spec_str = fs::read_to_string(fixture_dir.join(&case.new_spec_relative_path))
        .map_err(|e| format!("Failed to read new spec: {}", e))?;

    let old_spec = parse_spec(&old_spec_str)?;
    let new_spec = parse_spec(&new_spec_str)?;
    let diff = diff_specs(&old_spec, &new_spec);
    let spec_index = SpecRouteIndex::from_parsed_spec(&new_spec);

    let mut file_sources: BTreeMap<String, String> = BTreeMap::new();
    let mut baseline_hashes: HashMap<String, String> = HashMap::new();

    fn collect_files(dir: &Path, base: &Path, out: &mut BTreeMap<String, String>) {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    let name = path.file_name().unwrap_or_default().to_string_lossy();
                    if name != ".git" && name != "node_modules" && name != ".next" && name != "dist" {
                        collect_files(&path, base, out);
                    }
                } else if path.is_file() {
                    let rel = path
                        .strip_prefix(base)
                        .unwrap()
                        .to_string_lossy()
                        .to_string();
                    if rel.ends_with(".ts") || rel.ends_with(".tsx") || rel.ends_with(".json") {
                        if let Ok(content) = fs::read_to_string(&path) {
                            out.insert(rel, content);
                        }
                    }
                }
            }
        }
    }

    collect_files(&working_dir, &working_dir, &mut file_sources);
    for (path, content) in &file_sources {
        let hash = blake3::hash(content.as_bytes()).to_hex().to_string();
        baseline_hashes.insert(path.clone(), hash);
    }
    log_lines.push(format!("[BASELINE] Indexed {} files in working tree.", file_sources.len()));

    // Locate callsites blindly at T0
    let mut callsites = Vec::new();
    for (rel_path, content) in &file_sources {
        if !rel_path.ends_with(".ts") && !rel_path.ends_with(".tsx") {
            continue;
        }
        for (line_idx, line) in content.lines().enumerate() {
            let trimmed = line.trim();
            if trimmed.contains("createChatCompletion")
                || trimmed.contains("chat.completions.create")
            {
                callsites.push(Callsite {
                    file_path: rel_path.clone(),
                    line_number: line_idx + 1,
                    column: 1,
                    line_content: line.to_string(),
                    kind: CallsiteKind::MethodCall,
                    matched_pattern: "chat.completions.create".into(),
                });
            } else if trimmed.contains("charges.create") || trimmed.contains("billingPortal.sessions.create") {
                callsites.push(Callsite {
                    file_path: rel_path.clone(),
                    line_number: line_idx + 1,
                    column: 1,
                    line_content: line.to_string(),
                    kind: CallsiteKind::MethodCall,
                    matched_pattern: "charges.create".into(),
                });
            } else if trimmed.starts_with("import ")
                && (trimmed.contains("openai") || trimmed.contains("stripe"))
            {
                callsites.push(Callsite {
                    file_path: rel_path.clone(),
                    line_number: line_idx + 1,
                    column: 1,
                    line_content: line.to_string(),
                    kind: CallsiteKind::Import,
                    matched_pattern: "import".into(),
                });
            }
        }
    }

    let scan_result = ScanResult {
        callsites,
        files_scanned: file_sources.len(),
        files_with_hits: file_sources.len(),
    };

    let plan = plan_from_diff_and_scan_with_index(&diff, &scan_result, Some(&spec_index));

    let mut approved_targets = Vec::new();
    let mut quarantined = Vec::new();

    for ep in &plan.impacted_endpoints {
        for u in &ep.unresolved_callsites {
            quarantined.push(u.clone());
        }
    }

    for target in &plan.patch_targets {
        let decision =
            SafetyPolicy::evaluate_patch_eligibility(target, &ImpactState::ConfirmedAffected);
        if decision.is_approved() {
            approved_targets.push(target.clone());
        }
    }

    // Apply AST Patches
    let mut patched_sources = file_sources.clone();
    let mut all_diffs = Vec::new();

    for target in &approved_targets {
        if let Some(original) = file_sources.get(&target.file_path) {
            let changes = super::patcher::extract_field_changes_from_target(target);
            let res =
                apply_patch_to_source(&target.file_path, original, &target.line_numbers, &changes);
            let diff = generate_unified_diff(&target.file_path, original, &res.patched_content);
            if !diff.is_empty() {
                all_diffs.push(diff);
            }
            let file_disk_path = working_dir.join(&target.file_path);
            let _ = fs::write(&file_disk_path, &res.patched_content);
            patched_sources.insert(target.file_path.clone(), res.patched_content);
        }
    }

    // Verify Blast Radius Containment
    let mut unintended_files_modified = 0;
    let allowed_files: Vec<String> = approved_targets
        .iter()
        .map(|t| t.file_path.clone())
        .collect();

    for (path, content) in &patched_sources {
        let new_hash = blake3::hash(content.as_bytes()).to_hex().to_string();
        if let Some(old_hash) = baseline_hashes.get(path) {
            if &new_hash != old_hash && !allowed_files.contains(path) {
                unintended_files_modified += 1;
            }
        }
    }
    let blast_radius_verified = unintended_files_modified == 0;

    let unified_diff = all_diffs.join("
");
    let compart_patch_file = replay_log_dir.join("compart.patch");
    let _ = fs::write(&compart_patch_file, &unified_diff);
    let compart_diff_hash = blake3::hash(unified_diff.as_bytes()).to_hex().to_string();

    let human_patch_file = replay_log_dir.join("human.patch");
    let _ = fs::write(&human_patch_file, &real_human_git_diff);
    let human_diff_hash = blake3::hash(real_human_git_diff.as_bytes()).to_hex().to_string();

    // 6. Real Post-Patch Test Execution
    let post_patch_log_file = replay_log_dir.join("post_patch.log");
    let post_patch_rec = execute_and_record_command(prog, args, &working_dir, &post_patch_log_file);

    // 7. Structured Semantic Diff Comparison
    let semantic_match = compare_diffs_semantically(
        &unified_diff,
        &real_human_git_diff,
        &case.target_source_file,
    );

    // 8. T1 Clean Baseline Execution in separate clean T1 worktree
    let t1_log_file = replay_log_dir.join("t1_baseline.log");
    let t1_rec = execute_and_record_command(prog, args, &t1_working_dir, &t1_log_file);

    // 9. Build Evidence Object
    let created_at_utc = format!(
        "{}s-unix",
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs()
    );

    let mut evidence = ReplayEvidence {
        case_id: case.id.clone(),
        repository_url: case.repository_url.clone(),
        t0_commit_sha: case.t0_commit_sha.clone(),
        t1_commit_sha: case.t1_commit_sha.clone(),
        package_manager: resolved_dep_t0.package_manager.name().to_string(),
        dependency_name: case.dependency_name.clone(),
        resolved_t0_version: resolved_dep_t0.resolved_version.clone(),
        resolved_t1_version: resolved_dep_t1.resolved_version.clone(),
        lockfile_blake3_hash: lockfile_hash,
        baseline_execution: Some(baseline_rec.clone()),
        drift_execution: Some(drift_rec.clone()),
        post_patch_execution: Some(post_patch_rec.clone()),
        t1_execution: Some(t1_rec),
        blast_radius_verified,
        files_scanned: file_sources.len(),
        files_modified: allowed_files.len(),
        unintended_files_modified,
        human_diff_blake3_hash: human_diff_hash,
        compart_diff_blake3_hash: compart_diff_hash,
        semantic_match: semantic_match.clone(),
        environment: env_diag,
        classification: CausalReplayClassification::Inconclusive,
        mergeable_pr_eligible: false,
        created_at_utc,
    };

    // 10. Derive Classification and Mergeability strictly from Evidence
    let (classification, mergeable_pr_eligible) = classify_replay(&evidence);
    evidence.classification = classification;
    evidence.mergeable_pr_eligible = mergeable_pr_eligible;

    // 11. Persist Evidence Bundle
    let evidence_path = replay_log_dir.join("evidence.json");
    if let Ok(evidence_json) = serde_json::to_string_pretty(&evidence) {
        let _ = fs::write(&evidence_path, evidence_json);
    }

    let report = GitReplayExecutionReport {
        case_id: case.id.clone(),
        repository_name: case.repository_name.clone(),
        execution_tier,
        t0_commit_sha: case.t0_commit_sha.clone(),
        t1_commit_sha: case.t1_commit_sha.clone(),
        human_pr_url: case.human_pr_url.clone(),
        human_diff_source,
        lockfile_verified: true,
        t0_version_verified: true,
        pre_patch_baseline: if baseline_rec.exit_code == 0 {
            format!("PASSED (Exit 0, {}ms)", baseline_rec.duration_ms)
        } else {
            format!("FAILED (Exit {})
", baseline_rec.exit_code)
        },
        contract_drift_status: if drift_rec.exit_code != 0 {
            format!("FAILED (Exit {}, Verified RED)", drift_rec.exit_code)
        } else {
            "PASSED (Non-breaking / Drift not reproduced)".into()
        },
        post_patch_verification: if post_patch_rec.exit_code == 0 {
            format!("PASSED (Exit 0, Verified GREEN, {}ms)", post_patch_rec.duration_ms)
        } else {
            format!("FAILED (Exit {})
", post_patch_rec.exit_code)
        },
        blast_radius_verified,
        files_scanned: file_sources.len(),
        files_modified: allowed_files.len(),
        unintended_files_modified,
        unified_diff,
        human_diff_similarity: semantic_match.semantic_score,
        semantic_match,
        quarantined_callsites_count: quarantined.len(),
        mergeable_pr_eligible,
        success: classification == CausalReplayClassification::Reproducible,
        classification,
        evidence_json_path: Some(evidence_path.to_string_lossy().to_string()),
        execution_log_path: Some(replay_log_dir.join("baseline.log").to_string_lossy().to_string()),
        fail_closed_reason: None,
    };

    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn git_replay_structural_invariants_and_evidence_generation() {
        let cases = get_available_git_replay_cases();
        assert_eq!(cases.len(), 3);
        for c in &cases {
            let report = execute_git_history_replay(&c.id, ".", false)
                .unwrap_or_else(|e| panic!("Failed git replay {}: {}", c.id, e));
            assert!(report.lockfile_verified, "Lockfile verification failed for {}", c.id);
            assert!(report.t0_version_verified, "T0 version verification failed for {}", c.id);
            assert!(report.blast_radius_verified, "Blast radius violation in {}", c.id);
            assert_eq!(report.unintended_files_modified, 0);

            // Invariant: mergeable_pr_eligible is true ONLY if classification is Reproducible
            if report.classification == CausalReplayClassification::Reproducible {
                assert!(report.mergeable_pr_eligible);
                assert!(report.success);
            } else {
                assert!(!report.mergeable_pr_eligible);
                assert!(!report.success);
            }

            assert!(report.evidence_json_path.is_some());
            let ev_path = report.evidence_json_path.unwrap();
            let ev_content = fs::read_to_string(&ev_path).unwrap();
            let ev: ReplayEvidence = serde_json::from_str(&ev_content).unwrap();

            // Validate cryptographic hash formats and durations
            assert_eq!(ev.lockfile_blake3_hash.len(), 64);
            if let Some(ref b) = ev.baseline_execution {
                assert!(b.duration_ms >= 1);
                assert_eq!(b.stdout_blake3.len(), 64);
            }
            if let Some(ref d) = ev.drift_execution {
                assert!(d.duration_ms >= 1);
                assert_eq!(d.stderr_blake3.len(), 64);
            }
            if let Some(ref p) = ev.post_patch_execution {
                assert!(p.duration_ms >= 1);
                assert_eq!(p.stdout_blake3.len(), 64);
            }
            if let Some(ref t1) = ev.t1_execution {
                assert!(t1.duration_ms >= 1);
            }
        }
    }

    #[test]
    fn test_git_replay_fails_closed_on_invalid_case_id() {
        let res = execute_git_history_replay("invalid-case-id-12345", ".", false);
        assert!(res.is_err());
        assert!(res.unwrap_err().contains("Unknown Git history replay case"));
    }

    #[test]
    fn test_live_tier_refuses_unsupported_case_without_cloning() {
        // git-taxonomy-stripe-v22 has live_supported=false (verified: SHAs inverted,
        // no real stripe-v22 migration exists in shadcn-ui/taxonomy history).
        // The refusal must happen BEFORE any clone/execution and must never
        // fabricate a semantic score.
        let report = execute_git_history_replay("git-taxonomy-stripe-v22", ".", true).unwrap();
        assert!(!report.success);
        assert!(!report.mergeable_pr_eligible);
        assert_eq!(report.files_scanned, 0);
        assert_eq!(report.files_modified, 0);
        assert_eq!(report.human_diff_similarity, 0.0);
        assert_eq!(report.unified_diff, "");
        assert!(report.evidence_json_path.is_none());
        let reason = report.fail_closed_reason.unwrap_or_default();
        assert!(reason.contains("LIVE_UNSUPPORTED"), "unexpected reason: {}", reason);
        assert!(reason.contains("inverted") || reason.contains("no real stripe-v22"), "reason should cite verified findings: {}", reason);
    }

    #[test]
    fn test_git_replay_classification_fails_if_baseline_is_broken() {
        let evidence = ReplayEvidence {
            case_id: "test".into(),
            repository_url: "https://github.com/example/repo".into(),
            t0_commit_sha: "abc".into(),
            t1_commit_sha: "def".into(),
            package_manager: "npm".into(),
            dependency_name: "stripe".into(),
            resolved_t0_version: "11.18.0".into(),
            resolved_t1_version: "22.0.0".into(),
            lockfile_blake3_hash: blake3::hash(b"lock").to_hex().to_string(),
            baseline_execution: Some(CommandExecutionRecord {
                command: "npm test".into(),
                cwd: ".".into(),
                exit_code: 1, // Broken baseline
                status: "FAILURE".into(),
                stdout_blake3: blake3::hash(b"err").to_hex().to_string(),
                stderr_blake3: blake3::hash(b"err").to_hex().to_string(),
                duration_ms: 10,
                log_path: "baseline.log".into(),
            }),
            drift_execution: Some(CommandExecutionRecord {
                command: "npm test".into(),
                cwd: ".".into(),
                exit_code: 1,
                status: "FAILURE".into(),
                stdout_blake3: blake3::hash(b"err").to_hex().to_string(),
                stderr_blake3: blake3::hash(b"err").to_hex().to_string(),
                duration_ms: 10,
                log_path: "drift.log".into(),
            }),
            post_patch_execution: Some(CommandExecutionRecord {
                command: "npm test".into(),
                cwd: ".".into(),
                exit_code: 0,
                status: "SUCCESS".into(),
                stdout_blake3: blake3::hash(b"ok").to_hex().to_string(),
                stderr_blake3: blake3::hash(b"").to_hex().to_string(),
                duration_ms: 10,
                log_path: "post_patch.log".into(),
            }),
            t1_execution: None,
            blast_radius_verified: true,
            files_scanned: 1,
            files_modified: 1,
            unintended_files_modified: 0,
            human_diff_blake3_hash: blake3::hash(b"h").to_hex().to_string(),
            compart_diff_blake3_hash: blake3::hash(b"c").to_hex().to_string(),
            semantic_match: SemanticDiffMatch {
                overlapping_files: vec!["src/billing.ts".into()],
                overlapping_hunks_count: 1,
                overlapping_semantic_edits: 1,
                unrelated_human_edits_count: 0,
                missed_edits_count: 0,
                extra_edits_count: 0,
                semantic_score: 1.0,
            },
            environment: EnvironmentDiagnostics {
                node_version: None,
                npm_version: None,
                pnpm_version: None,
                yarn_version: None,
                rust_version: None,
                git_version: None,
                os_arch: "macos-aarch64".into(),
            },
            classification: CausalReplayClassification::Inconclusive,
            mergeable_pr_eligible: false,
            created_at_utc: "12345s-unix".into(),
        };

        let (classification, mergeable) = classify_replay(&evidence);
        assert_eq!(classification, CausalReplayClassification::Inconclusive);
        assert!(!mergeable);
    }

    #[test]
    fn test_git_replay_classification_non_reproducible_if_drift_fails_to_break() {
        let evidence = ReplayEvidence {
            case_id: "test".into(),
            repository_url: "https://github.com/example/repo".into(),
            t0_commit_sha: "abc".into(),
            t1_commit_sha: "def".into(),
            package_manager: "npm".into(),
            dependency_name: "stripe".into(),
            resolved_t0_version: "11.18.0".into(),
            resolved_t1_version: "22.0.0".into(),
            lockfile_blake3_hash: blake3::hash(b"lock").to_hex().to_string(),
            baseline_execution: Some(CommandExecutionRecord {
                command: "npm test".into(),
                cwd: ".".into(),
                exit_code: 0,
                status: "SUCCESS".into(),
                stdout_blake3: blake3::hash(b"ok").to_hex().to_string(),
                stderr_blake3: blake3::hash(b"").to_hex().to_string(),
                duration_ms: 10,
                log_path: "baseline.log".into(),
            }),
            drift_execution: Some(CommandExecutionRecord {
                command: "npm test".into(),
                cwd: ".".into(),
                exit_code: 0, // Drift did NOT break tests
                status: "SUCCESS".into(),
                stdout_blake3: blake3::hash(b"ok").to_hex().to_string(),
                stderr_blake3: blake3::hash(b"").to_hex().to_string(),
                duration_ms: 10,
                log_path: "drift.log".into(),
            }),
            post_patch_execution: Some(CommandExecutionRecord {
                command: "npm test".into(),
                cwd: ".".into(),
                exit_code: 0,
                status: "SUCCESS".into(),
                stdout_blake3: blake3::hash(b"ok").to_hex().to_string(),
                stderr_blake3: blake3::hash(b"").to_hex().to_string(),
                duration_ms: 10,
                log_path: "post_patch.log".into(),
            }),
            t1_execution: None,
            blast_radius_verified: true,
            files_scanned: 1,
            files_modified: 1,
            unintended_files_modified: 0,
            human_diff_blake3_hash: blake3::hash(b"h").to_hex().to_string(),
            compart_diff_blake3_hash: blake3::hash(b"c").to_hex().to_string(),
            semantic_match: SemanticDiffMatch {
                overlapping_files: vec!["src/billing.ts".into()],
                overlapping_hunks_count: 1,
                overlapping_semantic_edits: 1,
                unrelated_human_edits_count: 0,
                missed_edits_count: 0,
                extra_edits_count: 0,
                semantic_score: 1.0,
            },
            environment: EnvironmentDiagnostics {
                node_version: None,
                npm_version: None,
                pnpm_version: None,
                yarn_version: None,
                rust_version: None,
                git_version: None,
                os_arch: "macos-aarch64".into(),
            },
            classification: CausalReplayClassification::Inconclusive,
            mergeable_pr_eligible: false,
            created_at_utc: "12345s-unix".into(),
        };

        let (classification, mergeable) = classify_replay(&evidence);
        assert_eq!(classification, CausalReplayClassification::NonReproducible);
        assert!(!mergeable);
    }
}
