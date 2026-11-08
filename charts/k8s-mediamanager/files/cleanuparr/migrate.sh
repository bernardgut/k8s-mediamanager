#!/bin/bash
# Migrates Cleanuparr's databases with the app's own EF migrations, then exits before the host
# starts, so the settings step sees the image's schema. See README "Cleanuparr settings as code".
set -uo pipefail
umask 022
cd /app || exit 3
python3 -I -B /cleanuparr-config/apply_config.py preflight --config-dir /config --app /app/Cleanuparr || exit $?
log=/tmp/cleanuparr-migrate.log
# WARNING: the dot makes BASE_PATH invalid, so Program.cs returns right after migrating, before RunAsync.
# The time bound only stops a hung start: a migration killed mid-way leaves a lock row behind.
BASE_PATH=/migrate.only timeout -k 30 600 /app/Cleanuparr >"$log" 2>&1
rc=$?
sed 's/^/cleanuparr-migrate: /' "$log"
# A failed migration crashes the app, the early return exits 0; the settings step then checks the
# migration history. The error line is not required: a stored log level of fatal suppresses it.
if [ "$rc" -ne 0 ]; then
  echo "cleanuparr-migrate: the migrate-only run failed (rc=$rc); refusing to continue" >&2
  exit 3
fi
if grep -q 'Invalid BASE_PATH configuration' "$log"; then
  echo "cleanuparr-migrate: the Invalid BASE_PATH error above is the expected migrate-only exit"
fi
