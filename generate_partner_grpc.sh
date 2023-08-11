#!/bin/bash

set -eoxu pipefail

python3 -m grpc_tools.protoc -I ./protobufs --python_out=./partner --grpc_python_out=./partner ./protobufs/cases.proto
python3 -m grpc_tools.protoc -I ./protobufs --python_out=./partner --grpc_python_out=./partner ./protobufs/rt_estimate.proto
