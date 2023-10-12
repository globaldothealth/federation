"""
Partner gRPC server
"""

from collections.abc import Callable
from concurrent import futures
from ctypes import c_int
from datetime import datetime
import logging
import multiprocessing
import os
import sys
from typing import Any

import boto3
import cognitojwt
from cryptography.fernet import Fernet
from flask import Flask
from flask.views import View
from google.protobuf.json_format import MessageToDict, ParseDict
import grpc
from grpc_interceptor import ServerInterceptor
from grpc_interceptor.exceptions import GrpcException
import pika
import psycopg
from psycopg.rows import dict_row

from cases_pb2 import Case, CasesResponse
from cases_pb2_grpc import add_CasesServicer_to_server, CasesServicer
from rt_estimate_pb2 import RtEstimate, RtEstimateResponse
from rt_estimate_pb2_grpc import add_RtEstimatesServicer_to_server, RtEstimatesServicer
from run_epyestim import estimate_rt
from constants import (
    LOCALSTACK_URL,
    AWS_REGION,
    AMQP_HOST,
    USER_NAME,
    USER_PASSWORD,
    JWKS_HOST,
    JWKS_FILE,
    DB_CONNECTION,
    TABLE_NAME,
    PARTNER_NAME,
    CASE_FIELDS,
    FIELD_VALIDATIONS,
    DATE_FIELDS,
    PATHOGEN_A,
    PATHOGEN_B,
    PATHOGEN_EXCHANGES,
    PATHOGEN_QUEUES,
    PATHOGEN_ROUTES,
)


# FIXME: non-localstack clients
COGNITO_CLIENT = boto3.client(
    "cognito-idp", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)
SECRETS_CLIENT = boto3.client(
    "secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = os.environ.get("FLASK_PORT", 5000)
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", False)

FLASK_APP = Flask(__name__)


def setup_logger():
    """
    Set up the logger to stream at the desired level
    """

    h = logging.StreamHandler(sys.stdout)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(h)
    rootLogger.setLevel(logging.DEBUG)


def consume_messages(topic_exchange: str, topic_queue: str, topic_route: str):
    """
    Consume messages for a particular subscription

    Args:
        topic_exchange (str): Where the publisher sends a message
        topic_queue (str): Where the exchange sends a message
        topic_route (str): Where the queue sends a message
    """

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=AMQP_HOST))
    channel = connection.channel()

    # G.h should create the topic exchange
    # Needs to persist if the thread stops
    channel.exchange_declare(exchange=topic_exchange, exchange_type="topic")
    result = channel.queue_declare(queue=topic_queue, durable=True)
    queue_name = result.method.queue

    logging.info(f"Created queue {queue_name}")

    channel.queue_bind(
        exchange=topic_exchange, queue=queue_name, routing_key=topic_route
    )

    def callback(ch, method, properties, body):
        logging.info(" [x] Received %r" % body)

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    logging.info(" [*] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()


def get_client_id() -> str:
    """
    Get a client ID from AWS Cognito

    Returns:
        str: The client ID
    """
    response = COGNITO_CLIENT.list_user_pools(MaxResults=1)
    pool_id = response.get("UserPools", [])[0].get("Id")

    response = COGNITO_CLIENT.list_user_pool_clients(UserPoolId=pool_id, MaxResults=1)
    client_id = response.get("UserPoolClients")[0].get("ClientId")

    return client_id


def get_jwt(client_id: str) -> str:
    """
    Get a client's JWT from AWS Cognito

    Args:
        client_id (str): The client with a JWT

    Returns:
        str: The JWT
    """
    response = COGNITO_CLIENT.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": USER_NAME, "PASSWORD": USER_PASSWORD},
        ClientId=client_id,
    )

    token = response.get("AuthenticationResult", {}).get("AccessToken")
    return token


def get_db_cases(pathogen_name: str) -> list[dict]:
    """
    Get cases from the database

    Args:
        pathogen_name (str): The name of the pathogen

    Returns:
        list[dict]: Case data
    """
    logging.debug(f"Getting cases from database for pathogen: {pathogen_name}")
    results = []
    try:
        with psycopg.connect(DB_CONNECTION, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT * FROM "{TABLE_NAME}" WHERE pathogen = '{pathogen_name}';"""
                )
                results = cur.fetchall()
    except Exception:
        logging.exception("Could not get cases from database")
        raise
    finally:
        conn.close()

    logging.debug(f"Got cases from database: {results}")
    return results


class CountActiveChannelsInterceptor(ServerInterceptor):

    """
    Interceptor to find idle status by counting the number of active gRPC channels

    Attributes:
        num_active_channels (multiprocessing.Value): The number of active gRPC channels
    """

    def __init__(self, num_active_channels: multiprocessing.Value):
        """
        Constructor for channel count interceptor

        Args:
            num_active_channels (multiprocessing.Value): The number of active gRPC channels
        """

        super().__init__()
        self.num_active_channels = num_active_channels

    def intercept(
        self,
        method: Callable,
        request: Any,
        context: grpc.ServicerContext,
        method_name: str,
    ) -> Any:
        """
        Keep a running count of the number of active gRPC channels

        Args:
            method (Callable): The RPC method
            request (Any): The gRPC request
            context (grpc.ServicerContext): The context
            method_name (str): The name of the gRPC method
        """
        response = None
        try:
            with self.num_active_channels.get_lock():
                self.num_active_channels.value += 1
                logging.debug(
                    f"increment num_active_channels: {self.num_active_channels.value}"
                )
            response = method(request, context)
            return response
        except GrpcException as e:
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise
        finally:
            logging.info("End first interceptor")
            with self.num_active_channels.get_lock():
                self.num_active_channels.value -= 1
                logging.debug(
                    f"decrement num_active_channels: {self.num_active_channels.value}"
                )


class JWTValidationInterceptor(ServerInterceptor):

    """
    Interceptor for JWT validation
    """

    def intercept(
        self,
        method: Callable,
        request: Any,
        context: grpc.ServicerContext,
        method_name: str,
    ) -> Any:
        """
        Intercept the request and validate the JWT

        Args:
            method (Callable): The RPC method
            request (Any): The gRPC request
            context (grpc.ServicerContext): The context
            method_name (str): The name of the gRPC method
        """

        try:
            metadata = dict(context.invocation_metadata())
            validate_jwt(metadata)
            return method(request, context)
        except GrpcException as e:
            logging.exception("gRPC exception during JWT validation")
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise
        except Exception as e:
            logging.exception("Something went wrong during JWT validation")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise


def validate_jwt(metadata: dict) -> None:
    """
    Validate a JWT

    Args:
        metadata (dict): Request metadata, including JWT

    Raises:
        GrpcException: The JWT should validate
    """

    logging.debug("Validating JWT")
    auth_header = metadata.get("authorization")
    status_code = grpc.StatusCode.UNAUTHENTICATED
    details = ""
    if not auth_header:
        details = "No authorization header in request"
        raise GrpcException(status_code=status_code, details=details)
    token = auth_header.split()[-1]

    # FIXME: matching
    response = COGNITO_CLIENT.list_user_pools(MaxResults=1)
    pool_id = response.get("UserPools", [])[0].get("Id")

    # FIXME: Use only for localstack
    jwks_url = f"{JWKS_HOST}/{pool_id}/{JWKS_FILE}"
    logging.debug(f"Using JWKS at {jwks_url}")
    os.environ["AWS_COGNITO_JWKS_PATH"] = jwks_url
    try:
        _ = cognitojwt.decode(token, AWS_REGION, pool_id)
    except Exception:
        details = "JWT validation failed"
        logging.exception(details)
        raise GrpcException(status_code=status_code, details=details)


def get_encryption_key() -> bytes:
    """
    Get the encryption key

    Returns:
        bytes: The encryption key
    """

    response = SECRETS_CLIENT.get_secret_value(SecretId=PARTNER_NAME)
    return response.get("SecretBinary", b"")


class CaseDataValidationInterceptor(ServerInterceptor):

    """
    Interceptor for case data validation
    """

    def intercept(
        self,
        method: Callable,
        request: Any,
        context: grpc.ServicerContext,
        method_name: str,
    ) -> Any:
        """
        Validate case data contained in response

        Args:
            method (Callable): The RPC method
            request (Any): The gRPC request
            context (grpc.ServicerContext): The context
            method_name (str): The name of the gRPC method
        """

        try:
            logging.debug("Validating response data schema conformance")
            response = method(request, context)
            response_type = type(response)
            logging.info(f"Response type: {response_type}")
            if response_type != CasesResponse:
                return method(request, context)
            dict_response = MessageToDict(response, preserving_proto_field_name=True)
            for _, data in dict_response.items():
                for elem in data:
                    for k, v in elem.items():
                        if k not in CASE_FIELDS:
                            raise AttributeError(f"Field {k} not a valid case field")

                        if k in FIELD_VALIDATIONS:
                            # if k is a date-based field and v not m-d-Y, raise
                            if k in DATE_FIELDS:
                                try:
                                    datetime.strptime(v, FIELD_VALIDATIONS[k])
                                except ValueError:
                                    raise
                            # if k has an enum and v not in enum, raise
                            else:
                                valid_values = FIELD_VALIDATIONS[k]
                                if v not in valid_values:
                                    raise ValueError(
                                        f"Field {k} is set to {v} but requires a value in {valid_values}."
                                    )
            logging.debug("Case data validated")
            return method(request, context)
        except GrpcException as e:
            logging.exception("gRPC exception during data validation")
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise
        except Exception:
            logging.exception("Something went wrong during case data validation")
            raise


# The result of not using TLS
class EncryptionInterceptor(ServerInterceptor):

    """
    Interceptor for encrypting data
    """

    def intercept(
        self,
        method: Callable,
        request: Any,
        context: grpc.ServicerContext,
        method_name: str,
    ) -> Any:
        """
        Encrypt data

        Args:
            method (Callable): The RPC method
            request (Any): The gRPC request
            context (grpc.ServicerContext): The context
            method_name (str): The name of the gRPC method
        """
        try:
            logging.debug("Encrypting response")
            response = method(request, context)

            key = get_encryption_key()
            fernet = Fernet(key)

            dict_response = MessageToDict(response)

            for _, data in dict_response.items():
                for elem in data:
                    for k, v in elem.items():
                        elem[k] = fernet.encrypt(str(v).encode()).decode()

            response_type = type(response)
            response = ParseDict(dict_response, response_type())
            logging.debug("Response encrypted")
            return response
        except GrpcException as e:
            logging.exception("gRPC exception during encryption")
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise
        except Exception:
            logging.exception("Something went wrong during encryption")
            raise


class CasesService(CasesServicer):

    """
    Service for case data
    """

    def GetCases(self, request, context):
        """
        Get case data

        Args:
            request (CasesRequest): A request for case data
            context (grpc._server._Context): Context for request

        Returns:
            CasesResponse: A response containing case data
        """

        logging.debug(f"Getting cases for pathogen {request.pathogen}")
        db_cases = get_db_cases(request.pathogen)
        cases = [
            Case(
                location_information=case["location_information"],
                outcome=case["outcome"],
                date_confirmation=case["date_confirmation"],
                hospitalized=case["hospitalized"],
                pathogen=request.pathogen,
            )
            for case in db_cases
        ]
        return CasesResponse(cases=cases)


class RtEstimateService(RtEstimatesServicer):

    """
    Service for R(t) estimate data
    """

    def GetRtEstimates(self, request, context):
        """
        Get R(t) estimate data

        Args:
            request (RtEstimateRequest): A request for R(t) estimate data
            context (grpc._server._Context): Context for request

        Returns:
            RtEstimateResponse: A response containing R(t) estimate data
        """

        logging.debug(f"Getting R(t) estimates for pathogen {request.pathogen}")
        db_cases = get_db_cases(request.pathogen)
        date_range = [request.start_date, request.end_date]
        quantiles = [request.q_lower, request.q_upper]
        gt_dist = request.gt_distribution
        delay_dist = request.delay_distribution
        results = estimate_rt(db_cases, date_range, quantiles, gt_dist, delay_dist)
        rt_estimates = [
            RtEstimate(
                date=estimate["date"].strftime("%m-%d-%Y"),
                cases=str(int(estimate["cases"])),
                r_mean=str(estimate["R_mean"]),
                r_var=str(estimate["R_var"]),
                q_lower=str(estimate["q_lower"]),
                q_upper=str(estimate["q_upper"]),
            )
            for estimate in results
        ]
        return RtEstimateResponse(estimates=rt_estimates)


class StatusView(View):

    """
    View for gRPC status (busy/idle)

    Attributes:
        num_active_channels (TYPE): Description
        status (str): Description
    """

    def __init__(self, num_active_channels: multiprocessing.Value):
        """Summary

        Args:
            num_active_channels (multiprocessing.Value): The number of active gRPC channels
        """

        self.num_active_channels = num_active_channels
        self.status = "idle"

    def dispatch_request(self) -> tuple[str, int]:
        """
        Get the gRPC status based on the number of active channels

        Returns:
            tuple: Message + HTTP status code
        """

        with self.num_active_channels.get_lock():
            logging.info(
                f"status num_active_channels: {self.num_active_channels.value}"
            )
            self.status = "idle" if self.num_active_channels.value == 0 else "busy"
        return {"status": self.status}, 200


def make_grpc_server(max_workers: int, interceptors: list) -> grpc.Server:
    """
    Create the gRPC server

    Args:
        max_workers (int): The maximum number threads
        interceptors (list): Interceptors to use before handling requests or sending responses

    Returns:
        grpc.Server: The gRPC server
    """

    return grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers), interceptors=interceptors
    )


def serve_grpc(server: grpc.Server):
    """
    Start and run the gRPC server

    Args:
        server (grpc.Server): The gRPC server
    """
    logging.info("Configuring gRPC server")

    add_CasesServicer_to_server(CasesService(), server)
    add_RtEstimatesServicer_to_server(RtEstimateService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    logging.info("Serving gRPC")
    server.wait_for_termination()


def run_flask_server():
    """
    Run a Flask server (used for sharing idle/busy state)
    """

    FLASK_APP.run(FLASK_HOST, FLASK_PORT, debug=FLASK_DEBUG)


if __name__ == "__main__":
    setup_logger()
    logging.info("Starting client")

    num_active_channels = multiprocessing.Value(c_int, 0)
    max_workers = 10
    interceptors = [
        EncryptionInterceptor(),
        CaseDataValidationInterceptor(),
        JWTValidationInterceptor(),
        CountActiveChannelsInterceptor(num_active_channels),
    ]

    try:
        amqp_a_args = (
            PATHOGEN_EXCHANGES.get(PATHOGEN_A),
            PATHOGEN_QUEUES.get(PATHOGEN_A),
            PATHOGEN_ROUTES.get(PATHOGEN_A),
        )
        amqp_b_args = (
            PATHOGEN_EXCHANGES.get(PATHOGEN_B),
            PATHOGEN_QUEUES.get(PATHOGEN_B),
            PATHOGEN_ROUTES.get(PATHOGEN_B),
        )
        amqp_a_consumer_process = multiprocessing.Process(
            target=consume_messages, args=amqp_a_args
        )
        amqp_b_consumer_process = multiprocessing.Process(
            target=consume_messages, args=amqp_b_args
        )
        rpc_server = make_grpc_server(max_workers, interceptors)
        grpc_server_process = multiprocessing.Process(
            target=serve_grpc, args=(rpc_server,)
        )
        FLASK_APP.add_url_rule(
            "/status", view_func=StatusView.as_view("status", num_active_channels)
        )
        flask_server_process = multiprocessing.Process(target=run_flask_server)
        amqp_a_consumer_process.start()
        amqp_b_consumer_process.start()
        grpc_server_process.start()
        flask_server_process.start()
    except KeyboardInterrupt:
        logging.info("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
