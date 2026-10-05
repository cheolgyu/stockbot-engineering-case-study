#!/usr/bin/env python3
"""Reject files and text that do not belong in the public case study."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ALLOWED_NAMES = {".gitattributes", ".gitignore", "LICENSE"}
ALLOWED_SUFFIXES = {
    ".json",
    ".lock",
    ".md",
    ".ps1",
    ".py",
    ".rs",
    ".sql",
    ".toml",
    ".yaml",
    ".yml",
}
SKIPPED_PARTS = {".git", "target", "node_modules", "__pycache__"}
BLOCKED_PARTS = {".claude", ".idea", ".vscode", "aws", "data", "pem"}
BLOCKED_SUFFIXES = {
    ".7z",
    ".bak",
    ".db",
    ".dump",
    ".gz",
    ".jks",
    ".key",
    ".keystore",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".xlsx",
    ".zip",
}
BLOCKED_FILENAMES = {"dev.session.sql"}
MAX_FILE_BYTES = 1_048_576
MAX_REPOSITORY_BYTES = 5_242_880

CONTENT_PATTERNS = (
    (
        "private-key header",
        re.compile("BEGIN " + "(?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY"),
    ),
    ("AWS access key", re.compile(r"\bA[K]IA[0-9A-Z]{16}\b|\bA[S]IA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub[_]pat_[A-Za-z0-9_]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b")),
    ("Stripe live key", re.compile(r"\bs[k]_live_[A-Za-z0-9]{16,}\b")),
    ("OpenAI key", re.compile(r"\bs[k]-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    (
        "credential-bearing URL",
        re.compile(r"\b(?:postgres(?:ql)?|mongodb(?:\+srv)?|mysql|https?)://[^\s/:@]+:[^\s/@]+@", re.IGNORECASE),
    ),
    ("email address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    (
        "Windows user path",
        re.compile(r"\b[A-Za-z]:[\\/]Users[\\/][^\\/\s]+", re.IGNORECASE),
    ),
    (
        "authorization bearer value",
        re.compile(r"\bAuthorization\s*:\s*Bearer\s+[A-Za-z0-9._~+/-]{12,}", re.IGNORECASE),
    ),
    (
        "Azure storage account key",
        re.compile(r"\bAccount[K]ey\s*=\s*[A-Za-z0-9+/=]{40,}", re.IGNORECASE),
    ),
    (
        "Google service-account document",
        re.compile('"type"\\s*:\\s*"service' + '_account"', re.IGNORECASE),
    ),
    ("AWS ARN", re.compile(r"\barn:aws(?:-[a-z]+)?:", re.IGNORECASE)),
    ("AWS account id", re.compile(r"(?<!\d)\d{12}(?!\d)")),
    ("ECR hostname", re.compile(r"\b\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com\b", re.IGNORECASE)),
    (
        "IPv4 address",
        re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
    ),
)

SENSITIVE_ASSIGNMENT = re.compile(
    r"\b(password|passwd|token|secret|api[_-]?key|access[_-]?key)\b\s*[:=]\s*[\"']?([^\s,;\"'}]+)",
    re.IGNORECASE,
)
SAFE_ASSIGNMENT_VALUES = {
    "example",
    "placeholder",
    "redacted",
    "test-only",
    "trust",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    parser.add_argument(
        "--git-history",
        action="store_true",
        help="also scan every path and blob reachable from Git history",
    )
    return parser.parse_args()


def is_skipped(relative_path: Path) -> bool:
    return any(part.lower() in SKIPPED_PARTS for part in relative_path.parts)


def validate_path(relative_path: Path, size: int) -> list[str]:
    violations: list[str] = []

    lowered_parts = {part.lower() for part in relative_path.parts}
    if lowered_parts & BLOCKED_PARTS:
        violations.append(f"{relative_path}: blocked path component")

    lowered_name = relative_path.name.lower()
    if lowered_name.startswith(".env") or lowered_name in BLOCKED_FILENAMES:
        violations.append(f"{relative_path}: blocked filename")

    suffix = relative_path.suffix.lower()
    if suffix in BLOCKED_SUFFIXES:
        violations.append(f"{relative_path}: blocked file type")

    if relative_path.name not in ALLOWED_NAMES and suffix not in ALLOWED_SUFFIXES:
        violations.append(f"{relative_path}: file type is not on the publication allowlist")

    if size > MAX_FILE_BYTES:
        violations.append(f"{relative_path}: exceeds the 1 MiB per-file limit")

    return violations


def validate_text(display_path: str, text: str) -> list[str]:
    violations: list[str] = []

    for label, pattern in CONTENT_PATTERNS:
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            violations.append(f"{display_path}:{line}: possible {label}")

    for match in SENSITIVE_ASSIGNMENT.finditer(text):
        value = match.group(2).strip().lower()
        if value not in SAFE_ASSIGNMENT_VALUES:
            line = text.count("\n", 0, match.start()) + 1
            violations.append(f"{display_path}:{line}: non-placeholder sensitive assignment")

    return violations


def validate_file(path: Path, relative_path: Path) -> tuple[list[str], int]:
    size = path.stat().st_size
    violations = validate_path(relative_path, size)
    if size > MAX_FILE_BYTES:
        return violations, size

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        violations.append(f"{relative_path}: non-UTF-8 or binary content")
        return violations, size

    violations.extend(validate_text(str(relative_path), text))

    return violations, size


def git_output(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=text,
        encoding="utf-8" if text else None,
    )
    return result.stdout


def validate_tracked_layout(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []

    violations: list[str] = []
    stage_output = git_output(root, "ls-files", "--stage", "-z")
    assert isinstance(stage_output, str)

    for entry in stage_output.split("\0"):
        if not entry:
            continue
        metadata, path_text = entry.split("\t", 1)
        mode = metadata.split(" ", 1)[0]
        relative_path = Path(path_text)
        if is_skipped(relative_path):
            violations.append(f"{relative_path}: generated or skipped path must not be tracked")
        if mode == "120000":
            violations.append(f"{relative_path}: tracked symbolic links are not allowed")

    return violations


def validate_git_history(root: Path) -> tuple[list[str], int]:
    if not (root / ".git").exists():
        return ["--git-history requires an initialized Git repository"], 0

    violations: list[str] = []
    unique_blob_sizes: dict[str, int] = {}

    commit_emails = git_output(root, "log", "--all", "--format=%ae%n%ce")
    assert isinstance(commit_emails, str)
    if any(
        email and not email.lower().endswith("@users.noreply.github.com")
        for email in commit_emails.splitlines()
    ):
        violations.append("Git history contains a non-noreply author or committer email")

    object_output = git_output(root, "rev-list", "--objects", "--all")
    assert isinstance(object_output, str)

    for line in object_output.splitlines():
        if " " not in line:
            continue

        object_id, path_text = line.split(" ", 1)
        relative_path = Path(path_text)
        display_path = f"history:{object_id[:12]}:{path_text}"

        object_type = git_output(root, "cat-file", "-t", object_id).strip()
        if object_type != "blob":
            continue

        size = int(git_output(root, "cat-file", "-s", object_id).strip())
        unique_blob_sizes.setdefault(object_id, size)

        if is_skipped(relative_path):
            violations.append(f"{display_path}: generated or skipped path exists in history")
        violations.extend(validate_path(relative_path, size))
        if size > MAX_FILE_BYTES:
            continue

        content = git_output(root, "cat-file", "blob", object_id, text=False)
        assert isinstance(content, bytes)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            violations.append(f"{display_path}: non-UTF-8 or binary content")
            continue
        violations.extend(validate_text(display_path, text))

    history_bytes = sum(unique_blob_sizes.values())
    if history_bytes > MAX_REPOSITORY_BYTES:
        violations.append("Git history exceeds the 5 MiB publication limit")

    return violations, len(unique_blob_sizes)


def main() -> int:
    arguments = parse_args()
    root = Path(arguments.root).resolve()
    if not root.is_dir():
        print(f"privacy guard failed: not a directory: {root}", file=sys.stderr)
        return 2

    violations: list[str] = []
    scanned_files = 0
    total_bytes = 0

    for path in sorted(root.rglob("*")):
        relative_path = path.relative_to(root)
        if path.is_symlink():
            violations.append(f"{relative_path}: symbolic links are not allowed")
            continue
        if is_skipped(relative_path) or path.is_dir():
            continue

        file_violations, size = validate_file(path, relative_path)
        violations.extend(file_violations)
        scanned_files += 1
        total_bytes += size

    if total_bytes > MAX_REPOSITORY_BYTES:
        violations.append("repository exceeds the 5 MiB publication limit")

    try:
        violations.extend(validate_tracked_layout(root))
        history_blobs = 0
        if arguments.git_history:
            history_violations, history_blobs = validate_git_history(root)
            violations.extend(history_violations)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        violations.append(f"Git inspection failed: {error}")
        history_blobs = 0

    if violations:
        print("privacy guard failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    history_summary = f", {history_blobs} historical blobs" if arguments.git_history else ""
    print(
        f"privacy guard passed: {scanned_files} files, {total_bytes} bytes{history_summary}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
