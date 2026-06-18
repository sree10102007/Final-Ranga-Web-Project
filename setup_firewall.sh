#!/usr/bin/env bash

# Linux Host Firewall Hardening Script (using UFW)
# Run as root: sudo ./setup_firewall.sh

set -euo pipefail

echo "=== Initializing Host Firewall Configuration ==="

# 1. Install UFW if missing
if ! command -v ufw &> /dev/null; then
    echo "Installing UFW..."
    apt-get update && apt-get install -y ufw
fi

# 2. Reset firewall rules to default
ufw --force reset

# 3. Set Default Policies (Deny incoming, Allow outgoing)
ufw default deny incoming
ufw default allow outgoing

# 4. Define Rules
# Allow SSH access
ufw allow 22/tcp comment 'Hardened SSH Port'

# Allow Web traffic
ufw allow 80/tcp comment 'HTTP traffic'
ufw allow 443/tcp comment 'HTTPS traffic'

# Restrict Flask port (5001) to loopback only (access via reverse proxy / docker only)
ufw allow in on lo to any port 5001 proto tcp comment 'Internal Flask'
ufw deny 5001/tcp comment 'Block External access to Flask'

# 5. Enable Firewall
ufw --force enable

# Show status
ufw status verbose

echo "=== Firewall Hardening Successfully Configured! ==="
