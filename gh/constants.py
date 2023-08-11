from dataclasses import dataclass
import os


PARTNER_A_NAME = os.environ.get("PARTNER_A_NAME")
PARTNER_B_NAME = os.environ.get("PARTNER_B_NAME")
PARTNER_C_NAME = os.environ.get("PARTNER_C_NAME")

PARTNER_A_LOCATION = "A-land"

PATHOGEN_A = os.environ.get("PATHOGEN_A", "")
PATHOGEN_B = os.environ.get("PATHOGEN_B", "")
PATHOGEN_C = os.environ.get("PATHOGEN_C", "")

PATHOGENS = [PATHOGEN_A, PATHOGEN_B, PATHOGEN_C]

AMQP_HOST = os.environ.get("AMQP_HOST")
DIRECT_EXCHANGE = "gh_direct_exchange"
DIRECT_QUEUE = "gh_direct_queue"
DIRECT_ROUTE = "gh_direct_route"

ESTIMATE_RT_JOB = "EstimateRt"
GET_CASES_JOB = "GetCases"

PATHOGEN_JOBS = {
    ESTIMATE_RT_JOB: [PATHOGEN_A, PATHOGEN_B, PATHOGEN_C],
    GET_CASES_JOB: [PATHOGEN_A, PATHOGEN_B, PATHOGEN_C],
}

# This will become a lookup table, each pathogen /w own params
# Start and end date from G.h? From partner?
RT_PARAMS = {
    "start_date": "01-01-2023",
    "end_date": "01-31-2023",
    "q_lower": 0.3,
    "q_upper": 0.7,
    "gt_distribution": [0.25, 0.5, 0.25],
    "delay_distribution": [0.1, 0.5, 0.4]
}

TOPIC_A_EXCHANGE = PATHOGEN_A + "_topic_exchange"
TOPIC_A_QUEUE = PATHOGEN_A + "_topic_queue"
TOPIC_A_ROUTE = PATHOGEN_A + "_topic_route"

GRPC_A_HOST = os.environ.get("GRPC_A_HOST")
GRPC_A_PORT = os.environ.get("GRPC_A_PORT")

TOPIC_B_EXCHANGE = PATHOGEN_B + "_topic_exchange"
TOPIC_B_QUEUE = PATHOGEN_B + "_topic_queue"
TOPIC_B_ROUTE = PATHOGEN_B + "_topic_route"

GRPC_B_HOST = os.environ.get("GRPC_B_HOST")
GRPC_B_PORT = os.environ.get("GRPC_B_PORT")

TOPIC_C_EXCHANGE = PATHOGEN_C + "_topic_exchange"
TOPIC_C_QUEUE = PATHOGEN_C + "_topic_queue"
TOPIC_C_ROUTE = PATHOGEN_C + "_topic_route"

GRPC_C_HOST = os.environ.get("GRPC_C_HOST")
GRPC_C_PORT = os.environ.get("GRPC_C_PORT")

GRAPHQL_PORT = os.environ.get("GRAPHQL_PORT")
GRAPHQL_ENDPOINT = "graphql"

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = int(os.environ.get("DB_PORT", 0))
DB_CONNECTION = os.environ.get("DB_CONNECTION")
DATABASE_NAME = os.environ.get("DB_NAME")

USERS_COLLECTION = os.environ.get("GH_USERS_COLLECTION")

GH_A_COLLECTION = os.environ.get("GH_A_COLLECTION")
GH_B_COLLECTION = os.environ.get("GH_B_COLLECTION")
GH_C_COLLECTION = os.environ.get("GH_C_COLLECTION")

GH_D_COLLECTION = os.environ.get("GH_A_RT_COLLECTION")
GH_E_COLLECTION = os.environ.get("GH_B_RT_COLLECTION")
GH_F_COLLECTION = os.environ.get("GH_C_RT_COLLECTION")

CASE_COLLECTIONS = {
    PATHOGEN_A: GH_A_COLLECTION,
    PATHOGEN_B: GH_B_COLLECTION,
    PATHOGEN_C: GH_C_COLLECTION,
}

RT_COLLECTIONS = {
    PATHOGEN_A: GH_D_COLLECTION,
    PATHOGEN_B: GH_E_COLLECTION,
    PATHOGEN_C: GH_F_COLLECTION,
}

S3_A_BUCKET = os.environ.get("S3_A_BUCKET")
S3_B_BUCKET = os.environ.get("S3_B_BUCKET")
S3_C_BUCKET = os.environ.get("S3_C_BUCKET")

RT_ESTIMATES_FOLDER = "rt_estimates"

LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION")

COGNITO_USER_NAME = os.environ.get("COGNITO_USER_NAME")
COGNITO_USER_PASSWORD = os.environ.get("COGNITO_USER_PASSWORD")


@dataclass
class Partner:
    name: str
    grpc_host: str
    grpc_port: int


PartnerA = Partner(PARTNER_A_NAME, GRPC_A_HOST, GRPC_A_PORT)
PartnerB = Partner(PARTNER_B_NAME, GRPC_B_HOST, GRPC_B_PORT)
PartnerC = Partner(PARTNER_C_NAME, GRPC_C_HOST, GRPC_C_PORT)
PARTNERS = [PartnerA, PartnerB, PartnerC]


@dataclass
class PathogenConfig:
    name: str
    topic_exchange: str
    topic_route: str
    topic_queue: str
    cases_collection: str
    rt_collection: str
    s3_bucket: str


PathogenConfigA = PathogenConfig(PATHOGEN_A, TOPIC_A_EXCHANGE, TOPIC_A_ROUTE, TOPIC_A_QUEUE, GH_A_COLLECTION, GH_D_COLLECTION, S3_A_BUCKET)
PathogenConfigB = PathogenConfig(PATHOGEN_B, TOPIC_B_EXCHANGE, TOPIC_B_ROUTE, TOPIC_B_QUEUE, GH_B_COLLECTION, GH_E_COLLECTION, S3_B_BUCKET)
PathogenConfigC = PathogenConfig(PATHOGEN_C, TOPIC_C_EXCHANGE, TOPIC_C_ROUTE, TOPIC_C_QUEUE, GH_C_COLLECTION, GH_F_COLLECTION, S3_C_BUCKET)


@dataclass
class GhAMQPConfig:
    host: str
    exchange: str
    queue: str
    route: str


AMQP_CONFIG = GhAMQPConfig(AMQP_HOST, DIRECT_EXCHANGE, DIRECT_QUEUE, DIRECT_ROUTE)


PATHOGEN_DATA_SOURCES = {
    PATHOGEN_A: [PartnerA],
    PATHOGEN_B: [PartnerB],
    PATHOGEN_C: [PartnerC]
}

PATHOGEN_DATA_DESTINATIONS = {
    PATHOGEN_A: PathogenConfigA,
    PATHOGEN_B: PathogenConfigB,
    PATHOGEN_C: PathogenConfigC
}
