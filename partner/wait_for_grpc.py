"""
Wait for the gRPC server to accept connections
"""

import logging
from time import sleep

from constants import PATHOGEN_A
from test_data_server import TEST_CASE, insert_case, get_cases, reset_database


WAIT_TIME = 2
MAX_ATTEMPTS = 42


def wait_for_grpc() -> None:
    """
    Waits for the gRPC server to accept connections

    Raises:
        Exception: The server should accept connections in the given amount of time
    """

    for _ in range(MAX_ATTEMPTS):
        try:
            _ = get_cases(PATHOGEN_A)
            return
        except Exception:
            logging.exception(
                f"Could not get cases from partner, retrying in {WAIT_TIME} seconds"
            )
            sleep(WAIT_TIME)
    raise Exception(f"gRPC not ready in {WAIT_TIME * MAX_ATTEMPTS} seconds")


if __name__ == "__main__":
    logging.info("Putting a fake case in the database")
    insert_case(PATHOGEN_A, TEST_CASE)
    logging.info("Waiting for gRPC")
    wait_for_grpc()
    logging.info("gRPC server up")
    logging.info("Clearing the database table")
    reset_database()
