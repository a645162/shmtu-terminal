#!/usr/bin/env python3
"""Upgrade npm dependencies across all sub-projects.

The script finds every relevant ``package.json`` under the repository root,
updates declared versions with ``npm-check-updates``, and optionally refreshes
lockfiles in a package-manager-aware way.

Default behavior:
  - discover projects containing ``package.json``
  - run ``npm-check-updates -u`` in each project

With ``-i`` / ``--install``:
  - refresh ``package-lock.json`` via ``npm install --package-lock-only``
  - refresh ``bun.lock`` / ``bun.lockb`` via ``bun install --lockfile-only``
  - if a project has no known lockfile yet, create ``package-lock.json``

``npm-check-updates`` runner resolution:
  - prefer ``bun x npm-check-updates``
  - fallback to ``npx npm-check-updates``
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

KNOWN_LOCKFILES = (
    "package-lock.json",
    "bun.lock",
    "bun.lockb",
    "pnpm-lock.yaml",
    "yarn.lock",
)

PRUNE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "cache",
    "coverage",
    "target",
    ".next",
    ".turbo",
    ".pnpm-store",
}


@dataclass(frozen=True)
class Project:
    dir_path: Path
    lockfiles: tuple[str, ...]

    @property
    def rel_path(self) -> Path:
        if self.dir_path.is_relative_to(REPO_ROOT):
            return self.dir_path.relative_to(REPO_ROOT)
        return self.dir_path

    @property
    def rel_str(self) -> str:
        return str(self.rel_path)


class Progress:
    """Thread-safe progress output with a compact live bar on TTYs."""

    BAR_WIDTH = 24

    def __init__(self, total: int) -> None:
        self.total = total
        self._done = 0
        self._running = 0
        self._success = 0
        self._fail = 0
        self._lock = threading.Lock()
        self._tty = sys.stdout.isatty()
        self._num_width = len(str(total))

    def start(self, name: str) -> None:
        with self._lock:
            self._running += 1
            if self._tty:
                self._draw()
            else:
                self._emit_line(f"  START {name}")

    def finish(self, name: str, success: bool) -> None:
        with self._lock:
            self._running -= 1
            self._done += 1
            if success:
                self._success += 1
            else:
                self._fail += 1

            tag = "OK " if success else "ERR"
            line = f"  [{self._done:>{self._num_width}}/{self.total}] {tag} {name}"
            if self._tty:
                self._clear_line()
                sys.stdout.write(line + "\n")
                self._draw()
            else:
                self._emit_line(line)

    def log_detail(self, lines: list[str]) -> None:
        with self._lock:
            if self._tty:
                self._clear_line()
            for line in lines:
                sys.stdout.write(line + "\n")
            sys.stdout.flush()
            if self._tty:
                self._draw()

    def finish_all(self) -> None:
        with self._lock:
            if self._tty:
                self._clear_line()
                sys.stdout.flush()

    def _draw(self) -> None:
        ratio = self._done / self.total if self.total else 1.0
        filled = int(self.BAR_WIDTH * ratio)
        bar = "#" * filled + "-" * (self.BAR_WIDTH - filled)
        parts = [f"[{bar}] {self._done}/{self.total}"]
        if self._running:
            parts.append(f"running={self._running}")
        if self._fail:
            parts.append(f"failed={self._fail}")
        sys.stdout.write("\r  " + "  ".join(parts))
        sys.stdout.flush()

    def _clear_line(self) -> None:
        sys.stdout.write("\r\033[K")

    def _emit_line(self, line: str) -> None:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upgrade npm dependencies across all package.json projects.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repository root (default: auto-detect)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        help="max parallel workers; 1=serial, -1=cpu count, 0=executor default",
    )
    parser.add_argument(
        "-i",
        "--install",
        action="store_true",
        help="refresh lockfiles after package.json has been updated",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show planned commands without modifying files",
    )
    parser.add_argument(
        "--match",
        action="append",
        default=[],
        metavar="TEXT",
        help="only process projects whose relative path contains TEXT; repeatable",
    )
    return parser.parse_args()


def should_skip_dir(name: str) -> bool:
    if name in PRUNE_DIRS:
        return True
    if name.startswith(".") and name != ".github":
        return True
    return False


def discover_projects(root: Path) -> list[Project]:
    projects: list[Project] = []
    seen: set[Path] = set()

    for current_root, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not should_skip_dir(d))
        if "package.json" not in files:
            continue

        project_dir = Path(current_root)
        if project_dir in seen:
            continue
        seen.add(project_dir)

        lockfiles = tuple(name for name in KNOWN_LOCKFILES if (project_dir / name).exists())
        projects.append(Project(project_dir, lockfiles))

    return sorted(projects, key=lambda p: p.rel_str)


def filter_projects(projects: list[Project], matches: list[str]) -> list[Project]:
    if not matches:
        return projects
    lowered = [item.lower() for item in matches]
    filtered: list[Project] = []
    for project in projects:
        rel = project.rel_str.lower()
        if any(token in rel for token in lowered):
            filtered.append(project)
    return filtered


def resolve_jobs(value: int) -> int | None:
    if value < -1:
        raise SystemExit("--jobs must be -1, 0, or a positive integer")
    if value == -1:
        return os.cpu_count() or 1
    if value == 0:
        return None
    return value


def choose_ncu_cmd() -> list[str]:
    if shutil.which("bun"):
        return ["bun", "x", "npm-check-updates", "-u"]
    if shutil.which("npx"):
        return ["npx", "--yes", "npm-check-updates", "-u"]
    raise SystemExit("missing required executable: bun or npx")


def validate_prereqs(do_install: bool) -> None:
    missing: list[str] = []
    if not shutil.which("bun") and not shutil.which("npx"):
        missing.append("bun or npx")
    if do_install and not shutil.which("npm"):
        missing.append("npm")
    if missing:
        raise SystemExit("missing required executable(s): " + ", ".join(missing))


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def format_command(cmd: list[str]) -> str:
    return " ".join(cmd)


def make_lockfile_steps(project: Project) -> list[tuple[list[str], str]]:
    steps: list[tuple[list[str], str]] = []

    has_npm_lock = "package-lock.json" in project.lockfiles
    has_bun_lock = "bun.lock" in project.lockfiles or "bun.lockb" in project.lockfiles
    has_any_lock = bool(project.lockfiles)

    if has_npm_lock or not has_any_lock:
        steps.append((["npm", "install", "--package-lock-only"], "npm lock"))
    if has_bun_lock:
        steps.append((["bun", "install", "--lockfile-only"], "bun lock"))

    return steps


def run_step(
    cmd: list[str],
    cwd: Path,
    label: str,
    rel_str: str,
    *,
    dry_run: bool,
    progress: Progress | None,
) -> tuple[bool, str]:
    if dry_run:
        if progress is not None:
            progress.log_detail([f"  PLAN {rel_str}: {format_command(cmd)}"])
        return True, f"{label}(dry)"

    rc, out = run_cmd(cmd, cwd)
    if rc != 0:
        lines = [f"  FAIL {rel_str}: {format_command(cmd)} (exit {rc})"]
        for line in out.strip().splitlines():
            lines.append(f"    {line}")
        if progress is not None:
            progress.log_detail(lines)
        return False, f"{label}!"

    interesting: list[str] = []
    if "npm-check-updates" in " ".join(cmd):
        interesting = [
            line for line in out.strip().splitlines() if "->" in line or "→" in line or "upgraded" in line.lower()
        ]
    if interesting and progress is not None:
        progress.log_detail([f"  UPD  {rel_str}:"] + [f"    {line}" for line in interesting])

    return True, f"{label}+"


def process_project(
    project: Project,
    *,
    ncu_cmd: list[str],
    dry_run: bool,
    do_install: bool,
    progress: Progress | None,
) -> tuple[Project, bool, str, float]:
    summary: list[str] = []
    success = True
    start_time = time.monotonic()

    if progress is not None:
        progress.start(project.rel_str)

    ok, tag = run_step(
        ncu_cmd,
        project.dir_path,
        "ncu",
        project.rel_str,
        dry_run=dry_run,
        progress=progress,
    )
    summary.append(tag)
    success = success and ok

    if do_install:
        for cmd, label in make_lockfile_steps(project):
            if label == "bun lock" and not shutil.which("bun"):
                if progress is not None:
                    progress.log_detail([f"  SKIP {project.rel_str}: bun not installed, skip bun lock refresh"])
                success = False
                summary.append("bun(skip)")
                continue

            ok, tag = run_step(
                cmd,
                project.dir_path,
                label,
                project.rel_str,
                dry_run=dry_run,
                progress=progress,
            )
            summary.append(tag)
            success = success and ok

    elapsed = time.monotonic() - start_time
    if progress is not None:
        progress.finish(project.rel_str, success)

    return project, success, " ".join(summary), elapsed


def main() -> int:
    args = parse_args()
    root = args.root.resolve()

    if not (root / ".git").exists():
        print(f"ERROR: {root} does not look like a git repository root.", file=sys.stderr)
        return 2

    validate_prereqs(args.install)
    ncu_cmd = choose_ncu_cmd()
    projects = filter_projects(discover_projects(root), args.match)

    if not projects:
        print("No matching package.json projects found.")
        return 0

    total = len(projects)
    width = len(str(total))
    print(f"Found {total} project(s):\n")
    for index, project in enumerate(projects, 1):
        locks = ", ".join(project.lockfiles) if project.lockfiles else "<none>"
        print(f"  [{index:>{width}}/{total}] {project.rel_str}  [{locks}]")
    print()

    steps = [format_command(ncu_cmd)]
    if args.install:
        steps.append("lockfile refresh")
    workers = resolve_jobs(args.jobs)
    mode = "serial" if workers == 1 else ("executor default" if workers is None else f"{workers} workers")

    print("-" * 64)
    print(f"  {' -> '.join(steps)}  ({mode})")
    print("-" * 64)
    print()

    progress = Progress(total)
    results: list[tuple[Project, bool, str, float]] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                process_project,
                project,
                ncu_cmd=ncu_cmd,
                dry_run=args.dry_run,
                do_install=args.install,
                progress=progress,
            ): project
            for project in projects
        }
        for future in as_completed(futures):
            results.append(future.result())

    progress.finish_all()
    results.sort(key=lambda item: item[0].rel_str)

    ok_count = sum(1 for _, ok, _, _ in results if ok)
    fail_count = total - ok_count
    total_seconds = sum(elapsed for _, _, _, elapsed in results)

    print()
    print("-" * 64)
    print("  Results:\n")
    for project, ok, summary, elapsed in results:
        status = "OK " if ok else "ERR"
        print(f"  {status} {project.rel_str:55s} {summary}  ({elapsed:.1f}s)")

    print()
    print("=" * 64)
    if fail_count:
        print(f"  {ok_count}/{total} succeeded, {fail_count} failed  ({total_seconds:.1f}s total)")
        return 1
    print(f"  All {total} projects succeeded  ({total_seconds:.1f}s total)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        raise SystemExit(130)
