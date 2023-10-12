"""
Wait for the server to provide healthchecks
"""

import logging
import os
import time

import requests

from util import setup_logger


HEALTHCHECK_ENDPOINT = os.environ.get("HEALTHCHECK_ENDPOINT")

WAIT_TIME = 2
MAX_ATTEMPTS = 42


def wait_for_flask() -> None:
    """
    Waits for the server to provide healthchecks

    Raises:
        Exception: The server should respond and show good health in the given amount of time
    """

    logging.info("Waiting for Flask")
    current_attempt = 0
    while current_attempt < MAX_ATTEMPTS:
        try:
            response = requests.get(HEALTHCHECK_ENDPOINT)
            if response.status_code == 200:
                logging.info("Flask ready")
                return
        except Exception:
            logging.info(f"Flask not ready. Retrying in {WAIT_TIME} seconds")
            current_attempt += 1
            time.sleep(WAIT_TIME)
    raise Exception(f"Flask not ready in {WAIT_TIME * MAX_ATTEMPTS} seconds")


if __name__ == "__main__":
    setup_logger()
    wait_for_flask()
