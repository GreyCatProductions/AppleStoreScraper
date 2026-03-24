#!/bin/bash
set -e

REPO_URL="https://github.com/GreyCatProductions/AppleStoreScraper"

apt-get update -y
apt-get install -y git python3.12 python3.12-venv

git clone "$REPO_URL" ~/apple_store_client

python3.12 -m venv .venv
.venv/bin/pip install -r client/requirements.txt

cat > /etc/systemd/system/scraper.service <<EOF
[Unit]
Description=Apple Store Scraper
After=network.target

[Service]
WorkingDirectory=/root/apple_store_client
ExecStart=/root/apple_store_client/.venv/bin/python client/src/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scraper
systemctl start scraper