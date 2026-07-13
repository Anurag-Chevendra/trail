#!/usr/bin/env python3
"""
push-watcher.py — Watches the results folder for new .json files,
copies them into the repo's data/ folder, updates manifest.json,
pushes to GitHub, and deletes the source files.
"""

import argparse
import json
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

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, timeout=60
    )

def build_manifest(repo):
    """Generate manifest.json from all .json files in data/."""
    data_path = repo / DATA_DIR
    if not data_path.exists():
        return []
    files = sorted(f.name for f in data_path.glob("*.json"))
    manifest_path = repo / "manifest.json"
    manifest_path.write_text(json.dumps(files))
    return files

def push(repo, msg):
    git(repo, "add", "-A")

    result = git(repo, "commit", "-m", msg)
    if result.returncode != 0:
        if "nothing to commit" in result.stdout:
            return
        log(f"git commit failed: {result.stderr.strip()}")
        return

    result = git(repo, "push")
    if result.returncode != 0:
        log(f"git push failed: {result.stderr.strip()}")
        git(repo, "reset", "HEAD~1")
        raise RuntimeError("push failed")
    log(f"Pushed: {msg}")

def process_batch(results_dir, repo):
    json_files = sorted(results_dir.glob("*.json"))
    if not json_files:
        return

    data_path = repo / DATA_DIR
    data_path.mkdir(exist_ok=True)

    copied = []

    for f in json_files:
        # Validate it's proper JSON before copying
        try:
            json.loads(f.read_text())
        except json.JSONDecodeError:
            log(f"Skipping (bad JSON, will retry): {f.name}")
            continue

        dest = data_path / f.name
        shutil.copy2(f, dest)
        copied.append(f)
        log(f"Copied: {f.name}")

    if not copied:
        return

    manifest = build_manifest(repo)
    log(f"Manifest: {len(manifest)} files")

    label = ", ".join(f.name for f in copied[:5])
    if len(copied) > 5:
        label += f" +{len(copied) - 5} more"
    push(repo, f"add {label}")

    # Only delete after successful push
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

    git(args.repo, "pull", "--rebase")

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
