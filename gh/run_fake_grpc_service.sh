#!/bin/bash

set -eoxu pipefail

python3 wait_for_secrets.py
python3 fake_grpc_service.py
