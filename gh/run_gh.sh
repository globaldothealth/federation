#!/bin/bash

set -eou pipefail

ARCH=$(uname -m)

if [ $ARCH == "x86" ]; then
	echo "Running x86 stack"
	docker-compose -f ./docker-compose.yml --compatibility --verbose up --build --force-recreate --remove-orphans --renew-anon-volumes -d
elif [ $ARCH == "arm64" ]; then
	echo "Running arm64 stack"
	docker-compose -f ./docker-compose-arm.yml --compatibility --verbose up --build --force-recreate --remove-orphans --renew-anon-volumes -d
else
	echo "System not set up for architecture ${ARCH}"
fi
