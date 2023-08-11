# Demo scripts

This folder contains ways to show off system functionality and/or smoke test different system behaviors.
They assume a running `e2e` stack, and do the following:

- `create_cases.py` sends a request to an outbreak simulator to populate a partner database with cases
- `request_cases.py` sends a request to the G.h service to retrieve cases from a partner service
- `request_estimates.py` sends a request to the G.h service to retrieve R(t) estimates from a partner service
- `approve_cases.py` updates the G.h database cases, simulating a manual approval process
- `approve_estimates.py` updates the G.h database estimates, simulating a manual approval process
- `get_cases.py` sends a request to the G.h service for case data (populated by `request_cases.py`)
- `get_estimates.py` sends a request to the G.h service for R(t) estimate data (populated by `request_estimates.py`)
