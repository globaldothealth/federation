"""
Partner database setup script for local development and testing
"""

import logging

import psycopg

from constants import DB_CONNECTION, TABLE_NAME


def setup_database() -> None:
    """
    Setup the database
    """

    logging.info(f"Creating table {TABLE_NAME}")
    with psycopg.connect(DB_CONNECTION) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{TABLE_NAME}" (
                    id serial PRIMARY KEY,
                    location_information text,
                    outcome text,
                    date_confirmation text,
                    hospitalized text,
                    pathogen text
                    )
                """
            )
            conn.commit()


if __name__ == "__main__":
    logging.info("Setting up database")
    setup_database()
    logging.info("Done setting up database")
