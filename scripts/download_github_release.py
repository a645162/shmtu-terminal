#!/usr/bin/env python3
"""
Download every asset of a GitHub release tag, generate sha256checksum.txt,
then re-download the same release 10 times and verify each file's hash
against the original SHA256SUMS.txt file.

Designed for the SHMTU CAS OCR model releases (a645162/shmtu-cas-ocr-model)
but works against any public GitHub repository.

Anonymous API access only. If the GitHub REST API is rate-limited, the script
falls back to scraping the `expanded_assets` HTML page to discover asset
download URLs.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        TextColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )
except ImportError:
    Console = None  # type: ignore[assignment]

# ---------- Defaults tuned for the SHMTU CAS OCR model release ----------

DEFAULT_OWNER = "a645162"
DEFAULT_REPO = "shmtu-cas-ocr-model"
DEFAULT_TAGS = ["v1.0-NCNN", "v1.0-ONNX"]

USER_AGENT = "shmtu-terminal-release-downloader/1.0"

DEFAULT_VERIFY_ROUNDS = 10
CHECKSUM_FILENAME = "SHA256SUMS.txt"

GITHUB_API_RELEASE = "https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
GITHUB_EXPANDED_ASSETS = (
    "https://github.com/{owner}/{repo}/releases/expanded_assets/{tag}"
)


# --------------------------------------------------------------------------- #
#  Console / progress helpers
# --------------------------------------------------------------------------- #

def make_console():
    if Console is None:
        return None
    return Console(stderr=False, force_terminal=False, soft_wrap=True)


def make_progress():
    if Console is None:
        return None
    return Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="left"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=Console(stderr=True),
        transient=False,
    )


# --------------------------------------------------------------------------- #
#  Asset discovery
# --------------------------------------------------------------------------- #

def _http_get_json(url, timeout=30.0):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        import json

        return json.loads(resp.read().decode("utf-8"))


def _http_get_text(url, timeout=30.0):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_assets_via_api(owner, repo, tag):
    """Use the GitHub REST API. Returns assets in release order.

    Raises urllib.error.HTTPError on non-2xx — the caller decides whether to
    fall back to HTML scraping.
    """
    url = GITHUB_API_RELEASE.format(owner=owner, repo=repo, tag=tag)
    payload = _http_get_json(url)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected GitHub API response shape: {type(payload)}")
    assets = payload.get("assets") or []
    return [a for a in assets if a.get("browser_download_url")]


class _ExpandedAssetsParser(HTMLParser):
    """Pulls release download URLs out of the expanded_assets HTML page.

    GitHub's expanded_assets page embeds the download links as relative
    ``/<owner>/<repo>/releases/download/<tag>/<asset>`` href values rather
    than absolute URLs, so we reconstruct the absolute form from the page URL.
    """

    HREF_RE = re.compile(
        r"/[^\s\"'<>]*/releases/download/[^\s\"'<>]+",
        re.IGNORECASE,
    )

    def __init__(self, base_url):
        super().__init__()
        self.base = base_url
        self.urls: list[str] = []
        self._in_anchor = False
        self._current_href: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._in_anchor = True
            self._current_href = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag.lower() == "a":
            self._in_anchor = False
            self._current_href = None

    def handle_data(self, data):
        candidates: list[str] = []
        if self._in_anchor and self._current_href and "releases/download/" in self._current_href:
            candidates.append(self._current_href)
        candidates.extend(self.HREF_RE.findall(data))
        for raw in candidates:
            absolute = urllib.parse.urljoin(self.base, raw)
            self.urls.append(absolute)


def fetch_assets_via_html(owner, repo, tag):
    """Last-resort fallback for when the REST API is rate-limited."""
    url = GITHUB_EXPANDED_ASSETS.format(owner=owner, repo=repo, tag=tag)
    html = _http_get_text(url)
    parser = _ExpandedAssetsParser(url)
    parser.feed(html)

    seen: set[str] = set()
    unique: list[str] = []
    for u in parser.urls:
        if u in seen:
            continue
        seen.add(u)
        unique.append(u)

    return [
        {
            "name": Path(urllib.parse.urlparse(u).path).name,
            "browser_download_url": u,
            "size": 0,
        }
        for u in unique
    ]


def discover_assets(owner, repo, tag, console):
    try:
        assets = fetch_assets_via_api(owner, repo, tag)
        if console:
            console.print(
                f"[green]+[/green] Discovered {len(assets)} asset(s) via REST API"
            )
        return assets
    except urllib.error.HTTPError as exc:
        if console:
            console.print(
                f"[yellow]![/yellow] REST API HTTP {exc.code}; "
                f"falling back to HTML scraping"
            )
    except Exception as exc:
        if console:
            console.print(
                f"[yellow]![/yellow] REST API failed ({exc!r}); "
                f"falling back to HTML scraping"
            )

    assets = fetch_assets_via_html(owner, repo, tag)
    if console:
        console.print(
            f"[green]+[/green] Discovered {len(assets)} asset(s) via HTML scrape"
        )
    return assets


# --------------------------------------------------------------------------- #
#  Download + hashing
# --------------------------------------------------------------------------- #

CHUNK = 64 * 1024


def hash_file(path, algo="sha256"):
    h = hashlib.new(algo)
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def download_one(url, destination, progress=None, overwrite=True):
    """Download a single asset with an optional rich progress bar."""
    task_id = None
    if progress is not None:
        task_id = progress.add_task(
            "download", filename=destination.name, total=None, start=False
        )

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    tmp_path = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = resp.headers.get("Content-Length")
            total = int(total) if total and total.isdigit() else None

            if progress is not None and task_id is not None:
                progress.update(task_id, total=total, start=True)

            with tmp_path.open("wb") as out:
                downloaded = 0
                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if progress is not None and task_id is not None:
                        progress.update(task_id, completed=downloaded)

        if progress is not None and task_id is not None:
            progress.update(task_id, completed=total or downloaded)

        if destination.exists() and not overwrite:
            tmp_path.unlink(missing_ok=True)
            return
        shutil.move(tmp_path, destination)
    finally:
        tmp_path.unlink(missing_ok=True)
        if progress is not None and task_id is not None:
            progress.remove_task(task_id)


def write_checksum(files, output):
    """Write a sha256checksum.txt file and return a {filename: hex} map."""
    mapping = {}
    lines = []
    for f in files:
        digest = hash_file(f, "sha256")
        mapping[f.name] = digest
        lines.append(f"{digest}  {f.name}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return mapping


def verify_against_checksum(files, checksum_path):
    """Compare each file's SHA256 with the value recorded in checksum_path.

    Returns (ok_count, mismatches) where each mismatch is
    (path, expected_hex, actual_hex).
    """
    expected = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([a-fA-F0-9]{64})\s+\*?(.+)$", line)
        if not match:
            continue
        expected[match.group(2).strip()] = match.group(1).lower()

    ok = 0
    mismatches = []
    for f in files:
        actual = hash_file(f, "sha256")
        want = expected.get(f.name)
        if want is None:
            mismatches.append((f, "<missing in checksum>", actual))
        elif want != actual:
            mismatches.append((f, want, actual))
        else:
            ok += 1
    return ok, mismatches


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Download every asset of a GitHub release tag, emit a "
            "SHA256SUMS.txt, then re-download N times to verify."
        ),
    )
    parser.add_argument("--owner", default=DEFAULT_OWNER, help="repo owner")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="repo name")
    parser.add_argument(
        "--tag",
        nargs="+",
        default=DEFAULT_TAGS,
        dest="tags",
        help="one or more release tags (default: v1.0-NCNN v1.0-ONNX)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="output directory (default: ./<owner>-<repo>-<tag>/ per tag)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=DEFAULT_VERIFY_ROUNDS,
        help=(
            "total number of download+verify rounds (default: 10). "
            "Round 1 generates sha256checksum.txt; rounds 2..N re-download "
            "and compare against it."
        ),
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help=(
            "keep the re-downloaded files from verification rounds "
            "(default: discard them, only the first round's files persist)"
        ),
    )
    return parser.parse_args()


class _NullContext:
    """Stand-in for `rich.progress.Progress` when rich is missing."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def process_tag(owner, repo, tag, dest, rounds, keep_files, console):
    progress = make_progress()

    dest.mkdir(parents=True, exist_ok=True)

    console.print(
        f"[bold]Release[/bold]  : {owner}/{repo} @ {tag}\n"
        f"[bold]Output[/bold]  : {dest}\n"
        f"[bold]Rounds[/bold]  : {rounds}\n"
    )

    assets = discover_assets(owner, repo, tag, console)
    if not assets:
        console.print("[red]No assets found for this release.[/red]")
        return False

    for a in assets:
        console.print(f"  - {a['name']}")

    overall_ok = True

    # Round 1: baseline download
    console.rule(f"[bold]Round 1/{rounds} -- baseline download")
    with progress or _NullContext():
        for asset in assets:
            target = dest / asset["name"]
            download_one(asset["browser_download_url"], target, progress=progress)

    checksum_path = dest / CHECKSUM_FILENAME
    files = sorted(
        p for p in dest.iterdir()
        if p.is_file() and p.name != CHECKSUM_FILENAME
    )
    write_checksum(files, checksum_path)
    console.print(
        f"[green]+[/green] Wrote [bold]{CHECKSUM_FILENAME}[/bold] "
        f"with {len(files)} entries"
    )

    for round_idx in range(2, rounds + 1):
        console.rule(f"[bold]Round {round_idx}/{rounds} -- re-download & verify")
        work = dest / f".verify-round-{round_idx}"
        work.mkdir(parents=True, exist_ok=True)

        with progress or _NullContext():
            for asset in assets:
                target = work / asset["name"]
                download_one(asset["browser_download_url"], target, progress=progress)

        ok, mismatches = verify_against_checksum(
            sorted(work.iterdir()), checksum_path
        )
        total = len(list(work.iterdir()))

        if mismatches:
            overall_ok = False
            console.print(
                f"[red]x Round {round_idx}: {ok}/{total} OK, "
                f"{len(mismatches)} mismatch(es)[/red]"
            )
            for path, expected, actual in mismatches:
                console.print(
                    f"    {path.name}\n"
                    f"      expected: {expected}\n"
                    f"      actual  : {actual}"
                )
        else:
            console.print(
                f"[green]+ Round {round_idx}: {ok}/{total} files match "
                f"{CHECKSUM_FILENAME}[/green]"
            )

        if not keep_files:
            shutil.rmtree(work, ignore_errors=True)

    console.rule("[bold]Summary")
    if overall_ok:
        console.print(
            f"[green]All {rounds} round(s) passed.[/green] "
            f"Checksum file: {checksum_path}"
        )
    else:
        console.print("[red]One or more rounds reported mismatches.[/red]")
    return overall_ok


def main():
    if Console is None:
        print(
            "ERROR: the 'rich' package is required. Install with: pip install rich",
            file=sys.stderr,
        )
        return 2

    args = parse_args()
    if args.rounds < 1:
        print("--rounds must be >= 1", file=sys.stderr)
        return 2

    console = make_console()
    all_ok = True

    for tag in args.tags:
        dest = args.dest
        if dest is None:
            dest = Path(f"{args.owner}-{args.repo}-{tag}")
        dest = dest.resolve()

        ok = process_tag(
            args.owner, args.repo, tag, dest,
            args.rounds, args.keep_files, console,
        )
        if not ok:
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        raise SystemExit(130)
