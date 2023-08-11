#!/bin/bash

set -eoxu pipefail

python3 wait_for_db.py
prisma generate
prisma db push
python3 -m pytest -vv .
