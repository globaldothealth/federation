"""
Wait for the gRPC server to accept connections
"""

import logging
from time import sleep

from aws import get_jwt, get_certificate
from constants import PATHOGEN_A, PartnerA
from grpc_client import get_credentials, get_partner_cases
from util import setup_logger


WAIT_TIME = 2
MAX_ATTEMPTS = 42


def wait_for_grpc() -> None:
    """
    Waits for the gRPC server to accept connections

    Raises:
        Exception: The server should accept connections in the given amount of time
    """

    logging.info("Waiting for gRPC")
    for _ in range(MAX_ATTEMPTS):
        try:
            token = get_jwt()
            certificate = get_certificate(PartnerA.domain_name)
            credentials = get_credentials(token, certificate)
            _ = get_partner_cases(PATHOGEN_A, PartnerA, credentials)
            logging.info("gRPC ready")
            return
        except Exception:
            logging.exception("Could not get cases from partner, retrying")
            sleep(WAIT_TIME)
    raise Exception(f"gRPC not ready in {WAIT_TIME * MAX_ATTEMPTS} seconds")


if __name__ == "__main__":
    setup_logger()
    wait_for_grpc()
