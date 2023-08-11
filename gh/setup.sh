#!/bin/bash

set -eoxu pipefail

echo "Waiting for dependencies"
python3 wait_for_rabbitmq.py
echo "Setting up localstack"
python3 setup_localstack.py
echo "Setting up database"
python3 setup_db.py
echo "Setup completed"
