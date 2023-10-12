"""
Wait for the database to accept connections
"""

import logging
import os
import sys
from time import sleep

from pymongo import MongoClient
from pymongo.errors import PyMongoError


DB_CONNECTION = os.environ.get("DB_CONNECTION")

MAX_ATTEMPTS = 42
WAIT_TIME = 5


def setup_logger() -> None:
    """
    Set up the logger to stream at the desired level
    """

    h = logging.StreamHandler(sys.stdout)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(h)
    rootLogger.setLevel(logging.DEBUG)


def wait_for_database() -> None:
    """
    Wait for the database to accept connections

    Raises:
        Exception: The database should accept connections in the given amount of time
    """

    logging.info("Waiting for database")
    counter = 0
    while counter < MAX_ATTEMPTS:
        try:
            client = MongoClient(DB_CONNECTION)
            logging.info(f"Connected with access to: {client.list_database_names()}")
            return
        except PyMongoError:
            logging.info(
                f"Database service not ready yet, retrying in {WAIT_TIME} seconds"
            )
            pass
        counter += 1
        sleep(WAIT_TIME)
    raise Exception("Database service not available")


if __name__ == "__main__":
    setup_logger()
    wait_for_database()
