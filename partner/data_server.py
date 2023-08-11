from collections.abc import Callable
from concurrent import futures
from datetime import datetime
import logging
import multiprocessing
import os
import sys
from typing import Any

import boto3
import cognitojwt
from cryptography.fernet import Fernet
from google.protobuf.json_format import MessageToDict, ParseDict
import grpc
from grpc_interceptor import ServerInterceptor
from grpc_interceptor.exceptions import GrpcException
import pika
import psycopg
from psycopg.rows import dict_row

from cases_pb2 import Case, CasesResponse
from cases_pb2_grpc import (
    add_CasesServicer_to_server,
    CasesServicer
)
from rt_estimate_pb2 import RtEstimate, RtEstimateResponse
from rt_estimate_pb2_grpc import (
    add_RtEstimatesServicer_to_server,
    RtEstimatesServicer
)
from run_epyestim import estimate_rt
from constants import (LOCALSTACK_URL, AWS_REGION, AMQP_HOST, USER_NAME, USER_PASSWORD,
    JWKS_HOST, JWKS_FILE, DB_CONNECTION, TABLE_NAME, PARTNER_NAME, CASE_FIELDS, FIELD_VALIDATIONS,
    DATE_FIELDS, PATHOGEN_A, PATHOGEN_B, PATHOGEN_EXCHANGES, PATHOGEN_QUEUES, PATHOGEN_ROUTES
)


# FIXME: non-localstack clients
COGNITO_CLIENT = boto3.client("cognito-idp", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)
SECRETS_CLIENT = boto3.client("secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)


def setup_logger():
    h = logging.StreamHandler(sys.stdout)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(h)
    rootLogger.setLevel(logging.DEBUG)


def consume_messages(topic_exchange: str, topic_queue: str, topic_route: str):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=AMQP_HOST))
    channel = connection.channel()

    # G.h should create the topic exchange
    # Needs to persist if the thread stops
    channel.exchange_declare(exchange=topic_exchange, exchange_type="topic")
    result = channel.queue_declare(queue=topic_queue, durable=True)
    queue_name = result.method.queue

    logging.info(f"Created queue {queue_name}")

    channel.queue_bind(
        exchange=topic_exchange, queue=queue_name, routing_key=topic_route)

    def callback(ch, method, properties, body):
        logging.info(" [x] Received %r" % body)

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    logging.info(" [*] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()


def get_client_id() -> str:
    response = COGNITO_CLIENT.list_user_pools(
        MaxResults=1
    )
    pool_id = response.get("UserPools", [])[0].get("Id")

    response = COGNITO_CLIENT.list_user_pool_clients(
        UserPoolId=pool_id,
        MaxResults=1
    )
    client_id = response.get("UserPoolClients")[0].get("ClientId")

    return client_id


def get_jwt(client_id: str) -> str:
    response = COGNITO_CLIENT.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": USER_NAME,
            "PASSWORD": USER_PASSWORD
        },
        ClientId=client_id
    )

    token = response.get("AuthenticationResult", {}).get("AccessToken")
    return token


def get_db_cases(pathogen_name: str) -> list[dict]:
    logging.debug(f"Getting cases from database for pathogen: {pathogen_name}")
    results = []
    try:
        with psycopg.connect(DB_CONNECTION, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(f"""SELECT * FROM "{TABLE_NAME}" WHERE pathogen = '{pathogen_name}';""")
                results = cur.fetchall()
    except Exception:
        logging.exception("Could not get cases from database")
        raise
    finally:
        conn.close()

    logging.debug(f"Got cases from database: {results}")
    return results


def validate_jwt(metadata: dict) -> None:
    logging.debug("Validating JWT")
    auth_header = metadata.get("authorization")
    status_code = grpc.StatusCode.UNAUTHENTICATED
    details = ""
    if not auth_header:
        details = "No authorization header in request"
        raise GrpcException(status_code=status_code, details=details)
    token = auth_header.split()[-1]

    # FIXME: matching
    response = COGNITO_CLIENT.list_user_pools(
        MaxResults=1
    )
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


class JWTValidationInterceptor(ServerInterceptor):
    def intercept(
        self,
        method: Callable,
        request: Any,
        context: grpc.ServicerContext,
        method_name: str,
    ) -> Any:
        try:
            metadata = dict(context.invocation_metadata())
            validate_jwt(metadata)
            return method(request, context)
        except GrpcException as e:
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            raise


def get_encryption_key():
    response = SECRETS_CLIENT.get_secret_value(SecretId=PARTNER_NAME)
    return response.get("SecretBinary", b"")


class CaseDataValidationInterceptor(ServerInterceptor):
    def intercept(
        self,
        method: Callable,
        request: Any,
        context: grpc.ServicerContext,
        method_name: str,
    ) -> Any:
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
                                    raise ValueError(f"Field {k} is set to {v} but requires a value in {valid_values}.")
            logging.debug("Case data validated")
            return method(request, context)
        except GrpcException as e:
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise
        except Exception as e:
            logging.exception("Something went wrong during case data validation")
            raise


# The result of not using TLS
class EncryptionInterceptor(ServerInterceptor):
    def intercept(
        self,
        method: Callable,
        request: Any,
        context: grpc.ServicerContext,
        method_name: str,
    ) -> Any:
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
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise
        except Exception as e:
            logging.exception("Something went wrong during encryption")
            raise


class CasesService(CasesServicer):

    def GetCases(self, request, context):
        logging.debug(f"Getting cases for pathogen {request.pathogen}")
        db_cases = get_db_cases(request.pathogen)
        cases = [
            Case(
                location_information=case["location_information"],
                outcome=case["outcome"],
                date_confirmation=case["date_confirmation"],
                hospitalized=case["hospitalized"],
                pathogen=request.pathogen
            )
            for case in db_cases
        ]
        return CasesResponse(cases=cases)


class RtEstimateService(RtEstimatesServicer):

    def GetRtEstimates(self, request, context):
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
                q_upper=str(estimate["q_upper"])
            )
            for estimate in results
        ]
        return RtEstimateResponse(estimates=rt_estimates)


def serve_grpc():
    logging.info("Configuring gRPC server")

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[EncryptionInterceptor(), CaseDataValidationInterceptor(), JWTValidationInterceptor()]
    )

    add_CasesServicer_to_server(
        CasesService(), server
    )
    add_RtEstimatesServicer_to_server(
        RtEstimateService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    logging.info("Serving gRPC")
    server.wait_for_termination()


if __name__ == "__main__":
    setup_logger()
    logging.info("Starting client")
    try:
        amqp_a_args = (PATHOGEN_EXCHANGES.get(PATHOGEN_A), PATHOGEN_QUEUES.get(PATHOGEN_A), PATHOGEN_ROUTES.get(PATHOGEN_A),)
        amqp_b_args = (PATHOGEN_EXCHANGES.get(PATHOGEN_B), PATHOGEN_QUEUES.get(PATHOGEN_B), PATHOGEN_ROUTES.get(PATHOGEN_B),)
        amqp_a_consumer = multiprocessing.Process(target=consume_messages, args=amqp_a_args)
        amqp_b_consumer = multiprocessing.Process(target=consume_messages, args=amqp_b_args)
        grpc_server = multiprocessing.Process(target=serve_grpc)
        amqp_a_consumer.start()
        amqp_b_consumer.start()
        grpc_server.start()
    except KeyboardInterrupt:
        logging.info("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
