#!/bin/bash
set -e

REPO_URL="https://github.com/GreyCatProductions/AppleStoreScraper"

apt-get update -y
apt-get install -y python3-pip python3-venv git

git clone "$REPO_URL" ~/apple_scraper_server

cd ~/apple_scraper_server

python3 -m venv .venv
.venv/bin/pip install -r server/requirements.txt
.venv/bin/pip install -r shared/requirements.txt

cat > /etc/systemd/system/scraper.service <<EOF
[Unit]
Description=Apple Store Scraper
After=network.target

[Service]
WorkingDirectory=/root/apple_scraper_server
Environment=PYTHONPATH=/root/apple_scraper_server
ExecStart=/root/apple_scraper_server/.venv/bin/python server/src/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scraper
systemctl start scraper