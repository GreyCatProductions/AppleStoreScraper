#!/bin/bash
set -e

REPO_URL="https://github.com/GreyCatProductions/Hello_World_Remote_Test"

apt-get update -y
apt-get install -y git python3.12 python3.12-venv

git clone "$REPO_URL" ~/apple_store_client

cd ~/apple_store_client
bash setup.sh
