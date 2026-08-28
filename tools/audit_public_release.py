from __future__ import annotations

lazy import re
lazy import subprocess
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    "",
    ".cff",
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
FORBIDDEN_FILENAMES = (
    re.compile(r"^\.env$", re.IGNORECASE),
    re.compile(r".*\.(?:db|sqlite|sqlite3|dpapi|mohan-profile)$", re.IGNORECASE),
    re.compile(r".*\.(?:pem|key|p12|pfx)$", re.IGNORECASE),
    re.compile(
        r"(?:client[_-]?secret|credentials|oauth|token|secret).*\.(?:json|txt)$",
        re.IGNORECASE,
    ),
)
SECRET_PATTERNS = {
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "Google OAuth secret": re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{10,}\b"),
    "Google OAuth client ID": re.compile(
        r"\b\d+-[A-Za-z0-9_-]{20,}\.apps\.googleusercontent\.com\b"
    ),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "hard-coded Windows user path": re.compile(
        r"(?i)\bC:\\Users\\(?!USERNAME(?:\\|$)|<[^>]+>)[^\\\s]+\\"
    ),
}


def _git_paths(root: Path, *selectors: str) -> set[str]:
    safe_directory = (
        f"safe.directory={ROOT.as_posix()}"
        if root == ROOT
        else f"safe.directory={root.as_posix()}"
    )
    result = subprocess.run(
        [
            "git",
            "-c",
            safe_directory,
            "ls-files",
            "-z",
            *selectors,
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return {
        item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    }


def public_source_files(root: Path = ROOT) -> list[Path]:
    candidates = _git_paths(
        root,
        "--cached",
        "--others",
        "--exclude-standard",
    )
    deleted = _git_paths(root, "--deleted")
    return [root / relative for relative in sorted(candidates - deleted)]


def audit_source_file(path: Path, findings: list[str]) -> tuple[int, bool]:
    relative = path.relative_to(ROOT).as_posix()
    if not path.is_file():
        findings.append(f"tracked path is missing: {relative}")
        return 0, False

    size = path.stat().st_size
    if size > 50 * 1024 * 1024:
        findings.append(f"file exceeds 50 MiB: {relative}")
    if any(pattern.fullmatch(path.name) for pattern in FORBIDDEN_FILENAMES):
        findings.append(f"private filename is tracked: {relative}")
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return size, False

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        findings.append(f"text file is not UTF-8: {relative}")
        return size, False
    secret_detected = any(pattern.search(text) for pattern in SECRET_PATTERNS.values())
    return size, secret_detected


def main() -> int:
    findings: list[str] = []
    secret_detected = False
    # Include new, untracked source files during local pre-commit review. In
    # CI the same command naturally resolves to the checked-in public tree.
    files = public_source_files()
    total_bytes = 0
    for path in files:
        size, file_contains_secret = audit_source_file(path, findings)
        total_bytes += size
        secret_detected |= file_contains_secret

    if findings or secret_detected:
        print("PUBLIC_RELEASE_AUDIT_FAILED", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        if secret_detected:
            print(
                "- Potential secret detected; value, file, and location redacted.",
                file=sys.stderr,
            )
        return 1
    print(
        "PUBLIC_RELEASE_AUDIT_OK "
        f"files={len(files)} total_mib={total_bytes / 1024 / 1024:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
