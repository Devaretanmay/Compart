# Launch kit

Drafts for launch week. Post in this order: X thread (warm up) → r/ClaudeAI →
Show HN → r/rust. Reply to every comment within the first 3 hours; that window
decides the whole trajectory.

One rule while posting: talk like an engineer who built a thing, not a founder
launching a thing. No "revolutionary." No "game-changing." Numbers do the talking.

---

## Show HN

**Title:**

> Show HN: Git blame for AI agents – provenance trailers + 2ms undo, all local

**First comment:**

Hey HN. I got tired of not being able to answer basic questions about my own repo after letting Claude Code loose on it:

- Which commits were written by an agent?
- Did it touch ~/.aws or read my .env while it worked?
- It just trashed 40 files – how do I get back without nuking my own uncommitted work?

git log doesn't know. git blame doesn't know. So I built Compart (Apache-2.0).

Three things it does:

1. Provenance trailers. `compart commit` stamps every agent commit with RFC-5322 metadata – agent identity, execution ID, sandbox verdict – readable with plain git. Wrote up the format as an open spec (SPEC.md in the repo) so other tools can emit the same fields. I'd rather have a standard than a moat here.

2. 2ms physical undo. Before every run it snapshots the workspace with BLAKE3 hashes. `compart undo` restores changed files and removes generated ones in about 2ms on a mid-size repo – without touching your untracked human work. This is the part I use constantly.

3. A kernel-level sandbox (macOS Seatbelt / Linux Landlock) so the agent physically can't read ~/.ssh or ~/.aws. Deny-by-default, inherited by every subprocess.

Yes, Codex CLI and Claude Code ship their own sandboxes now – that's good, sandboxing should be table stakes. Compart sits one layer above: orchestrate any agent, record everything, undo anything, prove who wrote what. The audit layer is the part no vendor will build themselves.

Stack: Rust core (~14k lines), Python CLI, ~200 tests including hostile concurrency cases. pip install compart, then `compart init` in any repo.

Happy to answer anything about the Seatbelt profile generation, the BLAKE3 diffing, or why the trailer spec uses neutral names instead of vendor prefixes.

---

## r/ClaudeAI

**Title:**

I built a free audit layer for Claude Code – know exactly what the agent did, undo it in milliseconds

**Body:**

Quick context: I let Claude Code run autonomously more than I probably should. It's great until one of these happens:

- it reads something it shouldn't (.env, ssh keys)
- it wrecks files across the repo and git reset --hard eats my uncommitted work too
- someone on my team asks "wait, which PRs did the agent write?" and nobody knows

So I spent the last few months building Compart. It wraps any agent CLI (claude, codex, cursor, aider, opencode):

- `compart claude` runs the session inside a macOS Seatbelt / Linux Landlock sandbox where ~/.ssh, ~/.aws etc are kernel-blocked before the agent even starts
- `compart undo` rolls back just that execution in ~2ms (BLAKE3 snapshots), leaves your own untracked files alone
- `compart commit` stamps commits with machine-readable trailers saying which agent/execution made them – readable in vanilla git

100% local, no account, Apache-2.0: https://github.com/Devaretanmay/Compart

Honest limits: macOS/Linux only right now, no Windows. And if you only ever run agents with per-action approval prompts, you need this less than people running long autonomous sessions.

Feedback wanted, especially: would the provenance trailers actually help your team, or is this a me-problem?

---

## r/rust

**Title:**

Built a Rust core for auditing AI coding agents – BLAKE3 snapshot engine doing 2ms full-workspace rollback, plus log/diff compression engines

**Body:**

Sharing the guts of [Compart](https://github.com/Devaretanmay/Compart) since this community will appreciate them more than the AI angle:

- **Snapshot engine (src/runtime/snapshot.rs):** walks the workspace excluding build dirs, blake3-hashes every file into a manifest, restore diffs current state against the manifest and only copies back what actually changed. Full rollback on a typical repo lands around 2ms because most files hash-match.
- **Four compression engines (~10k LOC, src/engines/):** structured-JSON crusher that keeps statistical outliers, a log compressor that isolates stack traces and drops progress-bar spam, a multi-file diff compressor, and an extractive text summarizer. They exist because agent tool output was eating 80% of our LLM context.
- **Seatbelt profile generation from Rust via FFI** (src/sandbox/macos.rs) and Landlock on Linux through the landlock crate.

~14k lines of Rust, opt-level="z" + LTO, ~200 tests total across the project. Apache-2.0.

The interesting design fight: deny-by-default Seatbelt profiles that still let dyld work, localhost stay alive for dev servers, but hard-deny credential paths before any agent code runs. Happy to go deep on the profile generation if there's interest.

---

## X/Twitter thread (5 posts)

**1/**
AI coding agents write a growing chunk of everyone's codebase now.

Git still has zero idea which commits they wrote.

I built the missing layer. It's called Compart. Open source, fully local.

**2/**
The pitch in one command:

`compart commit`

Every agent commit gets stamped with trailers: which agent, which run, sandbox verdict. Readable with plain git. Auditable forever.

Wrote the format up as an open spec so any tool can emit it. Standards > moats.

**3/**
Second thing: undo.

Agents wreck things. git reset --hard punishes your uncommitted work for the agent's crime.

compart undo = BLAKE3 snapshot diff, physical restore, ~2ms. Only touches what that execution touched.

**4/**
Third: secrets. Agents can read ~/.ssh and ~/.aws unless something stops them at the OS level. Compart blocks those paths with Seatbelt/Landlock before the process starts. Every child process inherits the jail.

**5/**
All local. No cloud. No dashboard. Apache-2.0.

pip install compart → compart init → run your agent inside it.

Repo: github.com/Devaretanmay/Compart

If you've ever had to explain to your team what an agent did to main, this is for you.

---

## Post-launch metrics to watch

| Signal | Healthy | Panic threshold |
| :--- | :--- | :--- |
| GitHub stars / wk 1 | 150+ | < 40 |
| PyPI downloads / wk 2 | 800+ | < 200 |
| % of visitors who star | 3%+ | < 1% |
| Comments asking "does it support X" | many | zero (means wrong audience) |

If panic thresholds hit, the problem is the post/title, not usually the product. Iterate the headline before touching code.
