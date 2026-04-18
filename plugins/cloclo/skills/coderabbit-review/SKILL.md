---
name: coderabbit-review
description: Use when the pipeline needs a local CodeRabbit CLI review of a git diff — invokes `coderabbit review --agent` and writes structured findings to a session file
user-invocable: false
---

# coderabbit-review

Local CodeRabbit CLI review of committed changes. Complements Codex: CodeRabbit
catches lint/security/style issues with static-analysis backing, Codex catches
architectural/spec-compliance issues.

## 1. Context Reception

The calling skill (typically `pipeline` Phase 6.5) passes:

| Parameter     | Description                                      |
|---------------|--------------------------------------------------|
| `session_dir` | Absolute path to session directory               |
| `output_file` | Where to write findings (e.g. `07b-coderabbit-review-impl.md`) |
| `base_ref`    | Git ref before implementation (Phase 5 `base_ref`) |

## 2. Prerequisites

```bash
command -v coderabbit >/dev/null 2>&1 || CR_UNAVAILABLE=1
```

If `coderabbit` not found → skip review with warning: `"CodeRabbit CLI unavailable. Install: curl -fsSL https://cli.coderabbit.ai/install.sh | sh"` and return.

Auth is managed by the CLI — do NOT check `coderabbit auth` state. If auth fails at runtime, the `coderabbit review` command prints a login hint; surface it to the user.

## 3. Execution (FOREGROUND)

```bash
cd "$(git rev-parse --show-toplevel)"
coderabbit review \
  --agent \
  --type committed \
  --base "$base_ref" \
  > "$output_file" 2>&1
```

- Print: `"CodeRabbit is reviewing... (typically 30-90 seconds)"`
- Block until exit
- On non-zero exit with empty output → append `## ERROR` section to `$output_file` with stderr tail and return
- Do NOT delete output on failure — the user needs to see what broke

## 4. Output Format

CodeRabbit `--agent` mode emits structured findings: one block per issue with
file path, line range, severity, rule, and suggested fix. The calling skill
reads the file verbatim — no summarization.

Prepend a 3-line header to the output file:

```markdown
# CodeRabbit Review — {review_type} ({timestamp})

Base: {base_ref} → HEAD
Type: committed changes
---

{raw coderabbit output}
```

## 5. Finding Severity

CodeRabbit uses its own severity levels (`high`, `medium`, `low`, `nit`). Map
them for the pipeline's decision point:

| CodeRabbit | Pipeline |
|------------|----------|
| `high`     | P0       |
| `medium`   | P1       |
| `low`      | P2       |
| `nit`      | P3 (informational) |

The calling skill uses these mappings when presenting findings to the user.

## 6. Important Rules

- **NEVER summarize or filter findings.** Raw output, tagged by severity.
- **Foreground ONLY.** No background job, no polling.
- **Log to `session.log`:** `[timestamp] CodeRabbit review complete: {output_file} ({N findings, severity breakdown})`
- **Do NOT fix findings.** The calling skill presents decision point A-E; user decides.
- **Evidence tag:** All CodeRabbit findings are `[TOOL]` (static analysis + AI) — highest evidence weight.
