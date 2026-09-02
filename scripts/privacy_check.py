#!/usr/bin/env python3
"""Fail when tracked files contain common secrets or deployment identities."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
MAX_TEXT_BYTES = 8 * 1024 * 1024

SENSITIVE_SUFFIXES = {
    ".bak",
    ".bundle",
    ".db",
    ".dump",
    ".har",
    ".jks",
    ".key",
    ".keystore",
    ".log",
    ".p12",
    ".pcap",
    ".pcapng",
    ".pem",
    ".pfx",
    ".sqlite",
    ".sqlite3",
}
SENSITIVE_DIRECTORIES = {".ssh", "credentials", "secrets"}
SAFE_HOME_USERS = {"apt-hunter", "example", "user"}
PRIVATE_ADDRESS_SCOPES = (
    "README.md",
    "SECURITY.md",
    "design-qa.md",
    ".github/",
    "docs/",
    "infra/",
)

PATTERNS = (
    (
        "private key",
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "provider token",
        re.compile(
            rb"(?:sk-[A-Za-z0-9_-]{16,}|github_pat_[A-Za-z0-9_]{20,}|"
            rb"gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
            rb"xox[baprs]-[A-Za-z0-9-]{10,})"
        ),
    ),
    (
        "credential embedded in URL",
        re.compile(
            rb"(?i)(?:https?|postgres(?:ql)?(?:\+[A-Za-z0-9._-]+)?|redis)://"
            rb"[^\s/:]+:[^\s/@]+@"
        ),
    ),
    (
        "Windows user profile",
        re.compile(rb"(?i)[A-Z]:\\Users\\(?!example(?:\\|$))[^\\\s]+"),
    ),
)

PRIVATE_IPV4 = re.compile(
    rb"(?<!\d)(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
    rb"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(?!\d)"
)
UNIX_HOME = re.compile(rb"/home/([A-Za-z0-9._-]+)")
PLACEHOLDERS = (b"change-me", b"replace-with", b"example", b"${")


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def sensitive_path(path: str) -> str | None:
    pure = PurePosixPath(path)
    lowered = path.lower()
    if pure.name == ".env" or (
        pure.name.startswith(".env.")
        and not pure.name.endswith((".example", ".sample", ".template"))
    ):
        return "runtime environment file"
    if pure.suffix.lower() in SENSITIVE_SUFFIXES:
        return f"sensitive artifact ({pure.suffix.lower()})"
    if any(part.lower() in SENSITIVE_DIRECTORIES for part in pure.parts):
        return "sensitive directory"
    if lowered.endswith(("id_rsa", "id_ed25519")):
        return "SSH private key"
    return None


def scan_content(path: str, content: bytes) -> set[str]:
    findings: set[str] = set()
    for label, pattern in PATTERNS:
        for match in pattern.finditer(content):
            if label == "credential embedded in URL" and any(
                placeholder in match.group(0).lower() for placeholder in PLACEHOLDERS
            ):
                continue
            findings.add(label)

    if path.startswith(PRIVATE_ADDRESS_SCOPES) and PRIVATE_IPV4.search(content):
        findings.add("private deployment address")

    for match in UNIX_HOME.finditer(content):
        if match.group(1).decode("ascii", errors="ignore") not in SAFE_HOME_USERS:
            findings.add("personal Unix home directory")
    return findings


def main() -> int:
    findings: list[tuple[str, str]] = []
    for relative in tracked_files():
        path_reason = sensitive_path(relative)
        if path_reason:
            findings.append((relative, path_reason))
            continue

        absolute = ROOT / relative
        if not absolute.is_file() or absolute.stat().st_size > MAX_TEXT_BYTES:
            continue
        content = absolute.read_bytes()
        if b"\0" in content:
            continue
        for reason in sorted(scan_content(relative, content)):
            findings.append((relative, reason))

    if findings:
        print("Privacy check failed. No secret values are printed:", file=sys.stderr)
        for path, reason in sorted(set(findings)):
            print(f"- {path}: {reason}", file=sys.stderr)
        return 1

    print(f"Privacy check passed for {len(tracked_files())} tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
