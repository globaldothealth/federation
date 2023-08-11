#!/bin/bash

set -eoxu pipefail

echo "Waiting for RabbitMQ"
python3 wait_for_rabbitmq.py
echo "Waiting for MongoDB"
python3 wait_for_db.py
echo "Setting up localstack"
python3 setup_localstack.py
echo "Waiting for G.h and outbreak simulator"
python3 wait_for_servers.py
echo "Running tests"
python3 -m pytest -vv .
