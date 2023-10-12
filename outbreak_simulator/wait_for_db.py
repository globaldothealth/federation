"""
Wait for the database to accept connections
"""

import logging
import os
import sys
from time import sleep

import psycopg


DB_CONNECTION = os.environ.get("DATABASE_URL")

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

    counter = 0
    while counter < MAX_ATTEMPTS:
        try:
            with psycopg.connect(DB_CONNECTION) as conn:
                with conn.cursor() as cur:
                    cur.execute("""SELECT table_name FROM information_schema.tables""")
            return
        except psycopg.Error as exc:
            logging.info(
                f"Database service not ready yet, error: {exc}, retrying in {WAIT_TIME} seconds"
            )
            pass
        counter += 1
        sleep(WAIT_TIME)
    raise Exception("Database service not available")


if __name__ == "__main__":
    setup_logger()
    logging.info("Waiting for database")
    wait_for_database()
    logging.info("Database ready")
