# Code Review — Template

## Frontmatter
```yaml
name: code-review
description: "Use when reviewing recent changes end-to-end before merging — checks correctness, secrets, error handling, and regressions. Triggers: review, read over, check the code, code audit"
```

## Scope
1. `git diff --stat HEAD~5` — which files changed recently?
2. For each changed file: read the code, understand the change.

## Checklist
- [ ] No committed secrets (.env, credentials)
- [ ] No debug console.log / print
- [ ] Proper error handling
- [ ] Correct types (no `any` in TS, no missing types in Python)
- [ ] No duplicated code
- [ ] Tests for new functionality
- [ ] No regressions in existing functionality

## Report
For each issue found:
- **File:line** — description of the problem
- **Severity**: High / Medium / Low
- **Suggested fix**: [code or description]
