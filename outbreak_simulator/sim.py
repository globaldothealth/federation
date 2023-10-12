"""
Outbreak simulator
"""

import logging
import os
import random

from faker import Faker
from flask import Flask, request
from prisma import Prisma


PATHOGEN = os.environ.get("PATHOGEN")

CASE_STATUSES = ["confirmed", "probable", "suspected" "discarded", "omit_error"]
PATHOGEN_STATUSES = ["endemic", "emerging", "unknown"]
SEXES_AT_BIRTH = ["male", "female", "other", "unknown"]
GENDERS = ["man", "woman", "transgender", "non-binary", "other", "unknown"]
RACES = [
    "Native Hawaiian or Other Pacific Islander",
    "Asian",
    "American Indian or Alaska Native",
    "Black or African American",
    "White",
    "Other",
]
ETHNICITIES = ["Hispanic or Latino", "Not Hispanic or Latino", "other"]
Y_N_NA = ["Y", "N", "NA"]
REASONS_FOR_HOSPITALIZATION = ["monitoring", "treatment", "unknown"]
OUTCOMES = ["recovered", "death", "ongoing post-acute condition"]
CONTACT_SETTINGS = [
    "HOUSE",
    "WORK",
    "SCHOOL",
    "HEALTH",
    "PARTY",
    "BAR",
    "LARGE",
    "LARGECONTACT",
    "OTHER",
    "UNK",
]
CONTACT_ANIMALS = ["PET", "PETRODENTS", "WILD", "WILDRODENTS", "OTHER"]
TRANSMISSIONS = [
    "ANIMAL",
    "HAI",
    "LAB",
    "MTCT",
    "OTHER",
    "FOMITE",
    "PTP",
    "SEX",
    "TRANSFU",
    "UNK",
]

SIM_PORT = os.environ.get("SIM_PORT")

FAKE = Faker()

FLASK = Flask(__name__)


class Case:

    """
    Pathogen case data
    """

    def __init__(self, pathogen: str, request={}) -> None:
        """
        Constructor for pathogen case data

        Args:
            pathogen (str): The name of the pathogen
            request (dict, optional): The request sent to create the case
        """
        self.pathogen = pathogen
        self.case_status = request.get("case_status", random.choice(CASE_STATUSES))
        self.pathogen_status = request.get(
            "pathogen_status", random.choice(PATHOGEN_STATUSES)
        )
        self.location_information = request.get("location_information", FAKE.country())
        self.age = request.get("age")
        self.sex_at_birth = request.get("sex_at_birth", random.choice(SEXES_AT_BIRTH))
        self.sex_at_birth_other = request.get("sex_at_birth_other")
        self.gender = request.get("gender", random.choice(GENDERS))
        self.gender_other = request.get("gender_other")
        self.race = request.get("race", random.choice(RACES))
        self.race_other = request.get("race_other")
        self.ethnicity = request.get("ethnicity", random.choice(ETHNICITIES))
        self.ethnicity_other = request.get("ethnicity_other")
        self.nationality = request.get("nationality")
        self.nationality_other = request.get("nationality_other")
        self.occupation = request.get("occupation")
        self.healthcare_worker = request.get("healthcare_worker", random.choice(Y_N_NA))

        self.previous_infection = request.get(
            "previous_infection", random.choice(Y_N_NA)
        )
        self.co_infection = request.get("co_infection")
        self.pre_existing_condition = request.get("pre_existing_condition")
        self.pregnancy_status = request.get("pregnancy_status", random.choice(Y_N_NA))
        self.vaccination = request.get("vaccination", random.choice(Y_N_NA))
        self.vaccine_name = request.get("vaccine_name")
        self.vaccination_date = request.get(
            "vaccination_date", FAKE.date(pattern="%m-%d-%Y")
        )
        self.vaccine_side_effects = request.get("vaccine_side_effects")

        self.symptoms = request.get("symptoms")
        self.date_onset = request.get("date_onset", FAKE.date(pattern="%m-%d-%Y"))
        self.date_confirmation = request.get(
            "date_confirmation", FAKE.date(pattern="%m-%d-%Y")
        )
        self.confirmation_method = request.get("confirmation_method")
        self.date_of_first = request.get("date_of_first", FAKE.date(pattern="%m-%d-%Y"))
        self.hospitalized = request.get("hospitalized", random.choice(Y_N_NA))
        self.reason_for_hospitalization = request.get(
            "reason_for_hospitalization", random.choice(REASONS_FOR_HOSPITALIZATION)
        )
        self.date_hospitalization = request.get(
            "date_hospitalization", FAKE.date(pattern="%m-%d-%Y")
        )
        self.date_discharge_hospital = request.get(
            "date_discharge_hospital", FAKE.date(pattern="%m-%d-%Y")
        )
        self.intensive_care = request.get("intensive_care", random.choice(Y_N_NA))
        self.date_admission_icu = request.get(
            "date_admission_icu", FAKE.date(pattern="%m-%d-%Y")
        )
        self.date_discharge_icu = request.get(
            "date_discharge_icu", FAKE.date(pattern="%m-%d-%Y")
        )
        self.home_monitoring = request.get("home_monitoring", random.choice(Y_N_NA))
        self.isolated = request.get("isolated", random.choice(Y_N_NA))
        self.date_isolation = request.get("date_isolation")
        self.outcome = request.get("outcome", random.choice(OUTCOMES))
        self.date_death = request.get("date_death", FAKE.date(pattern="%m-%d-%Y"))
        self.date_recovered = request.get(
            "date_recovered", FAKE.date(pattern="%m-%d-%Y")
        )

        self.contact_with_case = request.get("contact_with_case", random.choice(Y_N_NA))
        self.contact_id = request.get("contact_id")
        self.contact_setting = request.get(
            "contact_setting", random.choice(CONTACT_SETTINGS)
        )
        self.contact_setting_other = request.get("contact_setting_other")
        self.contact_animal = request.get(
            "contact_animal", random.choice(CONTACT_ANIMALS)
        )
        self.contact_comment = request.get("contact_comment")
        self.transmission = request.get("transmission", random.choice(TRANSMISSIONS))
        self.travel_history = request.get("travel_history", random.choice(Y_N_NA))
        self.travel_history_entry = request.get("travel_history_entry")
        self.travel_history_start = request.get("travel_history_start")
        self.travel_history_location = request.get("travel_history_location")

        self.genomics_metadata = request.get("genomics_metadata")
        self.accession_number = request.get("accession_number")

        self.source = request.get("source")
        self.source_ii = request.get("source_ii")
        self.source_iii = request.get("source_iii")
        self.source_iv = request.get("source_iv")
        self.date_entry = request.get("date_entry", FAKE.date(pattern="%m-%d-%Y"))
        self.date_last_modified = request.get(
            "date_last_modified", FAKE.date(pattern="%m-%d-%Y")
        )


def save_cases(cases: list) -> None:
    """
    Save cases to the partner database

    Args:
        cases (list): Case data
    """
    data = []

    for case in cases:
        data.append(
            {
                "pathogen": case.pathogen,
                "case_status": case.case_status,
                "pathogen_status": case.pathogen_status,
                "location_information": case.location_information,
                "age": case.age,
                "sex_at_birth": case.sex_at_birth,
                "sex_at_birth_other": case.sex_at_birth_other,
                "gender": case.gender,
                "gender_other": case.gender_other,
                "race": case.race,
                "race_other": case.race_other,
                "ethnicity": case.ethnicity,
                "ethnicity_other": case.ethnicity_other,
                "nationality": case.nationality,
                "nationality_other": case.nationality_other,
                "occupation": case.occupation,
                "healthcare_worker": case.healthcare_worker,
                "previous_infection": case.previous_infection,
                "co_infection": case.co_infection,
                "pre_existing_condition": case.pre_existing_condition,
                "pregnancy_status": case.pregnancy_status,
                "vaccination": case.vaccination,
                "vaccine_name": case.vaccine_name,
                "vaccination_date": case.vaccination_date,
                "vaccine_side_effects": case.vaccine_side_effects,
                "symptoms": case.symptoms,
                "date_onset": case.date_onset,
                "date_confirmation": case.date_confirmation,
                "confirmation_method": case.confirmation_method,
                "date_of_first_consultation": case.date_of_first,
                "hospitalized": case.hospitalized,
                "reason_for_hospitalization": case.reason_for_hospitalization,
                "date_hospitalization": case.date_hospitalization,
                "date_discharge_hospital": case.date_discharge_hospital,
                "intensive_care": case.intensive_care,
                "date_admission_icu": case.date_admission_icu,
                "date_discharge_icu": case.date_discharge_icu,
                "home_monitoring": case.home_monitoring,
                "isolated": case.isolated,
                "date_isolation": case.date_isolation,
                "outcome": case.outcome,
                "date_death": case.date_death,
                "date_recovered": case.date_recovered,
                "contact_with_case": case.contact_with_case,
                "contact_id": case.contact_id,
                "contact_setting": case.contact_setting,
                "contact_setting_other": case.contact_setting_other,
                "contact_animal": case.contact_animal,
                "contact_comment": case.contact_comment,
                "transmission": case.transmission,
                "travel_history": case.travel_history,
                "travel_history_entry": case.travel_history_entry,
                "travel_history_start": case.travel_history_start,
                "travel_history_location": case.travel_history_location,
                "genomics_metadata": case.genomics_metadata,
                "accession_number": case.accession_number,
                "source": case.source,
                "source_ii": case.source_ii,
                "source_iii": case.source_iii,
                "source_iv": case.source_iv,
                "date_entry": case.date_entry,
                "date_last_modified": case.date_last_modified,
            }
        )

    try:
        db = Prisma()
        db.connect()
        db.outbreakcase.create_many(data=data)
    except Exception:
        logging.exception("Could not add cases to database")
        raise
    finally:
        db.disconnect()


@FLASK.route("/cases", methods=["POST"])
def create_and_save_cases() -> tuple[str, int]:
    """
    Create cases and save them to the partner database

    Returns:
        tuple: Message + HTTP status code
    """
    cases = []
    for requested_case in request.json:
        case = Case(PATHOGEN, requested_case)
        cases.append(case)
    save_cases(cases)
    return "OK", 201


@FLASK.route("/health")
def healthcheck() -> tuple[str, int]:
    """
    Healthcheck endpoint for the service

    Returns:
        tuple: "OK" + 200 HTTP status code
    """
    return "OK", 200


if __name__ == "__main__":
    FLASK.run(host="0.0.0.0", port=SIM_PORT, debug=True)
