# Compart Trials v2: Ground Truth API Migration Benchmark

Compart Trials v2 evaluates autonomous code maintenance engines against verified historical API migrations from real GitHub repositories.

## Guiding Principle

> **Compart prefers a transparent refusal to an unsafe automated change.**
>
> The final objective is not to maximize the raw count of generated pull requests. The objective is to maximize **trusted, verified, autonomous maintenance**.

---

## Benchmark Structure

### Ground Truth Verification Standard

Every case in Compart Trials v2 must be independently verifiable against primary historical sources:
1. Public repository commit pair (T0 pre-migration and T1 post-migration).
2. Merged pull request or authored migration commit by human maintainers.
3. Upstream OpenAPI specification diff or official vendor migration guide.

Cases lacking pinned commit pairs or verifiable diffs are classified as `RejectedUnverified` and strictly excluded from official benchmark scores.

### Qualification States
- `VerifiedGroundTruth`: Pinned commit pair, verified vendor spec, verified human patch.
- `RejectedUnverified`: Speculative or unpinned migration candidate. Excluded from scoring.

---

## 10 Clinical Metrics

1. **Detection Recall**: Fraction of truly breaking API operations detected.
2. **Impact Precision**: Confirmed affected callsites divided by resolvable callsites.
3. **False Positive Rate**: Unaffected callsites in affected files rejected divided by resolvable callsites.
4. **File Precision**: True positive modified files divided by total modified files.
5. **File Recall**: True positive modified files divided by expected changed files.
6. **Patch Semantic Correctness**: AST transforms that reproduce human ground truth semantics without regressions.
7. **Test Preservation Rate**: Test suites that continue to pass without breaks on unaffected tests.
8. **Ground Truth Similarity**: Exact match between Compart synthesized patches and human PRs.
9. **Autonomous Acceptance Rate**: PRs qualifying for merge under the central SafetyPolicy.
10. **Unsafe Patch Count**: Modifications emitted on unresolved or unverified targets (Must be 0).

---

## Running the Benchmark

```bash
# Run Trials v2 historical benchmark suite
compart trials --version 2

# Filter by provider
compart trials --version 2 --provider stripe

# Run single case by ID
compart trials --version 2 --case anthropic-messages-api-migration

# Machine-readable output
compart trials --version 2 --json
```

## Results

Detailed machine-readable output is automatically saved to:
- `trials/results/trials_v2_report.json`
- `trials/results/trials_v2_report.md`
