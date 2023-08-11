#!/bin/bash

set -eoxu pipefail

echo "Waiting for RabbitMQ"
python3 wait_for_rabbitmq.py
echo "Starting client"
python3 data_server.py
