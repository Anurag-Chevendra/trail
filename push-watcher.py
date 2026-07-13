#!/usr/bin/env python3
import argparse
import json
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("/home/feet/Desktop/checker/results")
REPO_DIR = Path("/home/feet/Desktop/www/trail")
POLL_INTERVAL = 15
PACKAGES_FILE = "packages.json"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, timeout=60
    )

def load_packages(repo):
    pkg_file = repo / PACKAGES_FILE
    if not pkg_file.exists():
        return []
    try:
        data = json.loads(pkg_file.read_text())
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        return []
    except (json.JSONDecodeError, OSError):
        log(f"WARNING: corrupt {PACKAGES_FILE}, starting fresh")
        return []

def upsert(packages, record):
    key = (record.get("package", ""), record.get("registry_version", ""))
    for i, p in enumerate(packages):
        if (p.get("package", ""), p.get("registry_version", "")) == key:
            packages[i] = record
            return packages
    packages.append(record)
    return packages

def save_packages(repo, packages):
    (repo / PACKAGES_FILE).write_text(json.dumps(packages))

def push(repo, names):
    git(repo, "add", PACKAGES_FILE)
    label = ", ".join(names[:5])
    if len(names) > 5:
        label += f" +{len(names) - 5} more"
    msg = f"add {label}"

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

    packages = load_packages(repo)
    processed = []

    for f in json_files:
        try:
            record = json.loads(f.read_text())
        except json.JSONDecodeError:
            log(f"Skipping (bad JSON, will retry): {f.name}")
            continue

        # Handle both single objects and arrays of objects
        if isinstance(record, list):
            for item in record:
                if isinstance(item, dict):
                    packages = upsert(packages, item)
            processed.append(f)
            log(f"Merged: {f.name} ({len(record)} records)")
        elif isinstance(record, dict):
            packages = upsert(packages, record)
            processed.append(f)
            log(f"Merged: {f.name} ({record.get('package', '?')})")
        else:
            log(f"Skipping (not a dict or list): {f.name}")
            continue

    if not processed:
        return

    save_packages(repo, packages)
    names = [f.name for f in processed]
    push(repo, names)

    for f in processed:
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

    git(args.repo, "pull", "--ff-only")

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
