#!/bin/bash

set -eox pipefail

if [ -v LOCALSTACK_URL ]; then
	echo "Waiting for dependencies"
	python3 wait_for_rabbitmq.py
	python3 wait_for_grpc.py
	echo "Setting up database"
	python3 setup_db.py
fi

echo "Running AMQP server"
python3 amqp_server.py
