"""
Functions for interacting with AWS resources
"""

import logging
import json

import boto3

from constants import (
    LOCALSTACK_URL,
    AWS_REGION,
    COGNITO_USER_NAME,
    COGNITO_USER_PASSWORD,
)


def get_jwt() -> str:
    """
    Get the G.h JWT

    Returns:
        str: The JWT
    """

    logging.debug("Getting JWT")
    cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)
    if LOCALSTACK_URL:
        logging.debug("Using localstack Cognito service")
        cognito_client = boto3.client(
            "cognito-idp", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
        )

    response = cognito_client.list_user_pools(MaxResults=1)
    logging.debug(f"User pools: {response.get('UserPools')}")
    pool_id = response.get("UserPools", [])[0].get("Id")

    response = cognito_client.list_user_pool_clients(UserPoolId=pool_id, MaxResults=1)
    client_id = response.get("UserPoolClients")[0].get("ClientId")

    response = cognito_client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": COGNITO_USER_NAME,
            "PASSWORD": COGNITO_USER_PASSWORD,
        },
        ClientId=client_id,
    )
    token = response.get("AuthenticationResult", {}).get("AccessToken")

    return token


def get_certificate(domain_name: str) -> bytes:
    logging.info(f"Getting certificate from AWS for domain {domain_name}")
    acm_client = boto3.client("acm", region_name=AWS_REGION)
    if LOCALSTACK_URL:
        acm_client = boto3.client(
            "acm", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
        )
    response = acm_client.list_certificates()
    logging.debug(f"Response: {response}")
    certificates_list = response.get("CertificateSummaryList", [])

    certificate_arn = ""
    for certificate in certificates_list:
        if certificate.get("DomainName") == domain_name:
            certificate_arn = certificate.get("CertificateArn", "")

    if not certificate_arn:
        logging.warning(f"No certificate for domain {domain_name}")
        return b""

    response = acm_client.get_certificate(CertificateArn=certificate_arn)
    cert_str = response.get("Certificate")
    certificate = bytes(cert_str, encoding="utf8")

    return certificate


def store_data_in_s3(data: list, bucket_name: str, file_name: str) -> None:
    """
    Store data in S3

    Args:
        data (list): The data to store
        bucket_name (str): The bucket to store it in
        file_name (str): The name of the file to use in the bucket
    """

    logging.info(f"Storing data in file {file_name} in bucket {bucket_name}")
    try:
        s3 = boto3.client("s3")
        if LOCALSTACK_URL:
            s3 = boto3.client("s3", endpoint_url=LOCALSTACK_URL)
        s3.put_object(Body=json.dumps(data), Bucket=bucket_name, Key=file_name)
    except Exception:
        logging.exception("An error occurred while trying to store data in S3")
        raise
    logging.info("Stored data in S3")


def store_file_in_s3(bucket_name: str, folder: str, file_name: str) -> None:
    """
    Store a file in S3

    Args:
        bucket_name (str): The bucket to store it in
        folder (str): The folder to store it in
        file_name (str): The file to store
    """

    logging.info(f"Storing file {file_name} in bucket {bucket_name}")
    try:
        s3 = boto3.client("s3")
        if LOCALSTACK_URL:
            s3 = boto3.client("s3", endpoint_url=LOCALSTACK_URL)
        s3.upload_file(
            Filename=file_name, Bucket=bucket_name, Key=f"{folder}/{file_name}"
        )
    except Exception:
        logging.exception("An error occurred while trying to store file in S3")
        raise
    logging.info("Stored file in S3")
