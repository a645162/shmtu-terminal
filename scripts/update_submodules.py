#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sync and update git submodules for this repository. "
            "By default, this initializes newly added submodules and updates "
            "all nested submodules recursively."
        )
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (default: auto-detect from this script)",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help=(
            "also fetch the latest commits from each submodule's tracked remote "
            "branch"
        ),
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=0,
        help="parallel jobs for submodule update (default: let git decide)",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="skip 'git submodule sync --recursive'",
    )
    parser.add_argument(
        "--no-status",
        action="store_true",
        help="skip final 'git submodule status --recursive'",
    )
    return parser.parse_args()


def run_command(command: list[str], cwd: Path) -> int:
    pretty = " ".join(command)
    print(f"\n>>> {pretty}", flush=True)
    completed = subprocess.run(command, cwd=cwd)
    return completed.returncode


def ensure_git_available() -> None:
    if shutil.which("git") is None:
        print("ERROR: git was not found in PATH.", file=sys.stderr)
        raise SystemExit(127)


def ensure_repo_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        print(
            f"ERROR: {repo_root} does not look like a git repository root.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return repo_root


def main() -> int:
    args = parse_args()
    ensure_git_available()
    repo_root = ensure_repo_root(args.repo)

    print(f"Repository: {repo_root}", flush=True)

    if not args.no_sync:
        rc = run_command(["git", "submodule", "sync", "--recursive"], repo_root)
        if rc != 0:
            return rc

    update_command = [
        "git",
        "submodule",
        "update",
        "--init",
        "--recursive",
        "--progress",
    ]
    if args.remote:
        update_command.append("--remote")
    if args.jobs > 0:
        update_command.extend(["--jobs", str(args.jobs)])

    rc = run_command(update_command, repo_root)
    if rc != 0:
        return rc

    if not args.no_status:
        rc = run_command(["git", "submodule", "status", "--recursive"], repo_root)
        if rc != 0:
            return rc

    print("\nDone.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        raise SystemExit(130)
