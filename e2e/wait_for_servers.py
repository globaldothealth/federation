"""
Wait for system component servers to provide healthchecks
"""

import logging
import os
import time

import requests


SIM_A_HEALTHCHECK_ENDPOINT = os.environ.get("SIM_A_HEALTHCHECK_ENDPOINT")
SIM_B_HEALTHCHECK_ENDPOINT = os.environ.get("SIM_B_HEALTHCHECK_ENDPOINT")
SIM_C_HEALTHCHECK_ENDPOINT = os.environ.get("SIM_C_HEALTHCHECK_ENDPOINT")

GH_HEALTH_ENDPOINT = os.environ.get("GH_HEALTH_ENDPOINT")

WAIT_TIME = 2
MAX_ATTEMPTS = 42


def wait_for_server(healthcheck_url: str) -> None:
    """
    Waits for a server to provide healthchecks
    Args:
        healthcheck_url (str): The URL to GET a healthcheck from

    Raises:
        Exception: The server should respond and show good health in the given amount of time
    """
    logging.info(f"Waiting for server at {healthcheck_url}")
    current_attempt = 0
    while current_attempt < MAX_ATTEMPTS:
        try:
            response = requests.get(healthcheck_url)
            if response.status_code == 200:
                logging.info("Server ready")
                return
        except Exception:
            logging.info(f"Server not ready. Retrying in {WAIT_TIME} seconds")
            current_attempt += 1
            time.sleep(WAIT_TIME)
    raise Exception(f"Server not ready in {WAIT_TIME * MAX_ATTEMPTS} seconds")


if __name__ == "__main__":
    wait_for_server(GH_HEALTH_ENDPOINT)
    wait_for_server(SIM_A_HEALTHCHECK_ENDPOINT)
    wait_for_server(SIM_B_HEALTHCHECK_ENDPOINT)
    wait_for_server(SIM_C_HEALTHCHECK_ENDPOINT)
