---
name: verify
description: "Phase 7 of the dev pipeline: run configurable verification commands and deployment. Enforces evidence-before-claims — no completion without fresh verification output."
user-invocable: false
---

# Verify — Configurable Verification

Run verification commands and deployment steps. Collect evidence. Report results. Never claim success without proof.

<HARD-GATE>
IRON LAW: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.
Never say "should work", "I think it passes", "it looks correct". Run the commands, show the output, THEN claim success or failure. A verification that was not executed does not exist.
</HARD-GATE>

## Context Reception

This skill receives from the pipeline orchestrator:
- `session_dir` — path to the pipeline session directory
- `pipeline.config.md` — verification config (may or may not exist in session_dir)

## Step 1: Load Configuration

Read `{session_dir}/pipeline.config.md` if it exists. Parse these fields:

| Field | Purpose | Example |
|-------|---------|---------|
| `verification_commands[]` | Commands to run sequentially | `npm test`, `pytest tests/ -x`, `cargo test` |
| `deploy_commands[]` | Post-verification deployment | `docker compose up -d --build myservice` |
| `base_ref` | Git base branch for diff context | `main` |

**No config file?** Auto-detect from the project root:
- `package.json` with `scripts.typecheck` → `npm run typecheck` (or `pnpm`/`yarn` if lockfile present)
- `package.json` with `scripts.lint` → `npm run lint`
- `package.json` with `scripts.test` → `npm test`
- `tsconfig.json` → `tsc --noEmit`
- `pytest.ini` or `pyproject.toml [tool.pytest]` → `pytest tests/ -x`
- `Cargo.toml` → `cargo test`
- `go.mod` → `go test ./...`
- `Makefile` with `test` target → `make test`

If nothing detected, ASK the user what to run. Do not guess. Do not skip.

## Step 2: Run Verification Commands

Execute each command sequentially. For each command:

1. Print: `Running: <command>`
2. Execute with full stdout + stderr capture
3. Record: exit code, duration, output
4. **If a command fails:** report with full error output. Ask the user: fix and re-run, skip, or abort.
5. **If a command passes:** record success with actual output (30+ lines minimum, full for failures)

## Step 3: Deployment (If Configured)

Skip if `deploy_commands[]` is not set. Execute each deploy command sequentially.
Wait for services to be ready (health checks, status checks, port availability).
If a deploy fails: report immediately, do not continue. If all succeed: confirm with evidence (service status, health check response).

## Evidence Format

Report results in this exact structure:

```
## Verification Results

### Command: `npm test`
Status: PASS
Duration: 4.2s
Output:
(first 20+ lines of actual output)

### Command: `pytest tests/ -x`
Status: FAIL
Duration: 12.1s
Exit code: 1
Output:
(full error output — never truncate failures)

### Deploy: `docker compose up -d --build myservice`
Status: PASS
Duration: 38s
Service status: myservice running (healthy)
```

## Rationalization Prevention

These thoughts mean STOP — you are about to claim something without evidence:

| Thought | Reality |
|---------|---------|
| "It should work based on the code" | Run the command. Show the output. |
| "The tests probably pass" | Run them. Show the result. |
| "I already checked this" | When? Show fresh output from this session. |
| "The change is too small to break anything" | Small changes cause big bugs. Verify. |
| "Let me just report success" | Evidence first. Always. |
| "I can tell from the code it is correct" | Code review is not verification. Execute. |

If you catch yourself thinking any of the above, run the command before writing another word.

## Anti-Patterns

- Reporting PASS without showing actual command output
- Truncating error output on failures (show everything)
- Running commands in the background and moving on without waiting for results
- Claiming "tests pass" from a previous session — only this session's output counts
- Continuing after a failure without user input on how to proceed

## Output Contract

| Key | Value |
|-----|-------|
| **Return status** | `VERIFICATION_PASSED` (all commands green, all checks passed) |
| | `VERIFICATION_FAILED` (any command failed — includes full details) |
| **Evidence** | Full output for every command executed |
| **Next step** | Pipeline orchestrator logs the result and presents final summary |
