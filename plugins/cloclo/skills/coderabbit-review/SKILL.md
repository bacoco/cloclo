---
name: coderabbit-review
description: Use when the pipeline needs a local CodeRabbit CLI review of a git diff during Phase 6.5
user-invocable: false
---

# coderabbit-review

Local CodeRabbit CLI review of committed changes. Complements Codex and GLM:
CodeRabbit catches lint/security/style issues with static-analysis backing, the
LLM reviewers catch architectural/spec-compliance issues.

The shared review policy — the 3 auto-integration gates, consensus,
`[CONSENSUS]` escalation, the Phase 6.5 enable condition, and the reviewer
roster — lives in `../pipeline/references/review-chain.md`. This file only
covers the CodeRabbit-CLI-specific mechanics.

## 1. Context Reception

The calling skill (typically `pipeline` Phase 6.5) passes:

| Parameter     | Description                                      |
|---------------|--------------------------------------------------|
| `session_dir` | Absolute path to session directory               |
| `output_file` | Where to write findings (e.g. `07b-coderabbit-review-impl.md`) |
| `base_ref`    | Git SHA before implementation (Phase 5 `base_ref`) |

## 2. Prerequisites

```bash
command -v coderabbit >/dev/null || CR_UNAVAILABLE=1
```

If `coderabbit` not found → skip review with warning: `"CodeRabbit CLI unavailable. Install: curl -fsSL https://cli.coderabbit.ai/install.sh | sh"` and return. Skipping never blocks the pipeline (see review-chain.md, Phase 6.5 enable condition).

Auth is managed by the CLI — do NOT check `coderabbit auth` state. If auth fails at runtime, the `coderabbit review` command prints a login hint; surface it to the user. The CodeRabbit free tier is rate-limited — a rate-limit or auth failure surfaces on the ERROR path below, not as a clean pass.

## 3. Execution (FOREGROUND)

Pre-clear any stale output, short-circuit on an empty diff, then run the CLI.

```bash
cd "$(git rev-parse --show-toplevel)"

# Pre-clear a stale file so the post-run guard can't accept an old review as success.
rm -f "$output_file"

# Empty-diff pre-check: nothing to review between base_ref and HEAD.
if [ "$(git rev-list --count "$base_ref"..HEAD)" -eq 0 ]; then
  echo "# CodeRabbit Review — impl ($(date -u +%Y-%m-%dT%H:%M:%SZ))" > "$output_file"
  echo "" >> "$output_file"
  echo "Base: $base_ref → HEAD" >> "$output_file"
  echo "Type: committed changes" >> "$output_file"
  echo "---" >> "$output_file"
  echo "" >> "$output_file"
  echo "(no changes) — no commits between base_ref and HEAD; review skipped." >> "$output_file"
  # log to session.log and return
  exit 0
fi

# Write the header FIRST, then append the CLI output.
# base_ref is a SHA from Phase 5; --base takes a branch name, so a SHA needs
# --base-commit. Verify the flag with `coderabbit review --help` on upgrade.
{
  echo "# CodeRabbit Review — impl ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo ""
  echo "Base: $base_ref → HEAD"
  echo "Type: committed changes"
  echo "---"
  echo ""
} > "$output_file"

# --agent findings appended to $output_file; process/progress/rate-limit/auth
# lines (stderr) go to the sibling runtime log, NEVER into the verbatim file.
# < /dev/null: coderabbit's default mode is interactive and can hang on
# inherited stdin / auth prompts. timeout 600 caps a wedged run.
timeout 600 coderabbit review \
  --agent \
  --type committed \
  --base-commit "$base_ref" \
  < /dev/null \
  >> "$output_file" 2> "${output_file}.runtime.log"
CR_EXIT=$?
```

- Print: `"CodeRabbit is reviewing... (typically 30-90 seconds)"`
- Block until exit.
- Do NOT delete output on failure — the user needs to see what broke.

### Post-run guard (mandatory)

```bash
if [ $CR_EXIT -eq 0 ] && [ -s "$output_file" ]; then
  echo "[coderabbit-review] OK: $output_file"
else
  # exit≠0, timeout (124), or empty file → tool produced nothing.
  {
    echo ""
    echo "## ERROR"
    echo ""
    echo "CodeRabbit review did not complete (exit=$CR_EXIT). Possible causes:"
    echo "auth/login required, free-tier rate limit, network, or a wedged run (timeout)."
    echo ""
    echo "Runtime log tail (see \`${output_file}.runtime.log\` for full):"
    echo ""
    tail -n 20 "${output_file}.runtime.log" 2>/dev/null | sed 's/^/    /'
  } >> "$output_file"
  echo "[coderabbit-review] FAIL: exit=$CR_EXIT — treated as SKIPPED, not a clean pass." >&2
fi
```

**Guard semantics (do not conflate these three states):**

- `exit==0 && [ -s "$output_file" ]` → the run succeeded. If the CLI reported no
  issues, that is a genuine **clean pass** — log `(0 findings)`.
- `exit==0` but the file is empty (only the header, so `[ -s ]` on the appended
  body fails / tool wrote nothing) → the tool produced nothing. Treat as
  **skipped**, NOT a clean pass.
- `exit≠0` (including timeout `124`) → failure; append the `## ERROR` section and
  treat as skipped. Name the rate-limit mode explicitly in the error text.

## 4. Output Format

CodeRabbit `--agent` mode emits structured findings: one block per issue with
file path, line range, severity, rule, and suggested fix. The calling skill
reads the file verbatim — no summarization. Only the findings file is verbatim;
stderr lives in `${output_file}.runtime.log` and is never read as findings.

The output file is assembled in two steps (see §3): the header is written
**first**, then the raw CLI output is appended. The final file looks like:

```markdown
# CodeRabbit Review — impl (2026-07-02T10:00:00Z)

Base: <base_ref SHA> → HEAD
Type: committed changes
---

{raw coderabbit --agent output, or "(no changes)", or a ## ERROR section}
```

The header is a 4-line block (title, blank, `Base:`, `Type:`) followed by the
`---` rule — not "3 lines". `impl` is the fixed review type for this skill (the
only caller is Phase 6.5); it is not a received parameter.

## 5. Finding Severity

CodeRabbit's native levels map to the pipeline's P-scale (canonical map in
`../pipeline/references/review-chain.md`):

| CodeRabbit | Pipeline | Handling |
|------------|----------|----------|
| `high`     | P0       | auto-integration candidate (3 gates) |
| `medium`   | P1       | auto-integration candidate (3 gates) |
| `low`      | P2       | auto-integration candidate (3 gates) |
| `nit`      | P2 (advisory) | never auto-applied — logged only |

The scale stops at P2 — there is no lower tier. `nit` maps to P2 as advisory:
surfaced and logged, but never auto-applied. The calling skill feeds these into
the 3-gate auto-integration model from review-chain.md.

## 6. Auto-Integration & Escalation

This skill does **not** decide fixes — it only writes findings. The pipeline
applies them under the shared model in
`../pipeline/references/review-chain.md`:

- Findings that pass the **3 gates** (concrete patch; not auth/payments/data
  migration; no conflicting patch) are auto-applied.
- A CodeRabbit finding at the same `file:line` as an independent reviewer
  (Codex or GLM) forms **consensus** → mark `[CONSENSUS]`, escalate severity to
  the highest, apply even if judgment-only.
- Escalation triggers (iteration cap with open `high`, conflicting patches,
  auth/payments/data-migration domain, etc.) are the shared list in
  review-chain.md — escalate in the terminal, never on GitHub.

There are no interactive review gates in this skill — the pipeline
auto-integrates via review-chain.md.

## 7. Important Rules

- **NEVER summarize or filter findings.** Raw `--agent` output, verbatim, in `$output_file`.
- **stderr is not findings.** Progress/rate-limit/auth noise goes to `${output_file}.runtime.log` only.
- **Foreground ONLY.** No background job, no polling.
- **Distinguish skip from clean.** Empty file (exit 0) or error ≠ "0 findings". Only a completed run with no reported issues is a clean pass.
- **Log to `session.log`:** `[timestamp] CodeRabbit review {complete|skipped|failed}: {output_file} ({N findings, severity breakdown} | (0 findings) | (no changes))`
- **Do NOT fix findings.** The pipeline auto-integrates via review-chain.md's 3 gates; this skill only writes the file.
- **Evidence tag:** All CodeRabbit findings are `[TOOL]` (static analysis + AI) — highest evidence weight.
