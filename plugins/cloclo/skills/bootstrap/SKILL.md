---
name: bootstrap
description: "Use when setting up Claude Code for a new project — generates CLAUDE.md, real settings.json hooks, memory seeds, project skills, and an optional wiki, all adapted to the detected stack. Triggers: /bootstrap, setup project, initialise, configure claude code, nouveau projet"
---

# Bootstrap — Claude Code Project Setup

This skill installs a complete Claude Code setup on any project: CLAUDE.md, hooks,
a memory folder, project skills, and an optional wiki. Adapt everything to the real
project detected in Phase 1.

**Confirmation policy:** bootstrap may run non-destructive scaffolding without asking
(analysis, creating CLAUDE.md/hooks/skills on a fresh project). It MUST stop and ask
before: (a) committing anything (Phase 8), and (b) handling any credential or secret.
It MUST NEVER overwrite an existing `CLAUDE.md` or an existing `MEMORY.md` — merge or
skip instead (see Phase 0).

All template paths below use `${CLAUDE_PLUGIN_ROOT}` — the plugin root at runtime.
Templates live under `${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/templates/`.

## Prerequisites

```bash
git status          # must be a git repo
node --version      # Node.js 18+ only if you opt into opensrc (Phase 6)
jq --version        # required — the generated hooks parse stdin JSON with jq
ls -la              # project structure
```

---

## PHASE 0 — Already bootstrapped? (idempotency)

Before doing anything, detect prior setup and choose per-artifact behavior. NEVER
clobber existing memory or CLAUDE.md.

```bash
test -f CLAUDE.md && echo "CLAUDE.md exists"
jq -e '.hooks' .claude/settings.json >/dev/null 2>&1 && echo "settings.json already has hooks"
ls .claude/skills/ 2>/dev/null
test -f wiki/schema.md && echo "wiki already initialized"
```

Also locate the memory folder (Phase 4) and check `MEMORY.md`.

| Artifact | If it already exists |
|----------|----------------------|
| `CLAUDE.md` | Do NOT overwrite. Report it exists; offer to append missing OBLIGATOIRE sections only. |
| `.claude/settings.json` hooks | Merge new hook entries into the existing `hooks` object; do not drop existing hooks. |
| `MEMORY.md` | Do NOT overwrite. Append missing pointers/sections only. |
| feedback memories | Skip files that already exist. |
| `.claude/skills/<name>` | Skip skills that already exist; only create missing ones. |
| `wiki/` | Delegate to `cloclo:wiki` INIT, which has its own exists-check (Phase 5.5). |

If everything already exists, report "already bootstrapped" and stop.

---

## PHASE 1 — Project analysis (5 min max)

Explore the project to understand:

1. **Tech stack** — frameworks, languages, tools
2. **Structure** — monorepo or single app? main directories?
3. **Services** — ports, Docker, processes?
4. **Dependencies** — package.json, requirements.txt, pyproject.toml, Cargo.toml, go.mod?
5. **Existing patterns** — code organization, conventions?
6. **Tests** — test frameworks, coverage?

Use Glob + Grep + Read. Summarize findings in 10-15 lines. **This analysis drives
everything else** — including which hooks and which skills apply. A library or CLI with
no services should NOT get Docker-oriented skills (smoke-test, cross-service-debug).

---

## PHASE 2 — CLAUDE.md

If `CLAUDE.md` already exists (Phase 0), do NOT overwrite — skip or append only.

Otherwise create `CLAUDE.md` at the project root. Read the template:
`Read ${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/templates/claude-md-template.md`

Adapt EVERY section to the real project detected in Phase 1:
- Replace placeholders with the real build/test/lint commands
- Draw the real architecture diagram (services, ports, connections)
- Document the real codebase patterns
- Add the recurring errors specific to the detected stack

Note: `{{PLACEHOLDER}}` tokens are meant to be replaced. Literal `{{.Names}}` /
`{{.Status}}` in docker `--format` strings are Go template syntax — leave them as-is.

**Rule:** a CLAUDE.md with unreplaced `{{PLACEHOLDER}}` tokens is a failure.
Never put real credentials in CLAUDE.md (see Phase 2's template note on `.env.local`).

---

## PHASE 3 — Hooks

Create or enrich `.claude/settings.json`. Read the catalog:
`Read ${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/templates/hooks-template.json`

That file is a reference catalog written in the **real** `settings.json` `hooks` shape.
Copy the entries matching the stack detected in Phase 1 into the project's
`.claude/settings.json`. If the file already has `hooks`, MERGE (append entries into the
matching event arrays) — do not drop existing hooks.

The real target shape is:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "<parses stdin with jq>", "timeout": 30 }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "<git-commit blocker>", "timeout": 10 }
        ]
      }
    ]
  }
}
```

Contract every generated hook must respect (do NOT deviate):
- Input arrives as JSON on **stdin**. Parse with `jq` (`.tool_name`, `.tool_input.file_path`,
  `.tool_input.command`, `.cwd`). The vars `$CLAUDE_FILE_PATHS` / `$CLAUDE_COMMAND` DO NOT
  EXIST. Path var that exists: `${CLAUDE_PROJECT_DIR}`.
- `timeout` is in **SECONDS** (e.g. 30, 10 — never 30000).
- PostToolUse context injection prints
  `{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<text>"}}`.
- PreToolUse blocking uses
  `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"..."}}`
  (or exit code 2 with the message on **stderr**). `exit 1` is non-blocking.

Which entries to pick (from the catalog, by stack):

| Stack | PostToolUse type-check | PreToolUse commit-blocker |
|-------|------------------------|---------------------------|
| TypeScript | `tsc --noEmit` (entry 0) | block `console.log` (entry 0) |
| Python | `py_compile` (entry 1) | block bare `except:` (entry 1) |
| Go | `go vet` (entry 2) | — |
| Rust | `cargo check` (entry 3) | — |
| Multi-stack | combine the relevant entries | combine the relevant blockers |

Entries 4 (pytest) and 5 (next build) are heavier/optional — include only if the project
already has that test/build set up.

**Rule:** at minimum one PostToolUse type-check for the primary language. The commit-blocker
is optional but recommended.

### Verify hooks fire (mandatory)

```bash
jq -e '.hooks' .claude/settings.json    # confirm hooks are present and valid JSON
```

Then prove they actually run: edit a scratch file in the primary language (e.g. create
`/tmp/hooktest.py` with a deliberate syntax error and Write to it) and confirm the injected
reminder appears in the transcript. Delete the scratch file afterward. If nothing is
injected, the hook is not wired — re-check the settings.json shape and `jq` availability.

---

## PHASE 4 — Memory folder

Determine the project's memory folder path. Claude Code derives it from the project's
absolute path: `~/.claude/projects/<slugified-project-path>/memory/`, where the slug is the
absolute path with `/` replaced by `-` (leading `-` kept). Derive it, don't hardcode:

```bash
proj="$(pwd)"
slug="$(printf '%s' "$proj" | sed 's#/#-#g')"
memdir="$HOME/.claude/projects/${slug}/memory"
mkdir -p "$memdir"
echo "$memdir"
```

If `MEMORY.md` already exists there, do NOT overwrite it — append missing sections only.
Otherwise create `MEMORY.md`:

```markdown
# MEMORY.md

## User

## Feedback

## Project

## Reference
```

---

## PHASE 4.5 — Behavioral memory seeds

Copy the 7 generic feedback memories into the project memory folder. Templates:
`Read ${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/templates/feedback-memories/`

Naming convention: each source `<name>.md` becomes `feedback_<name>.md` in the memory folder
(the `feedback_` prefix marks a behavioral rule). Skip any file that already exists.

Files to create:
1. `feedback_verify_before_writing.md` — Grep/Glob BEFORE creating (Tier 1)
2. `feedback_test_after_change.md` — verify after each change (Tier 1)
3. `feedback_diagnostic_sequence.md` — sequence when something breaks (Tier 1)
4. `feedback_execute_not_plan.md` — execute, don't just plan (Tier 2)
5. `feedback_never_remove_features.md` — change HOW not WHAT (Tier 2)
6. `feedback_no_speculation.md` — facts or "I don't know" (Tier 2)
7. `feedback_commit_checkpoints.md` — commit every 3-5 changes (Tier 2)

Then add pointers to `MEMORY.md` under `## Feedback` (link text must match the target
filename). Append only — never rewrite an existing MEMORY.md:

```markdown
## Feedback
- [feedback_verify_before_writing.md](feedback_verify_before_writing.md) — Grep/Glob before creating anything
- [feedback_test_after_change.md](feedback_test_after_change.md) — verify after each change
- [feedback_diagnostic_sequence.md](feedback_diagnostic_sequence.md) — diagnostic sequence when something fails
- [feedback_execute_not_plan.md](feedback_execute_not_plan.md) — execute immediately, don't just plan
- [feedback_never_remove_features.md](feedback_never_remove_features.md) — change HOW not WHAT when simplifying
- [feedback_no_speculation.md](feedback_no_speculation.md) — facts or "I don't know yet"
- [feedback_commit_checkpoints.md](feedback_commit_checkpoints.md) — commit every 3-5 tested changes
```

---

## PHASE 5 — Skills

Create the skills that fit the project shape from Phase 1. Templates:
`Read ${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/templates/skill-templates/`

Gate skill creation on the analysis — do NOT impose service/Docker skills on a library or CLI.

### Always create:
1. **orchestrator** — dispatcher; routes to the right skill
2. **code-review** — end-to-end code review (works for any project)

### Create if the project has running services / Docker:
3. **smoke-test-all** — health check of all services
4. **deploy-and-verify** — rebuild + test + verify
5. **cross-service-debug** — only if the project has multiple services

### Create if relevant:
6. **code-audit** — scan for dangerous patterns
7. **task** — numbered-task execution
8. **opensrc-sync** — dependency source sync (only if Phase 6 is opted into)

### Domain skills (only if the project has a clear domain):
- Frontend dev, API dev, ML dev, Infra ops — per the detected stack

For each skill:
1. Read the template
2. Adapt to the real project (ports, URLs, commands, patterns)
3. Create it at `.claude/skills/<name>/SKILL.md`
4. Skip if that skill directory already exists (idempotency)

**Rule:** adapt the orchestrator's routing table to the skills you actually created — don't
route to a skill you skipped.

---

## PHASE 5.5 — Project wiki (optional)

Delegate wiki setup to the `cloclo:wiki` skill's INIT flow — it has its own exists-check and
is the single source of truth for the scaffold (do not inline a drifting copy here):

```
Invoke Skill("cloclo:wiki")  →  run INIT
```

The wiki INIT asks the domain question, creates `wiki/schema.md` + `index.md` + `log.md` +
the `pages/` directories, and skips if `wiki/schema.md` already exists.

Then ask the user ONE question about tracking:
> "Track the wiki in git? (yes = version history, shared with team / no = local only, gitignored)"

- If **local only**: add `wiki/` to `.gitignore`. Remember this choice for Phase 8 (do NOT
  `git add wiki/` and do NOT claim the wiki scaffold was committed).
- If **tracked**: leave `wiki/` out of `.gitignore`; Phase 8 may `git add wiki/`.

Finally, add a wiki routing row to the orchestrator skill's table.

---

## PHASE 6 — opensrc-sync (opt-in, optional)

This step is OPTIONAL. Only run it if the user explicitly wants dependency source syncing.
It requires Node.js 18+. Skip it entirely for most projects.

If opted in, install opensrc **user-locally** (no root, persistent path) — do NOT write to
`/usr/local/bin` and do NOT rely on `/tmp` (wiped on reboot):

```bash
mkdir -p "$HOME/.local/opensrc" "$HOME/.local/bin"
git clone https://github.com/vercel-labs/opensrc.git "$HOME/.local/opensrc/opensrc-cli" 2>/dev/null || true
( cd "$HOME/.local/opensrc/opensrc-cli" && npm install && npm run build )

cat > "$HOME/.local/bin/opensrc-run" << 'SCRIPT'
#!/usr/bin/env node
import(process.env.HOME + '/.local/opensrc/opensrc-cli/dist/index.js').then(m => m.createProgram().parse());
SCRIPT
chmod +x "$HOME/.local/bin/opensrc-run"
# Ensure ~/.local/bin is on PATH (add to shell profile if needed).
```

Then create `.claude/opensrc-tracked.json` with the project's core deps, fetch the sources,
and add `opensrc/` to `.gitignore`. The generated `opensrc-sync` skill (Phase 5, item 8) is
the single source for the install/fetch details — this block and that skill must not drift.

**Rule:** track only the core frameworks/libs, not utilities.

---

## PHASE 7 — Verification

```bash
ls .claude/skills/                       # skills scaffolded
head -5 CLAUDE.md                        # CLAUDE.md present
jq -e '.hooks' .claude/settings.json     # hooks valid + present
ls "$memdir"/feedback_*.md               # memories created
"$HOME/.local/bin/opensrc-run" list 2>/dev/null || true   # only if Phase 6 opted in
```

**Note on newly created skills:** creating a brand-new top-level `.claude/skills/` directory
requires the session to reload before the skills are discoverable. Tell the user to restart
the session (or `/reload`) before invoking any newly created skill, e.g. `orchestrator`. Do
NOT assert that Phase 7 can invoke and verify them in the same session — verify the files
exist on disk instead.

---

## PHASE 8 — Commit (requires confirmation)

Ask the user before committing. Never commit secrets.

Before staging: confirm no credentials/secrets are being added (no `.env`, no `.env.local`,
no tokens in CLAUDE.md). Stage conditionally on the Phase 5.5 wiki choice:

```bash
# Base stage — always:
git add .claude/ CLAUDE.md

# Only if the user chose to TRACK the wiki in Phase 5.5:
# git add wiki/

# Never git add an ignored path. Verify nothing sensitive is staged:
git diff --cached --name-only
```

Then commit (adjust the wiki line to match the actual choice):

```bash
git commit -m "feat: claude code setup — skills, hooks, memory, wiki

- CLAUDE.md adapted to the project
- Hooks: PostToolUse type-check + optional PreToolUse commit-blocker
- 7 behavioral memory seeds
- [N] skills (orchestrator, code-review, ...)
- wiki scaffold (tracked) — omit this line if wiki is local-only"
```

Note: the memory folder lives under `~/.claude/projects/...`, outside the repo — it is not
committed by design.

---

## Global rules

1. **No placeholders** — every file must be adapted to the real project.
2. **Phase 1 drives everything** — bad analysis makes everything else wrong.
3. **Verify hooks immediately** — after Phase 3, prove a hook actually fires.
4. **One commit at the end** — no intermediate commits during bootstrap.
5. **Confirm before committing and before any credential handling** — otherwise scaffolding
   proceeds without asking. Never overwrite an existing CLAUDE.md or MEMORY.md.
