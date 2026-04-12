#!/bin/bash
set -e

REPO_URL="https://github.com/GreyCatProductions/AppleStoreScraper"

apt-get update -y
apt-get install -y python3-pip python3-venv git ca-certificates
update-ca-certificates

if [ -d ~/apple_store_client ]; then
  git -C ~/apple_store_client pull
else
  git clone "$REPO_URL" ~/apple_store_client
fi

curl -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/GOOGLE_CREDENTIALS" \
  > ~/apple_store_client/googleCredentials.json

cd ~/apple_store_client

python3 -m venv .venv
.venv/bin/pip install -r client/requirements.txt
.venv/bin/pip install -r shared/requirements.txt

cat > /etc/systemd/system/scraper.service <<EOF
[Unit]
Description=Apple Store Scraper
After=network.target

[Service]
WorkingDirectory=/root/apple_store_client
Environment=PYTHONPATH=/root/apple_store_client
Environment=SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
Environment=REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ExecStart=/root/apple_store_client/.venv/bin/python client/src/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scraper
systemctl restart scraper