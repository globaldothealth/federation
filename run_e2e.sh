#!/bin/bash

set -eou pipefail

function cleanup() {
  sed -i "" -e "s#linux/amd64#UNKNOWN_PLATFORM#g" .env
  sed -i "" -e "s#linux/arm64/v8#UNKNOWN_PLATFORM#g" .env
}

trap cleanup EXIT

ARCH=$(uname -m)

# Note: Mac OS sed different from Linux sed
if [ $ARCH == "x86" ]; then
	echo "Running x86 stack"
	sed -i "" -e "s#UNKNOWN_PLATFORM#linux/amd64#g" .env
elif [ $ARCH == "arm64" ]; then
	echo "Running arm64 stack"
	sed -i "" -e "s#UNKNOWN_PLATFORM#linux/arm64/v8#g" .env
else
	echo "System not set up for architecture ${ARCH}"
	exit 1
fi

docker-compose -f ./docker-compose-e2e.yml --compatibility --verbose up --build --force-recreate --remove-orphans --renew-anon-volumes
