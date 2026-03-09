#!/bin/sh
# Nightly Postgres backup — commits to dooslave/doohub-backups repo.

set -eu

DATE=$(date +%Y-%m-%d)
FILENAME="doohub_${DATE}.sql"
REPO_DIR="/repo"
KEEP_DAYS=14

# Ensure tools are installed.
apk add --no-cache git postgresql16-client > /dev/null 2>&1 || true

# Clone or update the backup repo.
if [ ! -d "${REPO_DIR}/.git" ]; then
  git clone "https://x-access-token:${GH_TOKEN}@github.com/dooslave/doohub-backups.git" "${REPO_DIR}"
fi

cd "${REPO_DIR}"
git config user.name "doohub-backup"
git config user.email "backup@doohub.io"
git pull origin main || true

# Dump the database.
pg_dump -h db -U doohub --clean --if-exists doohub > "${REPO_DIR}/${FILENAME}"

# Remove backups older than KEEP_DAYS.
find "${REPO_DIR}" -name "doohub_*.sql" -mtime +${KEEP_DAYS} -delete

# Commit and push.
git add *.sql
git commit -m "Backup ${DATE}" || true
git push origin main
