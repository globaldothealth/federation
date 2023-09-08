#!/bin/bash

set -eoxu pipefail

python3 -m grpc_tools.protoc -I ./protobufs --python_out=./gh --grpc_python_out=./gh ./protobufs/cases.proto
python3 -m grpc_tools.protoc -I ./protobufs --python_out=./gh --grpc_python_out=./gh ./protobufs/rt_estimate.proto
python3 -m grpc_tools.protoc -I ./protobufs --python_out=./gh --grpc_python_out=./gh ./protobufs/model_comparison.proto
