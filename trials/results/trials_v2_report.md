# Compart Trials v2 Benchmark Report

**Date:** 2026-09-02  
**Total Cases Evaluated:** 5  
**Verified Ground Truth Cases:** 4  
**Excluded Unverified Cases:** 1  

## Aggregate Clinical Metrics

| Metric | Result | Description |
|---|---|---|
| Detection Recall | 100.0% | Truly breaking API operations detected |
| Impact Precision | 58.3% | Confirmed affected callsites vs rejected false positives |
| False Positive Rate | 41.7% | Unaffected sibling methods correctly rejected |
| File Precision | 100.0% | True positive modified files / total modified files |
| File Recall | 100.0% | Truly affected files modified / total expected files |
| Patch Semantic Correctness | 75.0% | Patches semantically matching human PR diffs |
| Test Preservation Rate | 100.0% | Pre-existing test suites passing without breakage |
| Autonomous Acceptance | 75.0% | Cases meeting merge-ready criteria under SafetyPolicy |
| Unsafe Patches Emitted | 0 | Zero unsafe patches emitted on unverified targets |
| Correctly Unresolved Refusals | 8 | Callsites safely quarantined for human triage |

## Per-Case Breakdown

| Status | Provider | Case ID | Recall | Precision | File-P | Unsafe | Decision |
|---|---|---|---|---|---|---|---|
| PASS | Stripe | stripe-v22-charges-type-drift | 100.0% | 33.3% | 100.0% | 0 | Autonomous PR Approved |
| PASS | OpenAI | openai-v4-chat-completions-rewrite | 100.0% | 50.0% | 100.0% | 0 | Autonomous PR Approved |
| PASS | Anthropic | anthropic-messages-api-migration | 100.0% | 100.0% | 100.0% | 0 | Autonomous PR Approved |
| FAIL | Twilio | twilio-regional-subdomain-sunset | 100.0% | 50.0% | 100.0% | 0 | Quarantined (Human Review) |
| SKIP | UnverifiedProvider | unverified-speculative-migration | 0.0% | 0.0% | 0.0% | 0 | Excluded (Unverified) |
