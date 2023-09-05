#!/bin/bash

set -eoxu pipefail

echo "Standing up compose stack"
docker-compose -f ./docker-compose.yml --compatibility --verbose up --build --force-recreate --remove-orphans --renew-anon-volumes -d

echo "Setting up ECR repository"
python3 setup_ecr_repo.py

echo "Running fake partner container"
docker run -d --name=fake_partner_container --env-file ./.env --network remote_dependency_management_default -p 127.0.0.1:5000:5000 --label version=0.1.0 fake_partner_image

echo "Running daemon in background"
python3 daemon.py 2>&1 &

echo "Running tests"
python3 -m pytest -vv .
