"""
Outbreak simulator test suite
"""

import os

import psycopg
from psycopg.rows import dict_row
import pytest

from sim import Case, save_cases, PATHOGEN


DB_CONNECTION = os.environ.get("DATABASE_URL")
TABLE_NAME = "OutbreakCase"


def test_sim_creates_input_cases():
    """
    The sim should create cases with given data
    """

    location = "USA"
    outcome = "A-OK"
    date_confirmation = "03-27-1985"
    hospitalized = "Y"
    expected = {
        "location_information": location,
        "outcome": outcome,
        "date_confirmation": date_confirmation,
        "hospitalized": hospitalized,
    }
    case = Case(PATHOGEN, expected)

    assert case.location_information == location
    assert case.outcome == outcome
    assert case.date_confirmation == date_confirmation
    assert case.hospitalized == hospitalized


def test_sim_creates_random_cases():
    """
    The sim should create cases using fallback data (e.g. chosen by random.choice)
    """

    case = Case(PATHOGEN)

    assert case.location_information
    assert case.outcome
    assert case.date_confirmation
    assert case.hospitalized


def test_sim_saves_cases():
    """
    The sim should save cases to the partner database
    """

    case = Case(PATHOGEN)

    location = case.location_information
    outcome = case.outcome
    date_confirmation = case.date_confirmation
    hospitalized = case.hospitalized
    expected = {
        "location_information": location,
        "outcome": outcome,
        "date_confirmation": date_confirmation,
        "hospitalized": hospitalized,
    }

    save_cases([case])

    actual = {}
    try:
        with psycopg.connect(DB_CONNECTION, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(f'SELECT * FROM "{TABLE_NAME}"')
                results = cur.fetchall()
                actual = results[0]
    except Exception:
        pytest.fail("Could not get cases from database")

    del actual["id"]
    for k, v in expected.items():
        assert v == actual[k]
