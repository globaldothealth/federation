"""
Setup localstack for testing G.h system components
"""

import logging
import os
import sys
from time import sleep

import boto3
from cryptography.fernet import Fernet
import requests


LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL")
S3_A_BUCKET = os.environ.get("S3_A_BUCKET")
S3_B_BUCKET = os.environ.get("S3_B_BUCKET")
S3_C_BUCKET = os.environ.get("S3_C_BUCKET")

USER_POOL_NAME = os.environ.get("COGNITO_USER_POOL_NAME")
USER_POOL_CLIENT_NAME = os.environ.get("COGNITO_USER_POOL_CLIENT_NAME")

USER_NAME = os.environ.get("COGNITO_USER_NAME")
USER_PASSWORD = os.environ.get("COGNITO_USER_PASSWORD")

AWS_REGION = os.environ.get("AWS_DEFAULT_REGION")

S3_CLIENT = boto3.client("s3", endpoint_url=LOCALSTACK_URL)
COGNITO_CLIENT = boto3.client(
    "cognito-idp", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)
SECRETS_CLIENT = boto3.client(
    "secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)

PARTNER_A_NAME = os.environ.get("PARTNER_A_NAME")
PARTNER_B_NAME = os.environ.get("PARTNER_B_NAME")
PARTNER_C_NAME = os.environ.get("PARTNER_C_NAME")

PARTNER_NAMES = [PARTNER_A_NAME, PARTNER_B_NAME, PARTNER_C_NAME]


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
            if cognito_status == "running":
                return
            # Lazy loading
            _ = COGNITO_CLIENT.list_user_pools(MaxResults=1)
        except requests.exceptions.ConnectionError:
            pass
        counter += 1
        sleep(5)
    raise Exception("Localstack not available")


def create_bucket(bucket_name: str) -> None:
    """
    Create an S3 bucket

    Args:
        bucket_name (str): Name of the bucket to create
    """

    response = S3_CLIENT.list_buckets()
    existing_buckets = response.get("Buckets", [])
    for existing_bucket in existing_buckets:
        if bucket_name == existing_bucket.get("Name", ""):
            logging.info(f"Bucket {bucket_name} already exists")
            return
    logging.info(f"Creating bucket {bucket_name}")
    S3_CLIENT.create_bucket(
        Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
    )


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


def setup_secrets_manager() -> None:
    """
    Setup AWS Secrets Manager resources
    """

    for name in PARTNER_NAMES:
        logging.info(f"Creating secret: {name}")
        key = Fernet.generate_key()
        _ = SECRETS_CLIENT.create_secret(Name=name, SecretBinary=key)
        logging.info("Created secret")
        logging.info(f"Creating secret: {name}_api_key_password")
        response = SECRETS_CLIENT.get_random_password(ExcludePunctuation=True)
        password = response.get("RandomPassword")
        _ = SECRETS_CLIENT.create_secret(
            Name=f"{name}_api_key_password", SecretString=password
        )
        logging.info("Created secret")


if __name__ == "__main__":
    setup_logger()
    logging.info("Starting script")
    wait_for_localstack()
    create_bucket(S3_A_BUCKET)
    create_bucket(S3_B_BUCKET)
    create_bucket(S3_C_BUCKET)
    setup_cognito()
    setup_secrets_manager()
