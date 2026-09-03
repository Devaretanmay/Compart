/// which files and lines need attention, what changed upstream, and what
/// contract tests should be synthesized — everything a patch-generating agent
/// needs to do its job correctly.
pub mod contracts;
pub mod evidence;
pub mod git_replay;
pub mod inventory;
pub mod manifest_lockfile;
pub mod patcher;
mod planner;
pub mod policy;
pub mod replay;
pub mod report;
pub mod resolver;
pub mod trials;
pub mod trials_v2;
mod types;
pub mod workflow;

pub use contracts::synthesize_contract_tests;
pub use evidence::{
    collect_environment_diagnostics, compare_diffs_semantically, CausalReplayClassification,
    CommandExecutionRecord, EnvironmentDiagnostics, ReplayEvidence, SemanticDiffMatch,
};
pub use git_replay::{
    execute_git_history_replay, get_available_git_replay_cases, GitReplayCase,
    GitReplayExecutionReport,
};
pub use inventory::{render_inventory, run_inventory, DepHealth, DiscoveredDep, Inventory};
pub use manifest_lockfile::{
    detect_package_manager, parse_cargo_lock, parse_package_json_manifest, parse_package_lock_json,
    parse_pnpm_lock, parse_yarn_lock, resolve_dependency, PackageManager, ResolvedDependency,
};
pub use patcher::{apply_patch_to_source, generate_unified_diff, patch_plan_targets, PatchResult};
pub use planner::plan_maintenance;
pub use policy::{SafetyDecision, SafetyPolicy};
pub use replay::{
    execute_historical_replay, get_available_replay_cases, HistoricalReplayCase, ReplayAuditReport,
};
pub use report::{render_markdown, render_trust_report_cli};
pub use trials::{run_compart_trials, CaseResult, TrialsReport};
pub use trials_v2::{
    historical_benchmark_cases, run_compart_trials_v2, HistoricalTrialCase, TrialCaseV2Result,
    TrialVerificationStatus, TrialsV2Summary,
};
pub use types::{
    AffectedCallsite, ImpactState, ImpactedEndpoint, MaintenancePlan, PatchTarget, PlanStatus,
    UncertaintyReason, UnresolvedCallsite, VerificationOutcome, VerificationSpec,
};
pub use workflow::{execution_order, parse_workflow, validate_workflow, WorkflowDef};
