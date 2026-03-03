#!/bin/bash
set -e

# Set up SSH access to host (restricted doohub-ops user)
SSH_DIR="/home/claude/.ssh"
mkdir -p "$SSH_DIR"
cp "$SSH_DIR/doohub-ops-key" "$SSH_DIR/host-key"
chmod 600 "$SSH_DIR/host-key"
cat > "$SSH_DIR/config" << 'SSHEOF'
Host host
    HostName 172.17.0.1
    User doohub-ops
    IdentityFile ~/.ssh/host-key
    StrictHostKeyChecking no
SSHEOF
chmod 700 "$SSH_DIR"
chmod 600 "$SSH_DIR/config"
chown claude:claude "$SSH_DIR" "$SSH_DIR/host-key" "$SSH_DIR/config"

exec su claude -s /bin/bash -c "cd /app && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
