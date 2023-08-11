import os

from cases_pb2 import Case


AMQP_HOST = os.environ.get("AMQP_HOST")

PATHOGEN_A = os.environ.get("PATHOGEN_A")
PATHOGEN_B = os.environ.get("PATHOGEN_B")
PATHOGEN_C = os.environ.get("PATHOGEN_C")

PATHOGENS = [PATHOGEN_A, PATHOGEN_B, PATHOGEN_C]

PARTNER_NAME = os.environ.get("PARTNER_NAME")

TOPIC_A_EXCHANGE = f"{PATHOGEN_A}_topic_exchange"
TOPIC_A_QUEUE = f"{PATHOGEN_A}_topic_queue"
TOPIC_A_ROUTE = f"{PATHOGEN_A}_topic_route"

TOPIC_B_EXCHANGE = f"{PATHOGEN_B}_topic_exchange"
TOPIC_B_QUEUE = f"{PATHOGEN_B}_topic_queue"
TOPIC_B_ROUTE = f"{PATHOGEN_B}_topic_route"

PATHOGEN_EXCHANGES = {
    PATHOGEN_A: TOPIC_A_EXCHANGE,
    PATHOGEN_B: TOPIC_B_EXCHANGE
}

PATHOGEN_QUEUES = {
    PATHOGEN_A: TOPIC_A_QUEUE,
    PATHOGEN_B: TOPIC_B_QUEUE
}

PATHOGEN_ROUTES = {
    PATHOGEN_A: TOPIC_A_ROUTE,
    PATHOGEN_B: TOPIC_B_ROUTE
}

DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

TABLE_NAME = os.environ.get("DB_TABLE_NAME")

DB_CONNECTION = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION")

USER_NAME = os.environ.get("COGNITO_USER_NAME")
USER_PASSWORD = os.environ.get("COGNITO_USER_PASSWORD")

# TODO: Remove certs
JWKS_HOST = os.environ.get("LOCALSTACK_URL")
JWKS_FILE = os.environ.get("JWKS_FILE")

# Data validation fields
CASE_FIELDS = Case.DESCRIPTOR.fields_by_name.keys()

# This is brittle but not sure of a better way without TLS and enums
# Maybe there is a way to encrypt integers?
CASE_STATUS_FIELD = "case_status"
CASE_STATUSES = ["confirmed", "probable", "suspected" "discarded", "omit_error"]
PATHOGEN_STATUS_FIELD = "pathogen_status"
PATHOGEN_STATUSES = ["endemic", "emerging", "unknown"]
SEX_AT_BIRTH_FIELD = "sex_at_birth"
SEXES_AT_BIRTH = ["male", "female", "other", "unknown"]
GENDER_FIELD = "gender"
GENDERS = ["man", "woman", "transgender", "non-binary", "other", "unknown"]
RACE_FIELD = "race"
RACES = ["Native Hawaiian or Other Pacific Islander", "Asian", "American Indian or Alaska Native", "Black or African American", "White", "Other"]
ETHNICITY_FIELD = "ethnicity"
ETHNICITIES = ["Hispanic or Latino", "Not Hispanic or Latino", "other"]
Y_N_NA_FIELDS = [
    "healthcare_worker",
    "previous_infection",
    "pregnancy_status",
    "vaccination",
    "hospitalized",
    "intensive_care",
    "home_monitoring",
    "isolated",
    "contact_with_case",
    "travel_history"
]
Y_N_NA = ["Y", "N", "NA"]
REASON_FOR_HOSPITALIZATION_FIELD = "reason_for_hospitalization"
REASONS_FOR_HOSPITALIZATION = ["monitoring", "treatment", "unknown"]
OUTCOME_FIELD = "outcome"
OUTCOMES = ["recovered", "death", "ongoing post-acute condition"]
CONTACT_SETTING_FIELD = "contact_setting"
CONTACT_SETTINGS = ["HOUSE", "WORK", "SCHOOL", "HEALTH", "PARTY", "BAR", "LARGE", "LARGECONTACT", "OTHER", "UNK"]
CONTACT_ANIMAL_FIELD = "contact_animal"
CONTACT_ANIMALS = ["PET", "PETRODENTS", "WILD", "WILDRODENTS", "OTHER"]
TRANSMISSON_FIELD = "transmission"
TRANSMISSIONS = ["ANIMAL", "HAI", "LAB", "MTCT", "OTHER", "FOMITE", "PTP", "SEX", "TRANSFU", "UNK"]

DATE_FIELDS = [
    "vaccination_date",
    "date_onset",
    "date_confirmation",
    "date_of_first",
    "date_hospitalization",
    "date_discharge_hospital",
    "date_admission_icu",
    "date_discharge_icu",
    "date_death",
    "date_recovered",
    "date_entry",
    "date_last_modified"
]
VALID_DATE = "%m-%d-%Y"

FIELD_VALIDATIONS = {
    CASE_STATUS_FIELD: CASE_STATUSES,
    PATHOGEN_STATUS_FIELD: PATHOGEN_STATUSES,
    SEX_AT_BIRTH_FIELD: SEXES_AT_BIRTH,
    GENDER_FIELD: GENDERS,
    RACE_FIELD: RACES,
    ETHNICITY_FIELD: ETHNICITIES,
    REASON_FOR_HOSPITALIZATION_FIELD: REASONS_FOR_HOSPITALIZATION,
    OUTCOME_FIELD: OUTCOMES,
    CONTACT_SETTING_FIELD: CONTACT_SETTINGS,
    CONTACT_ANIMAL_FIELD: CONTACT_ANIMALS,
    TRANSMISSON_FIELD: TRANSMISSIONS
}
FIELD_VALIDATIONS.update({k: Y_N_NA for k in Y_N_NA_FIELDS})
FIELD_VALIDATIONS.update({k: VALID_DATE for k in DATE_FIELDS})
