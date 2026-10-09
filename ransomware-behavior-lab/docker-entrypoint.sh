#!/bin/sh
# Docker entrypoint — syncs config to the container's LAB_ROOT,
# seeds victim data on first run, then starts the web server.
set -e

LAB_ROOT="${LAB_ROOT:-/data/victim}"
PORT="${PORT:-6767}"

echo "[entrypoint] LAB_ROOT=$LAB_ROOT PORT=$PORT"

# 1. Runtime directories
mkdir -p "$LAB_ROOT" logs reports runs \
    evidence/baseline evidence/post

# 2. Point both config files at the container victim dir
python3 - "$LAB_ROOT" <<'EOF'
import json, sys
from pathlib import Path

lab_root = sys.argv[1]
for name in ("lab_config.json", "simulator/config.json"):
    p = Path("/app") / name
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"[entrypoint] WARNING: {name} not found, skipping")
        continue
    cfg["lab_root"] = lab_root
    if name == "lab_config.json":
        cfg["project_root"] = "/app"
    p.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"[entrypoint] synced {name} -> lab_root={lab_root}")
EOF

# 3. Seed victim files on first run (skip if data already present)
count=$(find "$LAB_ROOT" -maxdepth 3 -type f 2>/dev/null | wc -l)
if [ "$count" -lt 10 ]; then
    echo "[entrypoint] victim dir looks empty ($count files) — generating test data..."
    python3 simulator/generate_test_data.py
else
    echo "[entrypoint] victim dir already has $count files — skipping seed."
fi

# 4. Start the web server (single worker keeps pipeline state consistent)
echo "[entrypoint] starting web UI on 0.0.0.0:$PORT"
exec gunicorn \
    --chdir /app/webui \
    --bind "0.0.0.0:$PORT" \
    --workers 1 \
    --threads 8 \
    --timeout 300 \
    app:app
