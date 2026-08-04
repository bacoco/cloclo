Run a stop-gate review of the immediately previous Codex turn.

Only review direct code changes made in that turn. If the turn made no code changes, answer `ALLOW: no code changes in the previous turn`. Verify edits from repository state rather than trusting the response text. If changes were made, inspect for a blocking correctness, security, data-loss, rollback, retry, race, compatibility, or empty-state issue.

Your first line must be exactly `ALLOW: <reason>` or `BLOCK: <reason>`. Use BLOCK only for a concrete issue that must be fixed before stopping.

Previous Codex response:
{{CODEX_RESPONSE}}
