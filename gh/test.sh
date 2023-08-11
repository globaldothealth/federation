#!/bin/bash

set -eoxu pipefail

echo "Waiting for RabbitMQ"
python3 wait_for_rabbitmq.py
echo "Setting up dependencies"
python3 setup_localstack.py
python3 setup_db.py
python3 wait_for_flask.py
python3 -m pytest -vv .
