# Compart Quickstart Guide

Get up and running with Compart in under 2 minutes.

> **“Greptile understands changes humans make to software. Compart understands changes the outside world makes to software.”**

---

## 1. Installation

Install Compart via PyPI:

```bash
pip install --upgrade compart
```

---

## 2. Day-0 Dependency Audit & Risk Register

Immediately scan your codebase for breaking upstream API changes, deprecated callsites, and auto-repairable integrations:

```bash
cd my-project

# Run terminal risk register:
compart audit .

# Export as GitHub Issue markdown:
compart audit . --format=github-issue

# Inspect the External-Change Dependency Graph:
compart graph .
```

---

## 3. Autonomous Continuous Maintenance

Run autonomous maintenance on external providers (e.g. Stripe, OpenAI, Anthropic, Clerk, AWS):

```bash
# Detect drift and run surgical AST patch loop:
compart maintain . --provider stripe

# Custom version bump and open PR:
compart maintain . --provider openai --from v3.28.0 --to v4.0.0 --create-pr --repo owner/repo
```

---

## 4. Interactive Coding Agents & Sandboxed Governance

Run terminal coding agents inside a kernel-enforced sandbox with full native TUI fidelity:

```bash
# Launch Claude Code, OpenCode, Codex, Cursor, or Aider directly:
compart claude

# When the agent finishes:
compart diff    # Review what the agent changed
compart undo    # Instantly restore files if the agent made a mistake
compart commit  # Commit to Git with verified provenance trailers
```

---

## 5. Key Guarantees

- **External Intelligence**: Full-codebase AST mapping of providers, contracts, wrappers, and callsites.
- **Continuous Maintenance**: Surgical AST patching with local formatter matching and automated Developer Trust PRs.
- **Kernel Enforcement**: Built on native OS isolation (macOS Seatbelt / Linux Landlock).
- **Credential Protection**: `~/.ssh`, `~/.aws`, `~/.config/gcloud`, git credentials, and keychains are denied by default.
- **Instant Rollback**: Hash-based BLAKE3 file snapshots allow physical restoration of modified and deleted files in 2ms.
- **Zero Infrastructure**: No Docker, no daemon, no cloud account required.
