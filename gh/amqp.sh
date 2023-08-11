#!/bin/bash

set -eoxu pipefail

echo "Waiting for dependencies"
python3 wait_for_rabbitmq.py
python3 wait_for_grpc.py
echo "Setting up database"
python3 setup_db.py
echo "Running AMQP server"
python3 amqp_server.py
