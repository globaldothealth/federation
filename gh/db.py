"""
Functions for interacting with database
"""

import logging

from pymongo import MongoClient

from constants import DB_CONNECTION, DATABASE_NAME, USERS_COLLECTION


def get_curation_data(partner_name: str) -> dict:
    """
    Get curation data for a given partner

    Args:
        partner_name (str): The partner name

    Returns:
        dict: A partner's curation data
    """
    client = MongoClient(DB_CONNECTION)
    db = client[DATABASE_NAME]
    collection = db[USERS_COLLECTION]
    data = list(collection.find({"name": partner_name}))
    logging.debug(f"Got data from db: {data}")
    return data[0]


def get_gh_db_data(collection_name: str) -> list[dict]:
    """
    Get data from a collection in the database

    Args:
        collection_name (str): The collection name

    Returns:
        list[dict]: Requested data from the collection
    """
    client = MongoClient(DB_CONNECTION)
    db = client[DATABASE_NAME]
    collection = db[collection_name]
    data = list(collection.find())
    logging.debug(f"Got data from db collection {collection_name}: {data}")
    return data


def store_data_in_db(data: list, collection_name: str) -> None:
    """
    Store data in a collection in the database

    Args:
        data (list): Description
        collection_name (str): The collection name
    """
    logging.info("Storing data in DB")
    try:
        client = MongoClient(DB_CONNECTION)
        db = client[DATABASE_NAME]
        collection = db[collection_name]
        for elem in data:
            collection.insert_one(elem)
    except Exception:
        logging.exception("An error occurred while trying to store data in DB")
        raise
    logging.info("Stored data in DB")
