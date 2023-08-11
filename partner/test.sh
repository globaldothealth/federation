#!/bin/bash

set -eoxu pipefail

echo "Waiting for server"
python3 wait_for_grpc.py
echo "Running tests"
python3 -m pytest -vv .
