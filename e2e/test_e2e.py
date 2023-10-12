"""
End-to-end test suite
"""

from datetime import date
import json
import logging
import multiprocessing
import os
from time import sleep

import boto3
import pika
from pymongo import MongoClient
import pytest
import requests
from requests.auth import HTTPBasicAuth


SIM_A_HOST = os.environ.get("SIM_A_HOST")
SIM_A_PORT = os.environ.get("SIM_A_PORT")
SIM_B_HOST = os.environ.get("SIM_B_HOST")
SIM_B_PORT = os.environ.get("SIM_B_PORT")
SIM_C_HOST = os.environ.get("SIM_C_HOST")
SIM_C_PORT = os.environ.get("SIM_C_PORT")
SIM_A_ENDPOINT = f"http://{SIM_A_HOST}:{SIM_A_PORT}/cases"
SIM_B_ENDPOINT = f"http://{SIM_B_HOST}:{SIM_B_PORT}/cases"
SIM_C_ENDPOINT = f"http://{SIM_C_HOST}:{SIM_C_PORT}/cases"

AMQP_HOST = os.environ.get("AMQP_HOST")

PATHOGEN_A = os.environ.get("PATHOGEN_A")
PATHOGEN_B = os.environ.get("PATHOGEN_B")
PATHOGEN_C = os.environ.get("PATHOGEN_C")

ESTIMATE_RT_JOB = "EstimateRt"
GET_CASES_JOB = "GetCases"

TOPIC_A_EXCHANGE = PATHOGEN_A + "_topic_exchange"
TOPIC_A_QUEUE = PATHOGEN_A + "_topic_queue"
TOPIC_A_ROUTE = PATHOGEN_A + "_topic_route"

TOPIC_B_EXCHANGE = PATHOGEN_B + "_topic_exchange"
TOPIC_B_QUEUE = PATHOGEN_B + "_topic_queue"
TOPIC_B_ROUTE = PATHOGEN_B + "_topic_route"

TOPIC_C_EXCHANGE = PATHOGEN_C + "_topic_exchange"
TOPIC_C_QUEUE = PATHOGEN_C + "_topic_queue"
TOPIC_C_ROUTE = PATHOGEN_C + "_topic_route"

DB_CONNECTION = os.environ.get("DB_CONNECTION")
DATABASE_NAME = os.environ.get("DB_NAME")
GH_USERS_COLLECTION = os.environ.get("GH_USERS_COLLECTION")
GH_CASES_COLLECTION = os.environ.get("GH_CASES_COLLECTION")
GH_RT_COLLECTION = os.environ.get("GH_RT_COLLECTION")

LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL")
S3_BUCKET = os.environ.get("S3_A_BUCKET")
S3_CASES_FILE_NAME = f"{PATHOGEN_A}.json"
S3_RT_FILE_NAME = f"{PATHOGEN_A}_rt.json"

AWS_REGION = os.environ.get("AWS_REGION")
SECRETS_CLIENT = boto3.client(
    "secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)

GH_WORK_REQUEST_URL = os.environ.get("GH_WORK_REQUEST_URL")

GRAPHQL_HOST = os.environ.get("GRAPHQL_HOST")
GRAPHQL_PORT = os.environ.get("GRAPHQL_PORT")
GRAPHQL_ENDPOINT = os.environ.get("GRAPHQL_ENDPOINT")
GRAPHQL_SERVICE = f"http://{GRAPHQL_HOST}:{GRAPHQL_PORT}/{GRAPHQL_ENDPOINT}"

PARTNER_A_NAME = os.environ.get("PARTNER_A_NAME")
PARTNER_A_LOCATION = os.environ.get("PARTNER_A_LOCATION")

PARTNER_B_NAME = os.environ.get("PARTNER_B_NAME")
PARTNER_C_NAME = os.environ.get("PARTNER_C_NAME")

PARTNER_NAMES = [PARTNER_A_NAME, PARTNER_B_NAME, PARTNER_C_NAME]

WAIT_TIME = 2
RETRIES = 42

LOCATION_INFORMATION = "USA"
OUTCOME = "recovered"
DATE_CONFIRMATION = f"01-01-2023"
HOSPITALIZED = "Y"

FAKE_CASE = {
    "pathogen": PATHOGEN_A,
    "location_information": LOCATION_INFORMATION,
    "outcome": OUTCOME,
    "date_confirmation": DATE_CONFIRMATION,
    "hospitalized": HOSPITALIZED,
}


def consume_messages(
    write_pipe: multiprocessing.connection.Connection, exchange: str, route: str
) -> None:
    """
    Consume messages and create acknowledgments

    Args:
        write_pipe (multiprocessing.connection.Connection): One end of pipe, mocks behavior of subscriber
        exchange (str): Where the publisher sends a message
        route (str): Where the exchange sends a message
    """

    logging.info("Consuming messages")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=AMQP_HOST))
    channel = connection.channel()

    channel.exchange_declare(exchange=exchange, exchange_type="topic")
    result = channel.queue_declare("", durable=True)
    queue_name = result.method.queue

    logging.info(f"Created queue {queue_name}")

    channel.queue_bind(exchange=exchange, queue=queue_name, routing_key=route)

    def callback(ch, method, properties, body):
        logging.debug("The topic message was received.")
        write_pipe.send("OK")

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    logging.info(" [*] Waiting for messages.")
    channel.start_consuming()


def wait_for_message(read_pipe: multiprocessing.connection.Connection) -> None:
    """
    Wait a given amount of time for a message acknowledgment

    Args:
        read_pipe (multiprocessing.connection.Connection): One end of pipe, mocks behavior of subscriber

    Raises:
        Exception: The read pipe should receive a message acknowlegdment in a given amount of time
    """

    logging.debug("Checking for message about cases.")
    current_attempt = 0
    while current_attempt < RETRIES:
        if read_pipe.poll():
            logging.debug("Got message.")
            return
        logging.debug("Waiting for message.")
        current_attempt += 1
        sleep(WAIT_TIME)
    raise Exception("Did not get message as expected.")


def get_api_key(partner_name: str) -> str:
    """
    Get the API key for a partner from AWS Secrets Manager

    Args:
        partner_name (str): The partner to get an API key for

    Returns:
        str: The partner's API key
    """

    response = SECRETS_CLIENT.get_secret_value(
        SecretId=f"{partner_name}_api_key_password"
    )
    return response.get("SecretString")


def send_work_request(partner_name: str, key: str, pathogen: str, job: str) -> None:
    """
    Send a request for work to the Global.health server

    Args:
        partner_name (str): The name of the partner requesting work
        key (str): The partner API key
        pathogen (str): The name of the pathogen for requested work
        job (str): The name of the job to be done
    """

    auth = HTTPBasicAuth(partner_name, key)
    url = f"{GH_WORK_REQUEST_URL}/{pathogen}/{job}"
    _ = requests.get(url, auth=auth)


def get_gh_db_data(collection_name: str) -> list:
    """
    Get data from a collection in the Global.health database

    Args:
        collection_name (str): The name of the database collection

    Returns:
        list: The data retrieved from the collection
    """

    logging.info("Getting data from db")
    client = MongoClient(DB_CONNECTION)
    db = client[DATABASE_NAME]
    collection = db[collection_name]
    data = list(collection.find())
    logging.info(f"Got data from db: {data}")
    return data


def get_gh_s3_data(file_name: str, retry: bool = True) -> dict:
    """
    Get data from a file in AWS S3

    Args:
        file_name (str): The name of the file
        retry (bool, optional): Whether the function should retry instead of raise an Exception

    Returns:
        dict: The data retrieved from S3

    Raises:
        Exception: The data should download
    """

    s3 = boto3.resource("s3", endpoint_url=LOCALSTACK_URL)
    obj = s3.Object(S3_BUCKET, file_name)
    try:
        return json.loads(obj.get()["Body"].read().decode("utf-8"))
    except Exception:
        logging.exception(
            f"An exception happened trying to return the contents of {file_name} from bucket {S3_BUCKET}"
        )
        # eventual consistency, immediate jank
        if retry:
            sleep(5)
            return get_gh_s3_data(file_name, retry=False)
        raise Exception(f"Could not get data from {file_name} from bucket {S3_BUCKET}")


def get_gh_s3_file(file_name: str, retry: bool = True) -> None:
    """
    Download a file from AWS S3

    Args:
        file_name (str): The name of the file
        retry (bool, optional): Whether the function should retry instead of raise an Exception

    Returns:
        None: Description

    Raises:
        Exception: The file should download
    """

    s3 = boto3.client("s3", endpoint_url=LOCALSTACK_URL)
    try:
        s3.download_file(S3_BUCKET, file_name, file_name)
    except Exception:
        logging.exception(
            f"An exception happened trying to download {file_name} from bucket {S3_BUCKET}"
        )
        # eventual consistency, immediate jank
        if retry:
            sleep(5)
            return get_gh_s3_data(file_name, retry=False)
        raise Exception(f"Could not download {file_name} from bucket {S3_BUCKET}")


@pytest.fixture(scope="session", autouse=True)
def elevate_curator_roles() -> None:
    """
    Elevate curator roles for partner data auto-approval
    """

    logging.info("Elevating curator roles for partner data auto-approval")
    client = MongoClient(DB_CONNECTION)
    db = client[DATABASE_NAME]
    collection = db[GH_USERS_COLLECTION]
    for partner_name in PARTNER_NAMES:
        collection.update_one(
            {"name": partner_name}, {"$set": {"roles": ["senior curator"]}}
        )


def test_sim_cases_in_gh():
    """
    Testing for presence of sim-created cases in G.h
    A sim creates cases in a partner database, G.h requests and shares them
    """

    logging.info("Testing for presence of sim-created cases in G.h")
    r, w = multiprocessing.Pipe()

    args = (
        w,
        TOPIC_A_EXCHANGE,
        TOPIC_A_ROUTE,
    )
    amqp_consumer = multiprocessing.Process(target=consume_messages, args=args)
    amqp_consumer.start()

    logging.info("Creating case with outbreak simulator")

    try:
        requests.post(SIM_A_ENDPOINT, json=[FAKE_CASE])
    except Exception:
        amqp_consumer.terminate()
        pytest.fail(f"Could not POST {FAKE_CASE} to endpoint {SIM_A_ENDPOINT}")

    try:
        key = get_api_key(PARTNER_A_NAME)
        send_work_request(PARTNER_A_NAME, key, PATHOGEN_A, GET_CASES_JOB)
    except Exception:
        amqp_consumer.terminate()
        pytest.fail("Could not send work request")

    try:
        wait_for_message(r)
    except Exception:
        amqp_consumer.terminate()
        pytest.fail("Could not consume message")

    amqp_consumer.terminate()

    logging.info("Checking for case in database")

    actual = get_gh_db_data(GH_CASES_COLLECTION)
    FAKE_CASE["pathogen"] = PATHOGEN_A
    expected = [FAKE_CASE]
    del actual[0]["_id"]

    assert actual[0].get("createdBy")
    assert actual[0].get("verifiedBy")

    del actual[0]["createdBy"]
    del actual[0]["verifiedBy"]

    assert expected == actual

    logging.info("Checking for case in S3")

    actual = get_gh_s3_data(S3_CASES_FILE_NAME)

    assert expected == actual

    query = f"""
        query Cases {{
            cases(pathogen: "{PATHOGEN_A}"){{
                outcome
            }}
        }}
    """

    expected = [FAKE_CASE["outcome"]]

    logging.info("Checking for case in GraphQL service")

    try:
        response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})
        actual = [
            case.get("outcome") for case in json.loads(response.text).get("cases")
        ]
    except Exception:
        pytest.fail(f"Could not do GraphQL query at {GRAPHQL_SERVICE}")

    assert expected == actual


def test_multiple_outbreaks():
    """
    Testing for presence of sim-created cases in G.h, for multiple outbreaks
    Sims create cases in partner databases, G.h requests and shares them
    """

    logging.info("Testing for presence of sim-created cases in G.h")
    r, w = multiprocessing.Pipe()

    args = (
        w,
        TOPIC_B_EXCHANGE,
        TOPIC_B_ROUTE,
    )
    amqp_consumer = multiprocessing.Process(target=consume_messages, args=args)
    amqp_consumer.start()

    logging.info("Creating case with outbreak simulator")
    location_information = "USA"
    outcome = "recovered"
    case = {
        "location_information": location_information,
        "outcome": outcome,
        "pathogen": PATHOGEN_B,
    }

    try:
        requests.post(SIM_B_ENDPOINT, json=[case])
    except Exception:
        amqp_consumer.terminate()
        pytest.fail(f"Could not POST {case} to endpoint {SIM_B_ENDPOINT}")

    # G.h needs to be send work request to make gRPC request to service
    try:
        key = get_api_key(PARTNER_B_NAME)
        send_work_request(PARTNER_B_NAME, key, PATHOGEN_B, GET_CASES_JOB)
    except Exception:
        amqp_consumer.terminate()
        pytest.fail("Could not send work request")

    try:
        wait_for_message(r)
    except Exception:
        amqp_consumer.terminate()
        pytest.fail("Could not consume message")

    amqp_consumer.terminate()

    r, w = multiprocessing.Pipe()

    args = (
        w,
        TOPIC_C_EXCHANGE,
        TOPIC_C_ROUTE,
    )
    amqp_consumer = multiprocessing.Process(target=consume_messages, args=args)
    amqp_consumer.start()

    logging.info("Creating case with outbreak simulator")
    case["pathogen"] = PATHOGEN_C

    try:
        requests.post(SIM_C_ENDPOINT, json=[case])
    except Exception:
        amqp_consumer.terminate()
        pytest.fail(f"Could not POST {case} to endpoint {SIM_C_ENDPOINT}")

    try:
        key = get_api_key(PARTNER_C_NAME)
        send_work_request(PARTNER_C_NAME, key, PATHOGEN_C, GET_CASES_JOB)
    except Exception:
        amqp_consumer.terminate()
        pytest.fail("Could not send work request")

    try:
        wait_for_message(r)
    except Exception:
        amqp_consumer.terminate()
        pytest.fail("Could not consume message")

    amqp_consumer.terminate()

    query = f"""
        query Cases {{
            cases(pathogen: "{PATHOGEN_B}") {{
                outcome
                dateConfirmation
                hospitalized
            }}
        }}
    """

    expected = [case["outcome"]]

    logging.info("Checking for case in GraphQL services")

    try:
        response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})
        actual = [
            case.get("outcome") for case in json.loads(response.text).get("cases")
        ]
    except Exception:
        pytest.fail(f"Could not do GraphQL query at {GRAPHQL_SERVICE}")

    assert expected == actual

    query = f"""
        query Cases {{
            cases(pathogen: "{PATHOGEN_C}") {{
                outcome
                dateConfirmation
                hospitalized
            }}
        }}
    """

    try:
        response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})
        actual = [
            case.get("outcome") for case in json.loads(response.text).get("cases")
        ]
    except Exception:
        pytest.fail(f"Could not do GraphQL query at {GRAPHQL_SERVICE}")

    assert expected == actual


def test_rt_estimates_in_gh():
    """
    Testing for presence of R(t) estimates in G.h
    G.h requests them R(t) estimates from partners and shares the results
    """

    logging.info("Testing for presence of R(t) estimates in G.h")
    r, w = multiprocessing.Pipe()

    args = (
        w,
        TOPIC_A_EXCHANGE,
        TOPIC_A_ROUTE,
    )
    amqp_consumer = multiprocessing.Process(target=consume_messages, args=args)
    amqp_consumer.start()

    logging.info("Creating cases with outbreak simulator")
    cases = []
    for day in range(1, 31):
        date_confirmation = f"01-{day}-2023"
        for _ in range(50):
            case = FAKE_CASE.copy()
            case["date_confirmation"] = date_confirmation
            cases.append(case)
    try:
        requests.post(SIM_A_ENDPOINT, json=cases)
    except Exception:
        amqp_consumer.terminate()
        pytest.fail(f"Could not POST {cases} to endpoint {SIM_A_ENDPOINT}")

    try:
        key = get_api_key(PARTNER_A_NAME)
        send_work_request(PARTNER_A_NAME, key, PATHOGEN_A, ESTIMATE_RT_JOB)
    except Exception:
        amqp_consumer.terminate()
        pytest.fail("Could not send work request")

    try:
        wait_for_message(r)
    except Exception:
        amqp_consumer.terminate()
        pytest.fail("Could not consume message")

    amqp_consumer.terminate()

    logging.info("Checking for R(t) estimate in database")

    db_rt_estimates = get_gh_db_data(GH_RT_COLLECTION)
    for i in range(len(db_rt_estimates)):
        del db_rt_estimates[i]["_id"]
        assert db_rt_estimates[i].get("createdBy")
        assert db_rt_estimates[i].get("verifiedBy")
        del db_rt_estimates[i]["createdBy"]
        del db_rt_estimates[i]["verifiedBy"]

    assert db_rt_estimates

    logging.info("Checking for R(t) estimate in S3")

    s3_rt_estimates = get_gh_s3_data(S3_RT_FILE_NAME)

    assert s3_rt_estimates == db_rt_estimates

    query = f"""
        query RtEstimates {{
            estimates(pathogen: "{PATHOGEN_A}") {{
                date
                cases
                rMean
                rVar
                qLower
                qUpper
            }}
        }}
    """

    logging.info("Checking for R(t) estimate in GraphQL service")

    try:
        response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})
        gql_rt_estimates = json.loads(response.text).get("estimates")
    except Exception:
        pytest.fail(f"Could not do GraphQL query at {GRAPHQL_SERVICE}")

    assert gql_rt_estimates == db_rt_estimates

    logging.info("Checking for R(t) estimate graphic in S3")
    file_path = f"{PATHOGEN_A}/{date.today()}_{PARTNER_A_LOCATION}.png"
    try:
        get_gh_s3_file(file_path)
    except Exception:
        pytest.fail(f"Could not get R(t) graph from {file_path}")
