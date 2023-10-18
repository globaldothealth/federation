"""
Global.health system components test suite
"""

import json
import logging
import multiprocessing
import os
from time import sleep

import boto3
import pika
import pika.exceptions
from pymongo import MongoClient
import pytest
import requests
from requests.auth import HTTPBasicAuth

from amqp_server import publish_message, FLASK_PORT
from aws import get_jwt, get_certificate
from db import get_gh_db_data
from constants import (
    PARTNER_A_NAME,
    ESTIMATE_RT_JOB,
    GET_CASES_JOB,
    AMQP_CONFIG,
    PATHOGEN_A,
    DB_CONNECTION,
    DATABASE_NAME,
    CASE_COLLECTIONS,
    RT_COLLECTIONS,
    LOCALSTACK_URL,
    AWS_REGION,
    GRAPHQL_PORT,
    GRAPHQL_ENDPOINT,
    S3_A_BUCKET,
    PartnerA,
    PATHOGEN_DATA_DESTINATIONS,
    USERS_COLLECTION,
    AMQP_HOST,
    TOPIC_A_EXCHANGE,
    TOPIC_A_ROUTE,
)
from grpc_client import get_partner_cases, get_credentials


SECRETS_CLIENT = boto3.client(
    "secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)

FAKE_MESSAGE = "This is a test message"
FAKE_WORK_REQUEST = {"info": FAKE_MESSAGE}

GH_WORK_REQUEST_URL = os.environ.get("GH_WORK_REQUEST_URL")

GRPC_CLIENT = os.environ.get("GRPC_CLIENT")

GRAPHQL_SERVER = os.environ.get("GRAPHQL_SERVER")
GRAPHQL_SERVICE = f"http://{GRAPHQL_SERVER}:{GRAPHQL_PORT}/{GRAPHQL_ENDPOINT}"

WAIT_TIME = 2
RETRIES = 42


def get_gh_s3_file(file_name, retry=True):
    """
    Get data from a file in S3

    Args:
        file_name (str): The name of the file
        retry (bool, optional): Whether the function should retry instead of raise an Exception

    Returns:
        dict: The data retrieved from S3

    Raises:
        Exception: The data should download
    """

    s3 = boto3.resource("s3", endpoint_url=LOCALSTACK_URL)
    obj = s3.Object(S3_A_BUCKET, file_name)
    try:
        return json.loads(obj.get()["Body"].read().decode("utf-8"))
    except Exception as exc:
        print(
            f"An exception happened trying to return the contents of {file_name} from bucket {S3_A_BUCKET}: {exc}"
        )
        # eventual consistency, immediate jank
        if retry:
            sleep(5)
            return get_gh_s3_file(file_name, retry=False)
        raise Exception(
            f"Could not get data from {file_name} from bucket {S3_A_BUCKET}"
        )


def get_api_key() -> str:
    """
    Get the API key for a partner from AWS Secrets Manager

    Returns:
        str: The partner's API key
    """

    response = SECRETS_CLIENT.get_secret_value(
        SecretId=f"{PartnerA.name}_api_key_password"
    )
    return response.get("SecretString")


def send_work_request(key: str, pathogen: str, job: str):
    """
    Send a request for work to the Global.health server

    Args:
        key (str): The partner API key
        pathogen (str): The name of the pathogen for requested work
        job (str): The name of the job to be done
    """

    auth = HTTPBasicAuth(PartnerA.name, key)
    url = f"{GH_WORK_REQUEST_URL}/{pathogen}/{job}"
    _ = requests.get(url, auth=auth)


def approve_data(collection_name: str):
    """
    Manually approve partner data

    Args:
        collection_name (str): Database collection containing data
    """
    client = MongoClient(DB_CONNECTION)
    db = client[DATABASE_NAME]
    collection = db[collection_name]
    collection.update_many(
        {}, {"$set": {"verifiedBy": "someoneSenior"}}, upsert=False, array_filters=None
    )


class NoMessageException(Exception):
    """
    Raised when the topic queue does not get a message
    """

    pass


def consume_messages(write_pipe: object, exchange: str, route: str) -> None:
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


def wait_for_message(read_pipe: object) -> None:
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
    raise NoMessageException("Did not get message as expected.")


def reset_database(collection_name: str):
    """
    Delete all data from a database collection

    Args:
        collection_name (str): Database collection containing data
    """
    client = MongoClient(DB_CONNECTION)
    db = client[DATABASE_NAME]
    collection = db[collection_name]
    collection.delete_many({})


def test_server_publishes_messages():
    """
    The server should publish messages to the relevant exchange, route, and queue
    """

    pathogen_config = PATHOGEN_DATA_DESTINATIONS.get(PATHOGEN_A)

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=AMQP_CONFIG.host)
    )
    channel = connection.channel()
    channel.exchange_declare(
        exchange=pathogen_config.topic_exchange, exchange_type="topic"
    )
    result = channel.queue_declare(queue=pathogen_config.topic_exchange, durable=True)
    queue_name = result.method.queue
    channel.queue_bind(
        exchange=pathogen_config.topic_exchange,
        queue=queue_name,
        routing_key=pathogen_config.topic_route,
    )

    try:
        publish_message(message=FAKE_MESSAGE, pathogen_config=pathogen_config)
    except pika.exceptions.UnroutableError:
        pytest.fail("Message was returned")


def test_get_partner_cases():
    """
    The gRPC client should get cases from a partner and store them in a database
    """

    token = get_jwt()
    certificate = get_certificate(PartnerA.domain_name)
    credentials = get_credentials(token, certificate)
    try:
        cases = get_partner_cases(PATHOGEN_A, PartnerA, credentials)
    except Exception:
        pytest.fail("Failed to get cases")
    finally:
        collection_name = CASE_COLLECTIONS.get(PATHOGEN_A)
        reset_database(collection_name)
    assert cases


def test_rest_to_grpc_to_data():
    """
    The server should receive work requests for case data, delegate the work to a partner, and store the results in a database and data store
    """

    api_key = get_api_key()
    send_work_request(api_key, PATHOGEN_A, GET_CASES_JOB)

    s3_cases = get_gh_s3_file(f"{PATHOGEN_A}.json")
    collection_name = CASE_COLLECTIONS.get(PATHOGEN_A)
    db_cases = get_gh_db_data(collection_name)

    reset_database(collection_name)

    assert len(s3_cases) > 0
    assert len(db_cases) == len(s3_cases)


def test_rt_estimation():
    """
    The server should receive work requests for R(t) estimate data, delegate the work to a partner, and store the results in a database and data store
    """

    api_key = get_api_key()
    send_work_request(api_key, PATHOGEN_A, ESTIMATE_RT_JOB)

    s3_estimates = get_gh_s3_file(f"{PATHOGEN_A}_rt.json")
    collection_name = RT_COLLECTIONS.get(PATHOGEN_A)
    db_estimates = get_gh_db_data(collection_name)

    reset_database(collection_name)

    assert len(s3_estimates) > 0
    assert len(db_estimates) == len(s3_estimates)


def test_graphql():
    """
    The server should share approved data via GraphQL
    """

    api_key = get_api_key()
    send_work_request(api_key, PATHOGEN_A, GET_CASES_JOB)
    collection_name = CASE_COLLECTIONS.get(PATHOGEN_A)
    approve_data(collection_name)
    # Get all cases, return only their locations
    query = f"""
        query Cases {{
            cases(pathogen: "{PATHOGEN_A}"){{
                locationInformation
            }}
        }}
    """

    db_cases = get_gh_db_data(collection_name)
    expected = [case.get("location_information") for case in db_cases]

    response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})

    reset_database(collection_name)

    assert response.status_code == 200
    assert expected == [
        case.get("locationInformation")
        for case in json.loads(response.text).get("cases")
    ]


def test_query_requires_pathogen():
    """
    GraphQL queries should require the name of a pathogen
    """

    query = """
        query Cases {
            cases {
                locationInformation
            }
        }
    """

    response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})
    assert response.status_code == 400


def test_query_untracked_pathogen():
    """
    GraphQL queries should require the name of a pathogen with data
    """

    query = """
        query Cases {
            cases(pathogen: "foo") {
                locationInformation
            }
        }
    """

    response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})
    assert response.status_code == 400


def test_data_lifecycle():
    """
    Data subject to manual approval should enter a staging area, where it is not shared via GraphQL
    After approval, data is shared via GraphQL (manual approval happens in another service)
    """

    r, w = multiprocessing.Pipe()
    args = (
        w,
        TOPIC_A_EXCHANGE,
        TOPIC_A_ROUTE,
    )
    amqp_consumer = multiprocessing.Process(target=consume_messages, args=args)
    amqp_consumer.start()

    api_key = get_api_key()
    send_work_request(api_key, PATHOGEN_A, GET_CASES_JOB)

    query = f"""
        query Cases {{
            cases(pathogen: "{PATHOGEN_A}"){{
                locationInformation
            }}
        }}
    """

    collection_name = CASE_COLLECTIONS.get(PATHOGEN_A)
    db_cases = get_gh_db_data(collection_name)
    assert db_cases
    assert db_cases[0].get("createdBy")
    assert not db_cases[0].get("verifiedBy")

    response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})

    assert response.status_code == 200
    assert json.loads(response.text).get("cases") == []

    approve_data(collection_name)

    db_cases = get_gh_db_data(collection_name)
    assert db_cases[0].get("createdBy")
    assert db_cases[0].get("verifiedBy")
    expected = [case.get("location_information") for case in db_cases]

    response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})

    reset_database(collection_name)

    assert response.status_code == 200
    assert expected == [
        case.get("locationInformation")
        for case in json.loads(response.text).get("cases")
    ]

    # Manual approval in another service should trigger the message
    with pytest.raises(NoMessageException):
        wait_for_message(r)

    amqp_consumer.terminate()


def test_auto_verified_data_public():
    """
    Automatically approved data should be shared via GraphQL
    """

    r, w = multiprocessing.Pipe()
    args = (
        w,
        TOPIC_A_EXCHANGE,
        TOPIC_A_ROUTE,
    )
    amqp_consumer = multiprocessing.Process(target=consume_messages, args=args)
    amqp_consumer.start()

    client = MongoClient(DB_CONNECTION)
    db = client[DATABASE_NAME]
    collection = db[USERS_COLLECTION]
    collection.update_one(
        {"name": PARTNER_A_NAME}, {"$set": {"roles": ["senior curator"]}}
    )

    api_key = get_api_key()
    send_work_request(api_key, PATHOGEN_A, GET_CASES_JOB)

    try:
        wait_for_message(r)
    except Exception:
        pytest.fail("Could not consume message")
    finally:
        amqp_consumer.terminate()

    query = f"""
        query Cases {{
            cases(pathogen: "{PATHOGEN_A}"){{
                locationInformation
            }}
        }}
    """

    collection_name = CASE_COLLECTIONS.get(PATHOGEN_A)
    db_cases = get_gh_db_data(collection_name)
    assert db_cases[0].get("createdBy")
    assert db_cases[0].get("verifiedBy")
    expected = [case.get("location_information") for case in db_cases]

    response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})

    assert response.status_code == 200
    assert expected == [
        case.get("locationInformation")
        for case in json.loads(response.text).get("cases")
    ]

    reset_database(collection_name)


# https://docs.mongoengine.org/guide/querying.html#retrieving-a-subset-of-fields
# if fields that are not downloaded are accessed, their default value (or None if no default value is provided) will be given
def test_curator_data_not_public():
    """
    Data shared via GraphQL should not contain curation information
    """

    api_key = get_api_key()
    send_work_request(api_key, PATHOGEN_A, GET_CASES_JOB)
    collection_name = CASE_COLLECTIONS.get(PATHOGEN_A)
    approve_data(collection_name)

    query = f"""
        query Cases {{
            cases(pathogen: "{PATHOGEN_A}"){{
                createdBy
            }}
        }}
    """

    response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})

    assert response.status_code == 200
    assert not json.loads(response.text).get("cases")[0].get("createdBy")

    query = f"""
        query Cases {{
            cases(pathogen: "{PATHOGEN_A}"){{
                verifiedBy
            }}
        }}
    """

    response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})

    assert response.status_code == 200
    assert not json.loads(response.text).get("cases")[0].get("verifiedBy")

    reset_database(collection_name)


def test_healthchecks():
    """
    Healthcheck endpoints should work
    """

    urls = [
        f"http://{GRPC_CLIENT}:{FLASK_PORT}/health",
        f"http://{GRAPHQL_SERVER}:{GRAPHQL_PORT}/health",
    ]

    for url in urls:
        response = requests.get(url=url)
        assert response.status_code == 200
