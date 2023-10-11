"""
Setup localstack for local development and testing
"""

import logging
import os
import sys
from time import sleep

import boto3
import requests


LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION")

COGNITO_CLIENT = boto3.client(
    "cognito-idp", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)
SECRETS_CLIENT = boto3.client(
    "secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)
ACM_CLIENT = boto3.client("acm", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)

USER_POOL_NAME = os.environ.get("COGNITO_USER_POOL_NAME")
USER_POOL_CLIENT_NAME = os.environ.get("COGNITO_USER_POOL_CLIENT_NAME")

USER_NAME = os.environ.get("COGNITO_USER_NAME")
USER_PASSWORD = os.environ.get("COGNITO_USER_PASSWORD")

PARTNER_NAME = os.environ.get("PARTNER_NAME")

CERT_DOMAIN_NAME = os.environ.get("ACM_CERT_DOMAIN_NAME")


def setup_logger() -> None:
    """
    Set up the logger to stream at the desired level
    """

    h = logging.StreamHandler(sys.stdout)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(h)
    rootLogger.setLevel(logging.DEBUG)


def wait_for_localstack() -> None:
    """
    Wait for localstack services to be ready

    Raises:
        Exception: If localstack services are not available in the expected time
    """

    logging.info("Waiting for localstack")
    healthcheck_url = "".join([LOCALSTACK_URL, "/_localstack/health"])
    counter = 0
    while counter < 42:
        try:
            response = requests.get(healthcheck_url)
            acm_status = response.json().get("services", {}).get("acm")
            cognito_status = response.json().get("services", {}).get("cognito-idp")
            if acm_status == "running" and cognito_status == "running":
                return
            # Lazy loading
            _ = ACM_CLIENT.list_certificates()
            _ = COGNITO_CLIENT.list_user_pools(MaxResults=1)
        except requests.exceptions.ConnectionError:
            pass
        counter += 1
        sleep(5)
    raise Exception("Localstack not available")


def setup_cognito() -> None:
    """
    Setup AWS Cognito resources
    """

    logging.info(f"Creating AWS Cognito user pool {USER_POOL_NAME}")
    response = COGNITO_CLIENT.create_user_pool(PoolName=USER_POOL_NAME)
    pool_id = response.get("UserPool", {}).get("Id")
    logging.info(f"Created AWS Cognito user pool {pool_id}")
    logging.info(f"Creating AWS Cognito user pool client {USER_POOL_CLIENT_NAME}")
    response = COGNITO_CLIENT.create_user_pool_client(
        UserPoolId=pool_id, ClientName=USER_POOL_CLIENT_NAME
    )
    logging.info("Created AWS Cognito user pool client")
    logging.info(f"Creating user {USER_NAME}")
    response = COGNITO_CLIENT.admin_create_user(UserPoolId=pool_id, Username=USER_NAME)
    logging.info("Created user")
    logging.info(f"Setting user {USER_NAME} password to {USER_PASSWORD}")
    COGNITO_CLIENT.admin_set_user_password(
        UserPoolId=pool_id, Username=USER_NAME, Password=USER_PASSWORD, Permanent=True
    )
    logging.info("Set user password")


def setup_secrets_manager() -> None:
    """
    Setup AWS Secrets Manager resources
    """

    logging.info(f"Creating secret: {PARTNER_NAME}_api_key")
    response = SECRETS_CLIENT.get_random_password(ExcludePunctuation=True)
    password = response.get("RandomPassword")
    _ = SECRETS_CLIENT.create_secret(
        Name=f"{PARTNER_NAME}_api_key_password", SecretString=password
    )
    logging.info("Created secret")


def setup_acm() -> None:
    """
    Setup AWS ACM resources
    """

    logging.info("Creating AWS ACM certificate")
    _ = ACM_CLIENT.request_certificate(DomainName=CERT_DOMAIN_NAME)
    logging.info(f"Created certificate for domain {CERT_DOMAIN_NAME}")


if __name__ == "__main__":
    setup_logger()
    wait_for_localstack()
    setup_acm()
    setup_cognito()
    setup_secrets_manager()
