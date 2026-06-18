#!/usr/bin/env bash

# Automated Infrastructure Security Verification Script
# Run as root: sudo ./validate_infra.sh

set -euo pipefail

echo "=== Starting Infrastructure Verification Scans ==="
FAILED=0

# 1. Verify Firewall is enabled (UFW status)
if command -v ufw &> /dev/null; then
    STATUS=$(ufw status | grep "Status: active" || true)
    if [ -n "$STATUS" ]; then
        echo "[PASS] Firewall is active."
    else
        echo "[FAIL] Firewall (UFW) is not active!"
        FAILED=$((FAILED + 1))
    fi
else
    echo "[FAIL] UFW is not installed!"
    FAILED=$((FAILED + 1))
fi

# 2. Verify SSH Hardening Policies
if [ -f "/etc/ssh/sshd_config" ]; then
    ROOT_LOGIN=$(grep -i "^PermitRootLogin no" /etc/ssh/sshd_config || true)
    PWD_AUTH=$(grep -i "^PasswordAuthentication no" /etc/ssh/sshd_config || true)
    if [ -n "$ROOT_LOGIN" ] && [ -n "$PWD_AUTH" ]; then
        echo "[PASS] SSH parameters (no root login, no passwords) are enforced."
    else
        echo "[FAIL] SSH parameters permit unsafe connections!"
        FAILED=$((FAILED + 1))
    fi
else
    echo "[WARN] No SSH daemon configuration found on path."
fi

# 3. Verify sysctl network filters
SYN_COOKIES=$(sysctl net.ipv4.tcp_syncookies | grep "net.ipv4.tcp_syncookies = 1" || true)
IP_FORWARD=$(sysctl net.ipv4.ip_forward | grep "net.ipv4.ip_forward = 0" || true)
if [ -n "$SYN_COOKIES" ] && [ -n "$IP_FORWARD" ]; then
    echo "[PASS] System network kernel controls (SYN cookies, routing block) are secure."
else
    echo "[FAIL] Vulnerable network kernel values detected!"
    FAILED=$((FAILED + 1))
fi

# 4. Verify Application Container Runtime status
if command -v docker &> /dev/null; then
    CONTAINER_RUNNING=$(docker ps --filter "name=ranga_farm_app" --filter "status=running" -q)
    if [ -n "$CONTAINER_RUNNING" ]; then
        echo "[PASS] Application container ranga_farm_app is running."
    else
        echo "[WARN] Docker is installed, but ranga_farm_app is not currently running."
    fi
else
    echo "[INFO] Docker runtime not detected locally."
fi

echo "=== Scan Complete. Total Failures: $FAILED ==="
exit $FAILED
