"""
Partner client for Global.health server, sends requests for work
"""

import logging
import os

import boto3
import requests
from requests.auth import HTTPBasicAuth

LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION")
SECRETS_CLIENT = boto3.client(
    "secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
)

PARTNER_NAME = os.environ.get("PARTNER_NAME")

GH_WORK_REQUEST_URL = os.environ.get("GH_WORK_REQUEST_URL")
GH_API_KEY_NAME = f"{PARTNER_NAME}_api_key_password"


def get_api_key() -> str:
    """
    Get the partner API key

    Returns:
        str: The API key
    """
    logging.debug("Getting API key")
    response = SECRETS_CLIENT.get_secret_value(SecretId=GH_API_KEY_NAME)
    return response.get("SecretString")


def update_api_key() -> None:
    """
    Update the partner API key
    """

    logging.debug("Updating API key")
    response = SECRETS_CLIENT.get_random_password(ExcludePunctuation=True)
    password = response.get("RandomPassword")
    _ = SECRETS_CLIENT.put_secret_value(SecretId=GH_API_KEY_NAME, SecretString=password)
    logging.debug("Updated API key")


def send_work_request(api_key: str, pathogen: str, job: str) -> None:
    """
    Send a request for work to the server

    Args:
        api_key (str): The partner's API key
        pathogen (str): The name of the pathogen
        job (str): The name of the job to do
    """

    logging.debug(f"Sending request: {pathogen}: {job}")
    auth = HTTPBasicAuth(PARTNER_NAME, api_key)
    url = f"{GH_WORK_REQUEST_URL}/{pathogen}/{job}"
    response = requests.get(url, auth=auth)
    logging.debug(
        f"Response status code: {response.status_code}, body: {response.text}"
    )
    update_api_key()
