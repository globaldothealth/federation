"""
Partner data server test suite
"""

import json
import os

import boto3
from google.protobuf.json_format import MessageToDict
import grpc
import pika
import pika.exceptions
import psycopg
import pytest
import requests

from cases_pb2 import CasesRequest
from cases_pb2_grpc import CasesStub
from rt_estimate_pb2 import RtEstimateRequest
from rt_estimate_pb2_grpc import RtEstimatesStub

from data_server import get_client_id, get_jwt, FLASK_PORT, get_certificate_arn
from constants import (
    PATHOGEN_A,
    PATHOGENS,
    AMQP_HOST,
    TOPIC_A_EXCHANGE,
    TOPIC_A_ROUTE,
    DB_CONNECTION,
    LOCALSTACK_URL,
    AWS_REGION,
    TABLE_NAME,
)


GRPC_HOST = os.environ.get("GRPC_HOST")
GRPC_PORT = os.environ.get("GRPC_PORT")

TEST_CASE = {
    "location_information": "USA",
    "outcome": "recovered",
    "pathogen": PATHOGEN_A,
    "date_confirmation": "01-01-2023",
    "hospitalized": "Y",
}


def get_metadata() -> list:
    """
    Get request metadata

    Returns:
        list: Request metadata
    """

    client_id = get_client_id()
    token = get_jwt(client_id)
    return [("authorization", f"bearer {token}")]


def get_client_credentials() -> grpc.ChannelCredentials:
    """
    Get data required to create a secure channel

    Returns:
        grpc.ChannelCredentials: The client's channel credentials
    """

    acm_client = boto3.client(
        "acm", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
    )
    response = acm_client.get_certificate(CertificateArn=get_certificate_arn())
    cert_str = response.get("Certificate")
    certificate = bytes(cert_str, encoding="utf8")
    client_id = get_client_id()
    token = get_jwt(client_id)
    token_credentials = grpc.access_token_call_credentials(token)
    channel_credentials = grpc.ssl_channel_credentials(certificate)

    return grpc.composite_channel_credentials(channel_credentials, token_credentials)


def insert_case(pathogen_name: str, data: dict) -> None:
    """
    Insert a case into the database

    Args:
        pathogen_name (str): Pathogen name
        data (dict): Case data
    """

    location_information = data["location_information"]
    outcome = data["outcome"]
    date_confirmation = data["date_confirmation"]
    hospitalized = data["hospitalized"]

    try:
        with psycopg.connect(DB_CONNECTION) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""INSERT INTO "{TABLE_NAME}" (location_information, outcome, date_confirmation, hospitalized, pathogen) VALUES (%s, %s, %s, %s, %s)""",
                    (
                        location_information,
                        outcome,
                        date_confirmation,
                        hospitalized,
                        pathogen_name,
                    ),
                )
                conn.commit()
    except Exception as exc:
        print(f"Could not add case to database: {exc}")
        raise
    finally:
        conn.close()


def get_cases(pathogen_name: str) -> list:
    """
    Get case data from the database

    Args:
        pathogen_name (str): Pathogen name

    Returns:
        list: Case data
    """

    try:
        credentials = get_client_credentials()
        channel = grpc.secure_channel(f"{GRPC_HOST}:{GRPC_PORT}", credentials)
        client = CasesStub(channel)
        response = client.GetCases(CasesRequest(pathogen=pathogen_name))
    except Exception as exc:
        print(f"Could not make gRPC request: {exc}")
        raise

    return MessageToDict(response, preserving_proto_field_name=True).get("cases")


def reset_database() -> None:
    """
    Delete all rows from a database table
    """

    try:
        with psycopg.connect(DB_CONNECTION) as conn:
            with conn.cursor() as cur:
                cur.execute(f'DELETE FROM "{TABLE_NAME}"')
                conn.commit()
    except Exception:
        pytest.fail("Could not delete cases from database")
    finally:
        conn.close()


def test_client_consumes_messages():
    """
    The client should consume messages when subscribed to a topic
    """

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=AMQP_HOST))
    channel = connection.channel()
    channel.exchange_declare(exchange=TOPIC_A_EXCHANGE, exchange_type="topic")
    channel.confirm_delivery()

    try:
        channel.basic_publish(
            exchange=TOPIC_A_EXCHANGE,
            routing_key=TOPIC_A_ROUTE,
            body=json.dumps({"info": "There's a horse in the hospital"}),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=pika.DeliveryMode.Transient,
            ),
            mandatory=True,
        )
        print("Message was published")
    except pika.exceptions.UnroutableError:
        pytest.fail("Message was returned")


def test_client_serves_cases_from_db():
    """
    The client should provide access to cases from its database
    """

    expected = [TEST_CASE]
    insert_case(PATHOGEN_A, expected[0])
    actual = get_cases(PATHOGEN_A)
    assert expected == actual


def test_client_estimates_rt():
    """
    The client should provide R(t) estimate data
    """

    location_information = "USA"
    outcome = "recovered"
    hospitalized = "Y"

    start_date = "01-01-2023"
    end_date = "01-31-2023"
    q_lower = 0.3
    q_upper = 0.7
    gt_distribution = [0.25, 0.5, 0.25]
    delay_distribution = [0.1, 0.5, 0.4]

    values = []

    for day in range(1, 31):
        date_confirmation = f"01-{day}-2023"
        for _ in range(50):
            values.append(
                (
                    location_information,
                    outcome,
                    date_confirmation,
                    hospitalized,
                    PATHOGEN_A,
                )
            )

    try:
        with psycopg.connect(DB_CONNECTION) as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    f"""INSERT INTO "{TABLE_NAME}" (location_information, outcome, date_confirmation, hospitalized, pathogen) VALUES (%s, %s, %s, %s, %s)""",
                    values,
                )
                conn.commit()
    except Exception:
        pytest.fail("Could not add case to database")
    finally:
        conn.close()

    # FIXME: asynchronous call/response

    try:
        credentials = get_client_credentials()
        channel = grpc.secure_channel(f"{GRPC_HOST}:{GRPC_PORT}", credentials)
        client = RtEstimatesStub(channel)
        request = RtEstimateRequest(
            start_date=start_date,
            end_date=end_date,
            q_lower=q_lower,
            q_upper=q_upper,
            gt_distribution=gt_distribution,
            delay_distribution=delay_distribution,
            pathogen=PATHOGEN_A,
        )
        response = client.GetRtEstimates(request)
    except Exception:
        pytest.fail("Could not make gRPC request")

    rt_estimate = MessageToDict(response, preserving_proto_field_name=True).get(
        "estimates"
    )

    assert rt_estimate

    reset_database()


def test_multiple_outbreaks():
    """
    The client should support case data for multiple pathogens
    """

    for pathogen_name in PATHOGENS:
        TEST_CASE["pathogen"] = pathogen_name
        expected = [TEST_CASE]
        insert_case(pathogen_name, expected[0])

        actual = get_cases(pathogen_name)
        assert expected == actual

        reset_database()


def test_schema_violations():
    """
    The client should error when requested data violates the G.h schema
    """

    cases = [
        {
            "location_information": "USA",
            "outcome": "A-OK",
            "pathogen": PATHOGEN_A,
            "date_confirmation": "Wednesday",
            "hospitalized": "Sure",
        }
    ]

    insert_case(PATHOGEN_A, cases[0])

    with pytest.raises(grpc._channel._InactiveRpcError):
        _ = get_cases(PATHOGEN_A)

    reset_database()


def test_idle_status():
    """
    The partner should return an idle status when idle
    """

    response = requests.get(f"http://partner_service:{FLASK_PORT}/status")
    assert response.json().get("status") == "idle"
