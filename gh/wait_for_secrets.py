"""
Wait for secret to exist in AWS Secrets Manager
"""

import logging
from time import sleep

from setup_localstack import wait_for_localstack, SECRETS_CLIENT, PARTNER_A_NAME
from util import setup_logger


WAIT_TIME = 5


def wait_for_secrets() -> None:
    """
    Wait for secret to exist in AWS Secrets Manager

    Returns:
        TYPE: Description

    Raises:
        Exception: The secret should exist in the given amount of time
    """

    logging.info("Checking for secrets in Secrets Manager")
    counter = 0
    while counter < 42:
        response = SECRETS_CLIENT.list_secrets()
        secrets_list = response.get("SecretList", [])
        for secret in secrets_list:
            logging.info(f"Secret: {secret}")
            if secret.get("Name") == PARTNER_A_NAME:
                logging.info("Found secret")
                return
        logging.info(
            f"Did not find secret in attempt {counter}, waiting {WAIT_TIME} seconds"
        )
        counter += 1
        sleep(WAIT_TIME)
    logging.warning("Could not find secrets")
    raise Exception("Secrets not available")


if __name__ == "__main__":
    setup_logger()
    logging.info("Waiting for secrets")
    wait_for_localstack()
    wait_for_secrets()
