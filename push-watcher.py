#!/bin/bash
# ─────────────────────────────────────────────────────────────
# push-to-github.sh — Bundles analyzer results into packages.json
# and pushes to your GitHub Pages repo.
#
# Setup:
#   1. Clone your repo:
#      git clone https://<TOKEN>@github.com/<USER>/trail-site.git /home/feet/trail-site
#
#   2. Edit the two paths below.
#
#   3. Add to crontab (e.g. every 10 minutes):
#      crontab -e
#      */10 * * * * /home/feet/trail-site/push-to-github.sh >> /home/feet/trail-site/push.log 2>&1
# ─────────────────────────────────────────────────────────────

# ── CONFIG ───────────────────────────────────────────────────
RESULTS_DIR="/home/feet/Desktop/checker/results"
REPO_DIR="/home/feet/trail-site"
# ─────────────────────────────────────────────────────────────

set -e
cd "$REPO_DIR"

# Combine all .json result files into a single JSON array
# Uses a simple node one-liner (already on Pi if you run the analyzer)
node -e "
  const fs = require('fs');
  const dir = process.argv[1];
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.json'));
  const data = files.map(f => {
    try { return JSON.parse(fs.readFileSync(dir + '/' + f, 'utf8')); }
    catch { return null; }
  }).filter(Boolean);
  fs.writeFileSync('packages.json', JSON.stringify(data));
" "$RESULTS_DIR"

# Only push if something actually changed
if git diff --quiet packages.json 2>/dev/null; then
  echo "[$(date)] No changes to push."
  exit 0
fi

git add packages.json
git commit -m "update packages $(date +%Y-%m-%dT%H:%M:%S)"
git push

echo "[$(date)] Pushed $(wc -c < packages.json) bytes."
