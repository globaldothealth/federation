"""
Mock partner gRPC service for local development and testing
"""

from collections.abc import Callable
from concurrent import futures
import logging
import os
from typing import Any

import boto3
import cognitojwt
from cryptography.hazmat.primitives import serialization
import grpc
from grpc_interceptor import ServerInterceptor
from grpc_interceptor.exceptions import GrpcException

from cases_pb2 import Case, CasesRequest, CasesResponse
from cases_pb2_grpc import add_CasesServicer_to_server, CasesServicer
from rt_estimate_pb2 import RtEstimate, RtEstimateRequest, RtEstimateResponse
from rt_estimate_pb2_grpc import add_RtEstimatesServicer_to_server, RtEstimatesServicer
from constants import LOCALSTACK_URL, AWS_REGION, PATHOGEN_A
from util import setup_logger


COGNITO_CLIENT = boto3.client(
    "cognito-idp", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)
SECRETS_CLIENT = boto3.client(
    "secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)
ACM_CLIENT = boto3.client("acm", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)

CERT_DOMAIN_NAME = os.environ.get("ACM_CERT_DOMAIN_NAME", "fake_grpc_server")
DECRYPTION_PASSPHRASE = os.environ.get("DECRYPTION_PASSPHRASE", "foobar")

JWKS_HOST = os.environ.get("JWKS_HOST")
JWKS_FILE = os.environ.get("JWKS_FILE")


def get_server_credentials(certificate_arn: str):
    logging.info("Getting server credentials")
    passphrase = bytes(DECRYPTION_PASSPHRASE, encoding="utf8")
    response = ACM_CLIENT.export_certificate(
        CertificateArn=certificate_arn, Passphrase=passphrase
    )

    # Not the chain gRPC wants, but this works.
    # See https://groups.google.com/g/grpc-io/c/pJnoc_MHkfc?pli=1
    certificate = bytes(response.get("Certificate"), encoding="utf8")
    encrypted_private_key = bytes(response.get("PrivateKey"), encoding="utf8")

    pem_private_key = serialization.load_pem_private_key(
        encrypted_private_key, passphrase
    )
    private_key = pem_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return grpc.ssl_server_credentials(((private_key, certificate),))


def get_certificate_arn() -> str:
    logging.info("Getting certs from AWS")
    response = ACM_CLIENT.list_certificates()
    certificates_list = response.get("CertificateSummaryList", [])
    for certificate in certificates_list:
        if certificate.get("DomainName") == CERT_DOMAIN_NAME:
            return certificate.get("CertificateArn")
    raise Exception(f"No certificate found for {CERT_DOMAIN_NAME}")


class CasesService(CasesServicer):

    """
    Service for case data
    """

    def GetCases(self, request: CasesRequest, context: object) -> CasesResponse:
        """
        Get case data

        Args:
            request (CasesRequest): A request for case data
            context (grpc._server._Context): Context for request

        Returns:
            CasesResponse: A response containing case data
        """

        cases = [
            Case(
                id=0,
                location_information="USA",
                outcome="Something",
                pathogen=PATHOGEN_A,
            )
        ]
        return CasesResponse(cases=cases)


class RtEstimateService(RtEstimatesServicer):

    """
    Service for R(t) estimate data
    """

    def GetRtEstimates(
        self, request: RtEstimateRequest, context: object
    ) -> RtEstimateResponse:
        """
        Get R(t) estimate data

        Args:
            request (RtEstimateRequest): A request for R(t) estimate data
            context (grpc._server._Context): Context for request

        Returns:
            RtEstimateResponse: A response containing R(t) estimate data
        """

        rt_estimates = [
            RtEstimate(
                date="foo",
                cases=str(42),
                r_mean=str(0.4),
                r_var=str(0.2),
                q_lower=str(0.1),
                q_upper=str(0.9),
            )
        ]
        return RtEstimateResponse(estimates=rt_estimates)


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
            logging.debug(f"Metadata: {metadata}")
            validate_jwt(metadata)
            return method(request, context)
        except GrpcException as e:
            context.set_code(e.status_code)
            context.set_details(e.details)
            raise


def serve():
    """
    Serve gRPC
    """

    setup_logger()
    logging.info("Configuring gRPC server")
    certificate_arn = get_certificate_arn()
    server_credentials = get_server_credentials(certificate_arn)

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[JWTValidationInterceptor()],
    )

    add_CasesServicer_to_server(CasesService(), server)
    add_RtEstimatesServicer_to_server(RtEstimateService(), server)

    server.add_secure_port("[::]:50051", server_credentials)
    logging.info("Starting gRPC server")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
