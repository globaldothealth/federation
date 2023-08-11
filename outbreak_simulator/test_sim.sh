#!/bin/bash

set -eoux pipefail

docker-compose -f ./docker-compose-test.yml up --build --force-recreate --remove-orphans --renew-anon-volumes --exit-code-from test

