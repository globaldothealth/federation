"""
Global.health database setup script for local development and testing
"""

import logging
import os
import sys
from time import sleep

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from constants import (
    PARTNER_A_NAME,
    PARTNER_B_NAME,
    PARTNER_C_NAME,
    GH_A_COLLECTION,
    USERS_COLLECTION,
)


DB_CONNECTION = os.environ.get("DB_CONNECTION")
DATABASE_NAME = os.environ.get("DB_NAME")

MAX_ATTEMPTS = 42
WAIT_TIME = 5

PARTNER_NAMES = [PARTNER_A_NAME, PARTNER_B_NAME, PARTNER_C_NAME]


USERS = [
    {"name": name, "email": "partner_email@legit.org", "roles": ["junior curator"]}
    for name in PARTNER_NAMES
]


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
    Wait for database to be ready

    Raises:
        Exception: If database is not available in the expected time
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


def create_database() -> None:
    """
    Create the database
    """

    logging.info(f"Creating {DATABASE_NAME} database, or confirming it exists")
    client = MongoClient(DB_CONNECTION)
    database = client[DATABASE_NAME]
    logging.info("Creating pathogen cases collection")
    _ = database[GH_A_COLLECTION]
    logging.info("Creating users collection")
    _ = database[USERS_COLLECTION]
    logging.info("Created database and collections")


def create_users(users: list[dict]) -> None:
    """
    Create a document for each user

    Args:
        users (list[dict]): Users to create
    """
    logging.info(f"Creating users in collection {USERS_COLLECTION}")
    client = MongoClient(DB_CONNECTION)
    database = client[DATABASE_NAME]
    collection = database[USERS_COLLECTION]
    for user in users:
        logging.info(f"Creating user {user}")
        collection.insert_one(user)
    logging.info("Done creating users")


if __name__ == "__main__":
    setup_logger()
    logging.info("Starting local/testing setup script")
    wait_for_database()
    create_database()
    create_users(USERS)
    logging.info("Done")
