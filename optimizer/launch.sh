#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
study="$1"
python_command="${PYTHON:-python3}"
test -f "$study/config.json"
nohup "$python_command" -B -m optimizer run --study "$study" > "$study/controller.out" 2> "$study/controller.err" &
pid=$!
printf '%s\n' "$pid" > "$study/controller.pid"
printf 'Controller PID %s; logs in %s\n' "$pid" "$study"
