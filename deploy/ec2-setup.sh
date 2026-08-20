#!/usr/bin/env bash
# One-time bootstrap for a fresh Ubuntu 22.04 EC2 t3.micro (free-tier)
# instance. Run this once via SSH after launching the instance; see
# DEPLOY.md for the full walkthrough (security group, key pair, etc).
#
# Usage (on the instance):
#   curl -fsSL https://raw.githubusercontent.com/<you>/afm-explorer/main/deploy/ec2-setup.sh | bash
# or copy the repo up first and run it locally:
#   bash deploy/ec2-setup.sh

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/<you>/afm-explorer.git}"
APP_DIR="$HOME/afm-explorer"

echo "== Installing Docker Engine + Compose plugin =="
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker "$USER"

echo "== Cloning repo =="
if [ ! -d "$APP_DIR" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "== Starting the stack (production compose) =="
cd "$APP_DIR"
newgrp docker <<EOF
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
EOF

echo "== Done. The app should now be reachable on http://<this-instance-public-ip>/ =="
echo "== Next: set up TLS via Cloudflare Tunnel (see DEPLOY.md) =="
