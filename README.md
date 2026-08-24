<div align="center">

# Compart

### Git blame for agents.

**Compart records what your AI coding agents actually did, stamps every commit with proof of who wrote it, and hands you a undo button for when they go rogue.**

[PyPI Package](https://pypi.org/project/compart/) | [Quickstart](docs/QUICKSTART.md) | [Trailer Spec](SPEC.md)

<br/>

```text
   agents write the code.
    compart keeps the receipts.
```

</div>

---

## The problem

You gave an agent access to your repo. Then came the questions nobody can answer:

- *Which of these commits were written by Claude, and which by a human?*
- *Did the agent read `.env`, `~/.aws`, or your SSH keys while it worked?*
- *The last run wrecked 40 files. What's the fastest way back?*

`git log` has no idea. `git blame` shrugs. Your security team keeps asking.

Compart answers all three - locally, in milliseconds, with zero infrastructure.

## How it works

```bash
cd my-project
compart init          # one file, one directory. that's the whole setup.

compart claude        # run any agent: claude, codex, cursor, aider, opencode
compart exec -- pytest tests/

compart diff          # exactly what changed, isolated per execution
compart apply         # keep the good parts
compart undo          # physically roll back the rest in 2ms
compart commit -m "Add auth module"
```

That last command is the point. Every `compart commit` lands in git with
machine-readable provenance trailers - which agent ran, under which execution,
with what security verdict. Anyone can verify it later with plain git. No
server, no dashboard, no vendor lock-in.

```text
Agent-Origin: agent
Agent-Agent: claude-code
Agent-Execution: exec_7a9f12bc
Agent-Compartment: builder
Agent-Sandbox: clean
```

Open standard, spec'd in [SPEC.md](SPEC.md). Other tools can write the same trailers - we'd like that.

---

## What ships in the box

```text
┌───────────────────────────┬───────────────────────────┬──────────────────────────────┐
│ 1. Provenance Trailers    │ 2. 2ms Undo Engine        │ 3. Multi-Agent Pipelines     │
│    Audit-grade git trail  │    BLAKE3 physical revert │    DAGs across any agents    │
├───────────────────────────┼───────────────────────────┼──────────────────────────────┤
│ 4. Kernel Sandbox         │ 5. Credential Defense     │ 6. Token Compression         │
│    Seatbelt / Landlock    │    Secrets stay sealed    │    Rust engines, 40-70% less │
└───────────────────────────┴───────────────────────────┴──────────────────────────────┘
```

### 1. Provenance trailers
RFC-5322 metadata attached to every agent-authored commit: agent identity,
execution ID, compartment, security verdict. Turns "I think the AI wrote this"
into an auditable fact. Built for compliance reviews, incident response, and
the day someone asks you to prove your codebase is human-supervised.

### 2. Physical undo, 2 milliseconds
Before every agent run, Compart snapshots the workspace with BLAKE3 hashes.
`compart undo` restores modified files, removes generated ones, and leaves your
untracked human work alone. Faster than you can switch windows. No cloud
snapshots, no container rebuilds.

### 3. Multi-agent pipelines
Chain specialized steps into dependency-aware DAGs - a research step with
network access, a build step without, a test step read-only - then execute the
whole graph topologically. Failed upstream steps skip their dependents;
independent branches keep running.

```bash
compart -w vuln-scan
compart step vuln-scan src/fetch_cve.py --compartment research
compart step vuln-scan src/patch.py      --compartment builder
compart step vuln-scan "pytest tests/"   --compartment tester
compart --run vuln-scan
```

### 4. Kernel-level sandbox
Process isolation enforced by the OS itself - macOS Seatbelt, Linux Landlock.
Deny-by-default filesystem scoping, per-compartment network gating, and
confinement inherited by every child process the agent spawns. Not a wrapper
around `exec()`. Not vibes.

### 5. Credential defense
`~/.ssh`, `~/.aws`, `~/.config/gcloud`, keychains, browser profiles, git
credentials - denied at the kernel boundary before the agent ever starts. An
optional local proxy injects API secrets into outbound calls without the raw
keys ever entering the agent's context.

### 6. Token compression engines
Four Rust engines crush terminal noise before it eats your context window:
SmartCrusher (structured JSON), LogCompressor (stack traces over progress
bars), DiffCompressor (multi-file diffs), TextCrusher (extractive summaries).
40-70% token savings on typical agent output. Your API bill will notice.

---

## Python SDK

Drop Compart into LangGraph, CrewAI, AutoGen, or whatever pipeline you're
running this week:

```python
from compart import Compart, Compartment, CompartmentConfig

box = Compart(workdir=".")

box.add(Compartment(
    name="researcher",
    fn=lambda ctx: print("Fetching external docs..."),
    config=CompartmentConfig(permissions=["fs_read", "network"]),
))

box.add(Compartment(
    name="builder",
    fn=lambda ctx: print("Writing code. Zero exfiltration."),
    config=CompartmentConfig(permissions=["fs_read", "fs_write", "fs_exec"]),
))

box.edge("researcher", "builder")
result = box.run()
print(f"{result.status} in {result.elapsed_s}s")
```

| Framework | Pattern | Docs |
| :--- | :--- | :--- |
| **LangGraph / LangChain** | `@compart_tool` sandboxed decorator | [Framework Hooks](docs/FRAMEWORK_HOOKS.md) |
| **CrewAI** | Isolated `CompartTask` tool | [Framework Hooks](docs/FRAMEWORK_HOOKS.md#crewai) |
| **AutoGen** | Sandboxed code-exec container | [Framework Hooks](docs/FRAMEWORK_HOOKS.md#autogen) |
| **OpenHands / SWE-bench** | Zero-latency local backend | [Use Cases](docs/USE_CASES.md) |

---

## Why not just Docker?

| | Compart | Docker | Cloud microVMs (E2B etc.) | Raw host process |
| :--- | :---: | :---: | :---: | :---: |
| Startup overhead | **< 1 ms** | 2,000-10,000 ms | 1,000-5,000 ms | 0 ms |
| Setup | **one command** | Dockerfiles, daemon | cloud account, billing | none |
| Secrets blocked by default | **yes, kernel-enforced** | manual mounts | remote | lol no |
| Physical undo | **2 ms** | recreate container | VM snapshot | `git reset --hard` (good luck) |
| Agent provenance in git | **yes** | no | no | no |
| Code stays on your machine | **always** | yes | no | yes |

---

## Documentation

[Quickstart](docs/QUICKSTART.md) · [CLI Reference](docs/CLI.md) · [Agent Execution](docs/AGENT_EXECUTION.md) · [Credential Proxy](docs/CREDENTIAL_PROXY.md) · [Snapshots & Rollback](docs/SNAPSHOTS.md) · [Compression](docs/COMPRESSION.md) · [API Reference](docs/API_REFERENCE.md) · [Security Use Cases](docs/USE_CASES.md) · [Trailer Spec](SPEC.md)

## Contributing

PRs welcome - read [CONTRIBUTING.md](CONTRIBUTING.md) and [CLA.md](CLA.md) first.
Found a sandbox escape? That's a [security report](SECURITY.md), not an issue.

## License

Apache-2.0. Fork it, embed it, ship it - just don't use our name to sell your fork.
