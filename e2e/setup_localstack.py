"""
Setup localstack for end-to-end testing
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
S3_CLIENT = boto3.client("s3", endpoint_url=LOCALSTACK_URL)
SECRETS_CLIENT = boto3.client(
    "secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)
ACM_CLIENT = boto3.client("acm", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)

USER_POOL_NAME = os.environ.get("COGNITO_USER_POOL_NAME")
USER_POOL_CLIENT_NAME = os.environ.get("COGNITO_USER_POOL_CLIENT_NAME")

USER_NAME = os.environ.get("COGNITO_USER_NAME")
USER_PASSWORD = os.environ.get("COGNITO_USER_PASSWORD")

S3_A_BUCKET = os.environ.get("S3_A_BUCKET")
S3_B_BUCKET = os.environ.get("S3_B_BUCKET")
S3_C_BUCKET = os.environ.get("S3_C_BUCKET")

PARTNER_A_NAME = os.environ.get("PARTNER_A_NAME")
PARTNER_B_NAME = os.environ.get("PARTNER_B_NAME")
PARTNER_C_NAME = os.environ.get("PARTNER_C_NAME")

PARTNER_NAMES = [PARTNER_A_NAME, PARTNER_B_NAME, PARTNER_C_NAME]

CERT_DOMAIN_NAME_A = os.environ.get("ACM_CERT_DOMAIN_NAME_A", PARTNER_A_NAME)
CERT_DOMAIN_NAME_B = os.environ.get("ACM_CERT_DOMAIN_NAME_B", PARTNER_B_NAME)
CERT_DOMAIN_NAME_C = os.environ.get("ACM_CERT_DOMAIN_NAME_C", PARTNER_C_NAME)

PARTNER_CERT_DOMAINS = [CERT_DOMAIN_NAME_A, CERT_DOMAIN_NAME_B, CERT_DOMAIN_NAME_C]


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
            cognito_status = response.json().get("services", {}).get("cognito-idp")
            acm_status = response.json().get("services", {}).get("acm")
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

    logging.info("Creating AWS Cognito user pool")
    response = COGNITO_CLIENT.create_user_pool(PoolName=USER_POOL_NAME)
    pool_id = response.get("UserPool", {}).get("Id")
    logging.info(f"Created AWS Cognito user pool {pool_id}")
    logging.info("Creating AWS Cognito user pool client")
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


def bucket_exists(bucket_name: str) -> bool:
    """
    Check whether an S3 bucket exists

    Args:
        bucket_name (str): The name of the S3 bucket

    Returns:
        bool: True if the bucket exists, False if it does not
    """

    response = S3_CLIENT.list_buckets()
    existing_buckets = response.get("Buckets", [])
    for existing_bucket in existing_buckets:
        if bucket_name == existing_bucket.get("Name", ""):
            logging.info(f"Bucket {bucket_name} already exists")
            return True
    return False


def create_buckets() -> None:
    """
    Create an S3 bucket
    """

    for bucket_name in [S3_A_BUCKET, S3_B_BUCKET, S3_C_BUCKET]:
        if bucket_exists(bucket_name):
            continue
        logging.info(f"Creating bucket {bucket_name}")
        S3_CLIENT.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )


def setup_secrets_manager() -> None:
    """
    Setup AWS Secrets Manager resources
    """

    for name in PARTNER_NAMES:
        logging.info(f"Creating secret: {name}_api_key")
        response = SECRETS_CLIENT.get_random_password(ExcludePunctuation=True)
        password = response.get("RandomPassword")
        _ = SECRETS_CLIENT.create_secret(
            Name=f"{name}_api_key_password", SecretString=password
        )
        logging.info("Created secret")


def setup_acm() -> None:
    """
    Setup AWS ACM resources
    """

    logging.info("Creating AWS ACM certificates")
    for domain_name in [CERT_DOMAIN_NAME_A, CERT_DOMAIN_NAME_B, CERT_DOMAIN_NAME_C]:
        logging.info(f"Created certificate for domain {domain_name}")
        _ = ACM_CLIENT.request_certificate(DomainName=domain_name)
        logging.info(f"Created certificate for domain {domain_name}")


if __name__ == "__main__":
    setup_logger()
    wait_for_localstack()
    setup_cognito()
    create_buckets()
    setup_secrets_manager()
    setup_acm()
