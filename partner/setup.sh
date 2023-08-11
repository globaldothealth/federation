#!/bin/bash

set -eoxu pipefail

echo "Setting up Localstack"
python3 setup_localstack.py
echo "Setting up database"
python3 setup_db.py