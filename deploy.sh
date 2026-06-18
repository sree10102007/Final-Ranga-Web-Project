#!/usr/bin/env bash

# Hardened Production Deployment & Validation Script
# Run as root: sudo ./deploy.sh

set -euo pipefail

echo "=== Starting Hardened Production Deployment ==="

# 1. Run Secrets Leak Scan (Gating build)
if command -v detect-secrets &> /dev/null; then
    echo "Running detect-secrets scan..."
    detect-secrets scan --baseline .secrets.baseline .
    # Fail deployment if new secrets detected
    if ! git diff --exit-code .secrets.baseline &> /dev/null; then
        echo "ERROR: New secrets detected in baseline file! Deployment aborted."
        exit 1
    fi
else
    echo "WARNING: detect-secrets tool is missing. Skipping local check."
fi

# 2. Harden OS and Firewall
echo "Applying firewall rules..."
bash ./setup_firewall.sh

# 3. Secure File Permissions
echo "Securing local filesystem permissions..."
chown -R root:root .
chmod -R 755 .
if [ -d "./goat_farm_app/logs" ]; then
    chmod 770 ./goat_farm_app/logs
fi
if [ -d "./goat_farm_app/static/uploads" ]; then
    chmod 770 ./goat_farm_app/static/uploads
fi

# 4. Container Compilation & Refresh (Using hard resource limits)
if command -v docker-compose &> /dev/null; then
    echo "Compiling and launching containerized services..."
    docker-compose down
    docker-compose up -d --build
elif command -v docker &> /dev/null; then
    echo "Rebuilding Docker services..."
    docker build -t ranga-farm-app .
    docker run -d --name ranga_farm_app --read-only --cap-drop=ALL -m 512M --cpus=0.5 -p 5001:5001 ranga-farm-app
fi

# 5. Run Integrity validation scans
echo "Verifying server configuration integrity..."
bash ./validate_infra.sh

echo "=== Production Deployment Successfully Executed & Hardened! ==="
