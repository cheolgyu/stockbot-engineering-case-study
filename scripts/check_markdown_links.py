#!/usr/bin/env python3
"""Check that relative links in Markdown files resolve inside the repository."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    failures: list[str] = []
    checked = 0

    for document in sorted(root.rglob("*.md")):
        if any(part in {".git", "target"} for part in document.parts):
            continue

        text = document.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK.finditer(line):
                raw_target = match.group(1).strip().strip("<>")
                if raw_target.startswith(("#", "https://", "http://", "mailto:")):
                    continue

                path_part = unquote(raw_target.split("#", 1)[0])
                if not path_part:
                    continue

                target = (document.parent / path_part).resolve()
                try:
                    target.relative_to(root)
                except ValueError:
                    failures.append(
                        f"{document.relative_to(root)}:{line_number}: link escapes repository"
                    )
                    continue

                checked += 1
                if not target.exists():
                    failures.append(
                        f"{document.relative_to(root)}:{line_number}: missing {raw_target}"
                    )

    if failures:
        print("Markdown link check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Markdown link check passed: {checked} relative links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
