# Compart AutoPatch: Benchmark Baseline (Phase 0)

Date Recorded: 2026-09-02
Commit Environment: Local Development (macOS, Rust 1.85+, Python 3.14)

## Exact Observed Metrics

| Metric Category | Baseline Value | Source Command |
| :--- | :--- | :--- |
| **Rust Unit Tests** | 512 passed, 0 failed | `cargo test --lib` |
| **PyO3 FFI Check** | Clean compile (0 errors) | `cargo check --features pyo3-binding` |
| **Python SDK/CLI Tests** | 17 passed, 0 failed | `pytest tests/test_autopatch_sdk.py tests/test_autopatch_cli.py` |
| **Trials Benchmark Cases** | 3 cases (N=3 prototype) | `compart trials` |
| **Trials Cases Passed** | 3 / 3 (100.0%) | `compart trials` |
| **Total References Scanned** | 17 references | `compart trials` |
| **Confirmed Affected Callsites** | 3 callsites | `compart trials` |
| **False Positives Rejected** | 3 callsites | `compart trials` |
| **Unresolvable References** | 11 references | `compart trials` |
| **Impact Precision** | 50.0% (3 / (3 + 3)) | `compart trials` |
| **Surgical Patch Success** | 3 / 3 (100.0%) | `compart trials` |

## Per-Case Breakdown

```text
STATUS PROVIDER     MIGRATION                CONFIRM  REJECT   PRECISION  PATCH 
[PASS] Stripe       v22 Charges Type Drift   1        2        33.3     % YES   
[PASS] Anthropic    Claude Opus Sunset       1        0        100.0    % YES   
[PASS] Twilio       Regional Domain Sunset   1        1        50.0     % YES   
```

## Known Limitations of Baseline

1. **Small Sample Size**: The N=3 benchmark is a synthetic prototype suite, not statistically significant.
2. **Uncertainty is Opaque**: The 11 unresolvable references are aggregated as a flat number without typed taxonomy.
3. **Synthetic Specs & Fixtures**: Upstream OpenAPI specs and target repositories are locally synthesized fixtures rather than historical Git commits before and after real human migrations.
4. **No Behavioral Verification**: Patching is evaluated on mechanical string/AST transformation, not on preservation of actual application runtime behavior.
