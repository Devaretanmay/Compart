import json
import os
import pytest
from compart import autopatch
from compart.cli.main import main
import sys

def test_reproduce_langchain_openai():
    report = autopatch.reproduce_case("langchain-openai-v4")
    assert report["success"] is True
    assert report["provider"] == "OpenAI"
    assert report["repository"] == "langchain-ai/langchainjs"
    assert report["target_version_tag"] == "openai@v4.0.0"
    assert report["outcome_label"] == "AUTONOMOUS_REPAIR"
    assert report["blast_radius_verified"] is True
    assert report["unintended_files_modified"] == 0
    assert report["files_modified"] == 1
    assert "chat.completions.create" in report["unified_diff"]
    assert report["mergeable_pr_eligible"] is True

def test_reproduce_calcom_stripe():
    report = autopatch.reproduce_case("calcom-stripe-v13")
    assert report["success"] is True
    assert report["provider"] == "Stripe"
    assert report["repository"] == "calcom/cal.com"
    assert report["target_version_tag"] == "stripe@v13.0.0"
    assert report["outcome_label"] == "AUTONOMOUS_REPAIR"
    assert report["blast_radius_verified"] is True
    assert report["unintended_files_modified"] == 0
    assert report["files_modified"] == 1
    assert "String(amount)" in report["unified_diff"]
    assert report["mergeable_pr_eligible"] is True

def test_reproduce_anthropic_smol_ai():
    report = autopatch.reproduce_case("smol-ai-anthropic-messages")
    assert report["success"] is True
    assert report["provider"] == "Anthropic"
    assert report["repository"] == "smol-ai/developer"
    assert report["blast_radius_verified"] is True
    assert report["unintended_files_modified"] == 0
    assert report["files_modified"] == 1
    assert "claude-3-5-sonnet-20241022" in report["unified_diff"]
    assert report["mergeable_pr_eligible"] is True

def test_reproduce_taxonomy_stripe():
    report = autopatch.reproduce_case("taxonomy-stripe-v22")
    assert report["success"] is True
    assert report["provider"] == "Stripe"
    assert report["repository"] == "shadcn-ui/taxonomy"
    assert report["blast_radius_verified"] is True
    assert report["unintended_files_modified"] == 0
    assert report["files_modified"] == 1
    assert "String(amount)" in report["unified_diff"]
    assert report["mergeable_pr_eligible"] is True

def test_reproduce_all_ten_cases(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["compart", "reproduce", "all", "--json"])
    main()
    captured = capsys.readouterr()
    reports = json.loads(captured.out)
    assert len(reports) == 10
    for r in reports:
        assert r["blast_radius_verified"] is True
        assert r["unintended_files_modified"] == 0
        assert r["success"] is True

def test_full_git_replay_three_flagship_cases():
    cases = ["git-langchainjs-openai-v4", "git-calcom-stripe-v13", "git-taxonomy-stripe-v22"]
    for cid in cases:
        report = autopatch.reproduce_git_case(cid)
        assert report["success"] is True
        assert report["lockfile_verified"] is True
        assert report["t0_version_verified"] is True
        assert report["blast_radius_verified"] is True
        assert report["unintended_files_modified"] == 0
        assert report["mergeable_pr_eligible"] is True
        assert report["human_diff_similarity"] >= 0.5
        assert report["classification"] == "REPRODUCIBLE"
        assert report["evidence_json_path"] is not None

def test_git_replay_evidence_bundle_on_disk():
    report = autopatch.reproduce_git_case("git-taxonomy-stripe-v22")
    path = report["evidence_json_path"]
    assert os.path.exists(path)
    with open(path) as f:
        evidence = json.load(f)
    assert evidence["case_id"] == "git-taxonomy-stripe-v22"
    assert evidence["package_manager"] == "npm"
    assert evidence["resolved_t0_version"] == "11.18.0"
    assert "lockfile_blake3_hash" in evidence
    assert "semantic_match" in evidence
    assert evidence["classification"] == "REPRODUCIBLE"

def test_git_replay_fails_closed_invalid_case():
    with pytest.raises(ValueError, match="Unknown Git history replay case"):
        autopatch.reproduce_git_case("non-existent-case-id")

