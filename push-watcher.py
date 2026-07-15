

#!/usr/bin/env python3
"""push-watcher.py — Watches the results folder for new .json files,
copies them into the repo's data/ folder, pushes to GitHub, and deletes
the source files.

manifest.json / bundle.json are NOT built here. They are derived from
data/ by .github/workflows/pages.yml at deploy time.
"""

import argparse
import json
import re
import shutil
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("/home/feet/Desktop/checker/results")
REPO_DIR = Path("/home/feet/Desktop/www/trail")
POLL_INTERVAL = 15
DATA_DIR = "data"

# Files the engine drops in results/ that are not per-package records.
SKIP_NAMES = {"summary.json"}

# json_<pkg>__v1_0_2.json  ->  json_<pkg>
VERSIONED = re.compile(r"^(json_.+?)__v[\d_].*\.json$")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, timeout=120
    )


def push(repo, msg):
    git(repo, "add", "-A")

    result = git(repo, "commit", "-m", msg)
    if result.returncode != 0:
        if "nothing to commit" in result.stdout:
            return
        log(f"git commit failed: {result.stderr.strip()}")
        return

    if git(repo, "push").returncode == 0:
        log(f"Pushed: {msg}")
        return

    # Non-fast-forward: the remote moved. Rebase onto it and retry once.
    log("push rejected, rebasing onto remote")
    if git(repo, "pull", "--rebase").returncode != 0:
        git(repo, "rebase", "--abort")
        git(repo, "reset", "HEAD~1")
        raise RuntimeError("rebase failed - resolve by hand")

    if git(repo, "push").returncode != 0:
        git(repo, "reset", "HEAD~1")
        raise RuntimeError("push failed after rebase")

    log(f"Pushed after rebase: {msg}")


def drop_stale_versionless(data_path, name):
    """A retry produces json_foo__v1_0_2.json alongside an older, failed
    json_foo.json. Both would render. Keep the versioned one."""
    m = VERSIONED.match(name)
    if not m:
        return
    stale = data_path / (m.group(1) + ".json")
    if stale.exists():
        stale.unlink()
        log(f"Dropped stale versionless record: {stale.name}")


def process_batch(results_dir, repo):
    json_files = sorted(
        f for f in results_dir.glob("*.json") if f.name not in SKIP_NAMES
    )
    if not json_files:
        return

    data_path = repo / DATA_DIR
    data_path.mkdir(exist_ok=True)

    copied = []

    for f in json_files:
        # Validate before copying: the engine may still be writing this file.
        try:
            rec = json.loads(f.read_text())
        except json.JSONDecodeError:
            log(f"Skipping (bad JSON, will retry): {f.name}")
            continue

        # Shape check: the site drops anything without these, so catch it here
        # where you can still see the log, rather than silently on the website.
        if not isinstance(rec, dict) or not rec.get("package") or "overall_verdict" not in rec:
            log(f"Skipping (not a package record): {f.name}")
            continue

        shutil.copy2(f, data_path / f.name)
        drop_stale_versionless(data_path, f.name)
        copied.append(f)
        log(f"Copied: {f.name}")

    if not copied:
        return

    label = ", ".join(f.name for f in copied[:5])
    if len(copied) > 5:
        label += f" +{len(copied) - 5} more"
    push(repo, f"add {label}")

    # Only delete after a successful push.
    for f in copied:
        f.unlink()
        log(f"Deleted: {f.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=RESULTS_DIR)
    parser.add_argument("--repo", type=Path, default=REPO_DIR)
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL)
    args = parser.parse_args()

    if not args.results.is_dir():
        sys.exit(f"Results directory not found: {args.results}")
    if not (args.repo / ".git").is_dir():
        sys.exit(f"Not a git repo: {args.repo}")

    log(f"Watching: {args.results}")
    log(f"Repo:     {args.repo}")
    log(f"Interval: {args.interval}s")

    while True:
        try:
            process_batch(args.results, args.repo)
        except RuntimeError as e:
            log(f"Error (will retry): {e}")
        except Exception as e:
            log(f"Unexpected error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""push-watcher.py — Watches the results folder for new .json files,
copies them into the repo's data/ folder, pushes to GitHub, and deletes
the source files.

manifest.json / bundle.json are NOT built here. They are derived from
data/ by .github/workflows/pages.yml at deploy time.
"""

import argparse
import json
import re
import shutil
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("/home/feet/Desktop/checker/results")
REPO_DIR = Path("/home/feet/Desktop/www/trail")
POLL_INTERVAL = 15
DATA_DIR = "data"

# Files the engine drops in results/ that are not per-package records.
SKIP_NAMES = {"summary.json"}

# json_<pkg>__v1_0_2.json  ->  json_<pkg>
VERSIONED = re.compile(r"^(json_.+?)__v[\d_].*\.json$")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, timeout=120
    )


def push(repo, msg):
    git(repo, "add", "-A")

    result = git(repo, "commit", "-m", msg)
    if result.returncode != 0:
        if "nothing to commit" in result.stdout:
            return
        log(f"git commit failed: {result.stderr.strip()}")
        return

    if git(repo, "push").returncode == 0:
        log(f"Pushed: {msg}")
        return

    # Non-fast-forward: the remote moved. Rebase onto it and retry once.
    log("push rejected, rebasing onto remote")
    if git(repo, "pull", "--rebase").returncode != 0:
        git(repo, "rebase", "--abort")
        git(repo, "reset", "HEAD~1")
        raise RuntimeError("rebase failed - resolve by hand")

    if git(repo, "push").returncode != 0:
        git(repo, "reset", "HEAD~1")
        raise RuntimeError("push failed after rebase")

    log(f"Pushed after rebase: {msg}")


def drop_stale_versionless(data_path, name):
    """A retry produces json_foo__v1_0_2.json alongside an older, failed
    json_foo.json. Both would render. Keep the versioned one."""
    m = VERSIONED.match(name)
    if not m:
        return
    stale = data_path / (m.group(1) + ".json")
    if stale.exists():
        stale.unlink()
        log(f"Dropped stale versionless record: {stale.name}")


def process_batch(results_dir, repo):
    json_files = sorted(
        f for f in results_dir.glob("*.json") if f.name not in SKIP_NAMES
    )
    if not json_files:
        return

    data_path = repo / DATA_DIR
    data_path.mkdir(exist_ok=True)

    copied = []

    for f in json_files:
        # Validate before copying: the engine may still be writing this file.
        try:
            rec = json.loads(f.read_text())
        except json.JSONDecodeError:
            log(f"Skipping (bad JSON, will retry): {f.name}")
            continue

        # Shape check: the site drops anything without these, so catch it here
        # where you can still see the log, rather than silently on the website.
        if not isinstance(rec, dict) or not rec.get("package") or "overall_verdict" not in rec:
            log(f"Skipping (not a package record): {f.name}")
            continue

        shutil.copy2(f, data_path / f.name)
        drop_stale_versionless(data_path, f.name)
        copied.append(f)
        log(f"Copied: {f.name}")

    if not copied:
        return

    label = ", ".join(f.name for f in copied[:5])
    if len(copied) > 5:
        label += f" +{len(copied) - 5} more"
    push(repo, f"add {label}")

    # Only delete after a successful push.
    for f in copied:
        f.unlink()
        log(f"Deleted: {f.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=RESULTS_DIR)
    parser.add_argument("--repo", type=Path, default=REPO_DIR)
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL)
    args = parser.parse_args()

    if not args.results.is_dir():
        sys.exit(f"Results directory not found: {args.results}")
    if not (args.repo / ".git").is_dir():
        sys.exit(f"Not a git repo: {args.repo}")

    log(f"Watching: {args.results}")
    log(f"Repo:     {args.repo}")
    log(f"Interval: {args.interval}s")

    while True:
        try:
            process_batch(args.results, args.repo)
        except RuntimeError as e:
            log(f"Error (will retry): {e}")
        except Exception as e:
            log(f"Unexpected error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""push-watcher.py — Watches the results folder for new .json files,
copies them into the repo's data/ folder, pushes to GitHub, and deletes
the source files.

manifest.json / bundle.json are NOT built here. They are derived from
data/ by .github/workflows/pages.yml at deploy time.
"""

import argparse
import json
import re
import shutil
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("/home/feet/Desktop/checker/results")
REPO_DIR = Path("/home/feet/Desktop/www/trail")
POLL_INTERVAL = 15
DATA_DIR = "data"

# Files the engine drops in results/ that are not per-package records.
SKIP_NAMES = {"summary.json"}

# json_<pkg>__v1_0_2.json  ->  json_<pkg>
VERSIONED = re.compile(r"^(json_.+?)__v[\d_].*\.json$")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, timeout=120
    )


def push(repo, msg):
    git(repo, "add", "-A")

    result = git(repo, "commit", "-m", msg)
    if result.returncode != 0:
        if "nothing to commit" in result.stdout:
            return
        log(f"git commit failed: {result.stderr.strip()}")
        return

    if git(repo, "push").returncode == 0:
        log(f"Pushed: {msg}")
        return

    # Non-fast-forward: the remote moved. Rebase onto it and retry once.
    log("push rejected, rebasing onto remote")
    if git(repo, "pull", "--rebase").returncode != 0:
        git(repo, "rebase", "--abort")
        git(repo, "reset", "HEAD~1")
        raise RuntimeError("rebase failed - resolve by hand")

    if git(repo, "push").returncode != 0:
        git(repo, "reset", "HEAD~1")
        raise RuntimeError("push failed after rebase")

    log(f"Pushed after rebase: {msg}")


def drop_stale_versionless(data_path, name):
    """A retry produces json_foo__v1_0_2.json alongside an older, failed
    json_foo.json. Both would render. Keep the versioned one."""
    m = VERSIONED.match(name)
    if not m:
        return
    stale = data_path / (m.group(1) + ".json")
    if stale.exists():
        stale.unlink()
        log(f"Dropped stale versionless record: {stale.name}")


def process_batch(results_dir, repo):
    json_files = sorted(
        f for f in results_dir.glob("*.json") if f.name not in SKIP_NAMES
    )
    if not json_files:
        return

    data_path = repo / DATA_DIR
    data_path.mkdir(exist_ok=True)

    copied = []

    for f in json_files:
        # Validate before copying: the engine may still be writing this file.
        try:
            rec = json.loads(f.read_text())
        except json.JSONDecodeError:
            log(f"Skipping (bad JSON, will retry): {f.name}")
            continue

        # Shape check: the site drops anything without these, so catch it here
        # where you can still see the log, rather than silently on the website.
        if not isinstance(rec, dict) or not rec.get("package") or "overall_verdict" not in rec:
            log(f"Skipping (not a package record): {f.name}")
            continue

        shutil.copy2(f, data_path / f.name)
        drop_stale_versionless(data_path, f.name)
        copied.append(f)
        log(f"Copied: {f.name}")

    if not copied:
        return

    label = ", ".join(f.name for f in copied[:5])
    if len(copied) > 5:
        label += f" +{len(copied) - 5} more"
    push(repo, f"add {label}")

    # Only delete after a successful push.
    for f in copied:
        f.unlink()
        log(f"Deleted: {f.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=RESULTS_DIR)
    parser.add_argument("--repo", type=Path, default=REPO_DIR)
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL)
    args = parser.parse_args()

    if not args.results.is_dir():
        sys.exit(f"Results directory not found: {args.results}")
    if not (args.repo / ".git").is_dir():
        sys.exit(f"Not a git repo: {args.repo}")

    log(f"Watching: {args.results}")
    log(f"Repo:     {args.repo}")
    log(f"Interval: {args.interval}s")

    while True:
        try:
            process_batch(args.results, args.repo)
        except RuntimeError as e:
            log(f"Error (will retry): {e}")
        except Exception as e:
            log(f"Unexpected error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
