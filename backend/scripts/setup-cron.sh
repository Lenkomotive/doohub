#!/bin/bash
# Sets up the nightly cron job inside the backup container.
# Runs at 3 AM UTC daily.

echo "0 3 * * * /backup.sh >> /var/log/backup.log 2>&1" | crontab -
crond -f -d 8
