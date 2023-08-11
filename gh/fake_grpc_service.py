from collections.abc import Callable
from concurrent import futures
import logging
import os
from typing import Any

import boto3
import cognitojwt
from cryptography.fernet import Fernet
from google.protobuf.json_format import MessageToDict, ParseDict
import grpc
from grpc_interceptor import ServerInterceptor
from grpc_interceptor.exceptions import GrpcException

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
from constants import LOCALSTACK_URL, AWS_REGION, PATHOGEN_A, PARTNER_A_NAME
from util import setup_logger


COGNITO_CLIENT = boto3.client("cognito-idp", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)
SECRETS_CLIENT = boto3.client("secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)

JWKS_HOST = os.environ.get("JWKS_HOST")
JWKS_FILE = os.environ.get("JWKS_FILE")


class CasesService(CasesServicer):

    def GetCases(self, request, context):
        cases = [Case(id=0, location_information="USA", outcome="Something", pathogen=PATHOGEN_A)]
        return CasesResponse(cases=cases)


class RtEstimateService(RtEstimatesServicer):

    def GetRtEstimates(self, request, context):
        rt_estimates = [
            RtEstimate(
                date="foo",
                cases=str(42),
                r_mean=str(0.4),
                r_var=str(0.2),
                q_lower=str(0.1),
                q_upper=str(0.9)
            )
        ]
        return RtEstimateResponse(estimates=rt_estimates)


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
    logging.debug(f"User pools: {response.get('UserPools')}")
    pool_id = response.get("UserPools", [])[0].get("Id")
    logging.debug(f"Pool id: {pool_id}")

    # FIXME: Use only for localstack
    jwks_url = f"{JWKS_HOST}/{pool_id}/{JWKS_FILE}"
    logging.debug(f"Looking up JWK at {jwks_url}")
    os.environ["AWS_COGNITO_JWKS_PATH"] = jwks_url
    try:
        logging.debug("Decoding JWT")
        _ = cognitojwt.decode(token, AWS_REGION, pool_id)
    except Exception:
        details = "JWT validation failed"
        logging.exception(details)
        raise GrpcException(status_code=status_code, details=details)
    logging.debug("JWT validated")


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
            logging.debug(f"Metadata: {metadata}")
            validate_jwt(metadata)
            return method(request, context)
        except GrpcException as e:
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise


def get_encryption_key():
    response = SECRETS_CLIENT.get_secret_value(SecretId=PARTNER_A_NAME)
    return response.get("SecretBinary", b"")


class EncryptionInterceptor(ServerInterceptor):
    def intercept(
        self,
        method: Callable,
        request: Any,
        context: grpc.ServicerContext,
        method_name: str,
    ) -> Any:
        try:
            response = method(request, context)
            response_type = type(response)

            key = get_encryption_key()
            fernet = Fernet(key)

            dict_response = MessageToDict(response)

            for _, data in dict_response.items():
                for elem in data:
                    for k, v in elem.items():
                        elem[k] = fernet.encrypt(str(v).encode()).decode()

            response = ParseDict(dict_response, response_type())
            return response
        except GrpcException as e:
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise


def serve():
    setup_logger()
    logging.info("Configuring gRPC server")
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[EncryptionInterceptor(), JWTValidationInterceptor()]
    )

    add_CasesServicer_to_server(
        CasesService(), server
    )
    add_RtEstimatesServicer_to_server(
        RtEstimateService(), server
    )
    server.add_insecure_port("[::]:50051")
    logging.info("Starting gRPC server")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
