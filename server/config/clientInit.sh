#!/bin/bash
set -e

REPO_URL="https://github.com/GreyCatProductions/AppleStoreScraper"

gcloud compute firewall-rules create allow-8000 --allow tcp:8000 --direction INGRESS --source-ranges 0.0.0.0/0

apt-get update -y
apt-get install -y python3-pip python3-venv git

git clone "$REPO_URL" ~/apple_store_client

cd ~/apple_store_client

python3 -m venv .venv
.venv/bin/pip install -r client/requirements.txt

cat > /etc/systemd/system/scraper.service <<EOF
[Unit]
Description=Apple Store Scraper
After=network.target

[Service]
WorkingDirectory=/root/apple_store_client
Environment=PYTHONPATH=/root/apple_store_client
ExecStart=/root/apple_store_client/.venv/bin/python client/src/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scraper
systemctl start scraper