#!/usr/bin/env python3
"""Resolve the installed GLM dependency and forward its public CLI."""

from __future__ import annotations

import os
import sys

from run_glm_review import resolve_companion


def main() -> int:
    command = resolve_companion()
    if not command:
        print(
            "GLM Companion is unavailable. Install or enable glm@cloclo, or set GLM_COMPANION_BIN.",
            file=sys.stderr,
        )
        return 2
    os.execv(command[0], [*command, *sys.argv[1:]])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
