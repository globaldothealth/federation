#!/bin/bash

set -eoxu pipefail

echo "Waiting for database"
python3 wait_for_db.py
echo "Setting up database"
prisma generate
prisma db push
echo "Starting outbreak simulator"
python3 sim.py
