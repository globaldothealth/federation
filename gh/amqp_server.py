"""
G.h federated system server
Receives and delegates requests for work, publishes messages about data
"""

import logging
import os

import boto3
from flask import Flask
from flask_httpauth import HTTPBasicAuth
from google.protobuf.json_format import MessageToDict
import pika

from aws import get_jwt, store_data_in_s3, store_file_in_s3, get_certificate
from db import store_data_in_db, get_curation_data
from graphics import create_plot
from grpc_client import get_credentials, get_partner_cases, get_partner_rt_estimates
from util import setup_logger, cleanup_file, clean_cases_data, clean_estimates_data
from constants import (
    PathogenConfig,
    Partner,
    AMQP_CONFIG,
    PATHOGEN_JOBS,
    PATHOGEN_DATA_SOURCES,
    PATHOGENS,
    PATHOGEN_DATA_DESTINATIONS,
    GET_CASES_JOB,
    ESTIMATE_RT_JOB,
    RT_ESTIMATES_FOLDER,
    LOCALSTACK_URL,
    AWS_REGION,
)


APP = Flask(__name__)
AUTH = HTTPBasicAuth()

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = os.environ.get("FLASK_PORT", 5000)
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", False)

AUTO_APPROVE_ROLE = "senior"


def publish_message(message: str, pathogen_config: PathogenConfig) -> None:
    """
    Publish a message for a given pathogen

    Args:
        message (str): The message body for publication
        pathogen_config (PathogenConfig): The configuration for the pathogen, including exchange, routing, and queue
    """

    logging.debug(
        f"Publishing message to exchange {pathogen_config.topic_exchange} with routing key {pathogen_config.topic_route}"
    )
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=AMQP_CONFIG.host)
    )
    channel = connection.channel()
    channel.exchange_declare(
        exchange=pathogen_config.topic_exchange, exchange_type="topic"
    )
    channel.queue_declare(queue=pathogen_config.topic_queue, durable=True)
    # TODO: ack_nack_callback
    channel.confirm_delivery()
    props = pika.BasicProperties(content_type="text/plain")
    try:
        channel.basic_publish(
            exchange=pathogen_config.topic_exchange,
            routing_key=pathogen_config.topic_route,
            body=message,
            properties=props,
            mandatory=True,
        )
        logging.debug(f"Message {message} published")
    except Exception:
        logging.exception(f"Message {message} not published")
        raise


def should_auto_approve(curation_data: dict) -> bool:
    """
    Whether the curation data allows for automatic approval

    Args:
        curation_data (dict): The curator information for some data

    Returns:
        bool: True for auto-approval, False for manual approval
    """

    if any(AUTO_APPROVE_ROLE in role for role in curation_data.get("roles")):
        logging.debug("Auto-approving new data")
        return True
    return False


def add_curation_data(
    partner_name: str, curation_data: dict, auto_approve: bool, cleaned_data: list[dict]
) -> None:
    """
    Add curation data

    Args:
        partner_name (str): The name of the partner data came from
        curation_data (dict): The curator information for the data
        auto_approve (bool): Whether data should be automatically approved
        cleaned_data (list[dict]): The data, after cleaning and pre-processing
    """

    logging.debug("Adding curation data")
    name = curation_data.get("name", partner_name)
    data_to_add = {"createdBy": name}
    if auto_approve:
        data_to_add["verifiedBy"] = name
    for data in cleaned_data:
        data.update(data_to_add)


def run_get_cases_job(
    pathogen_config: PathogenConfig, partner: Partner, metadata: list[tuple]
):
    """
    Get cases for a pathogen from a partner

    Args:
        pathogen_config (PathogenConfig): Pathogen configuration data
        partner (Partner): Partner configuration data
        metadata (list[tuple]): gRPC request metadata
    """

    logging.info(f"Getting cases for pathogen {pathogen_config.name}")
    proto_cases = get_partner_cases(pathogen_config.name, partner, metadata)
    dict_cases = MessageToDict(proto_cases, preserving_proto_field_name=True).get(
        "cases"
    )
    if not dict_cases:
        logging.warning(
            f"No cases obtained from partner {partner.name} for pathogen {pathogen_config.name}"
        )
        return
    logging.debug(f"New cases: {dict_cases}")
    cleaned_cases = clean_cases_data(dict_cases)
    logging.debug(f"Cleaned new cases: {cleaned_cases}")
    curation_data = get_curation_data(partner.name)
    auto_approve = should_auto_approve(curation_data)
    store_data_in_s3(
        cleaned_cases, pathogen_config.s3_bucket, f"{pathogen_config.name}.json"
    )
    add_curation_data(partner.name, curation_data, auto_approve, cleaned_cases)
    store_data_in_db(cleaned_cases, pathogen_config.cases_collection)
    if auto_approve:
        publish_message("New cases stored", pathogen_config)
    else:
        logging.debug("New cases require manual approval")


def run_estimate_rt_job(
    pathogen_config: PathogenConfig, partner: Partner, metadata: list[tuple]
):
    """
    Get R(t) estimates for a pathogen from a partner

    Args:
        pathogen_config (PathogenConfig): Pathogen configuration data
        partner (Partner): Partner configuration data
        metadata (list[tuple]): gRPC request metadata
    """

    logging.info(f"Estimating R(t) for pathogen {pathogen_config.name}")
    proto_estimates = get_partner_rt_estimates(pathogen_config.name, partner, metadata)
    dict_estimates = MessageToDict(
        proto_estimates, including_default_value_fields=True
    ).get("estimates")
    if not dict_estimates:
        logging.warning(
            f"No R(t) estimates obtained from partner {partner.name} for pathogen {pathogen_config.name}"
        )
        return
    logging.debug(f"New estimates: {dict_estimates}")
    cleaned_estimates = clean_estimates_data(dict_estimates)
    logging.debug(f"Cleaned new estimates: {cleaned_estimates}")
    curation_data = get_curation_data(partner.name)
    auto_approve = should_auto_approve(curation_data)
    store_data_in_s3(
        cleaned_estimates, pathogen_config.s3_bucket, f"{pathogen_config.name}_rt.json"
    )
    add_curation_data(partner.name, curation_data, auto_approve, cleaned_estimates)
    store_data_in_db(cleaned_estimates, pathogen_config.rt_collection)
    file_name = create_plot(cleaned_estimates, partner.location)
    store_file_in_s3(pathogen_config.s3_bucket, RT_ESTIMATES_FOLDER, file_name)
    if auto_approve:
        publish_message("New R(t) estimates stored", pathogen_config)
    else:
        logging.debug("New R(t) estimates requires manual approval")
    cleanup_file(file_name)


def run_jobs(pathogen_name: str, job_name: str):
    """
    Run a requested job for a given pathogen

    Args:
        pathogen_name (str): Name of the pathogen
        job_name (str): Name of the job
    """

    partners = PATHOGEN_DATA_SOURCES.get(pathogen_name)
    logging.info(f"Running {job_name} for {pathogen_name} on partners {partners}")
    for partner in partners:
        logging.info(
            f"Running {job_name} for {pathogen_name} with partner {partner.name}"
        )
        token = get_jwt()
        certificate = get_certificate(partner.domain_name)
        credentials = get_credentials(token, certificate)
        pathogen_config = PATHOGEN_DATA_DESTINATIONS.get(pathogen_name)
        if job_name == GET_CASES_JOB:
            run_get_cases_job(pathogen_config, partner, credentials)
        elif job_name == ESTIMATE_RT_JOB:
            run_estimate_rt_job(pathogen_config, partner, credentials)


@AUTH.verify_password
def verify_password(username: str, password: str) -> bool:
    """
    Verify a password for a given user using AWS Secrets Manager

    Args:
        username (str): User name
        password (str): User password

    Returns:
        bool: True if correct, False otherwise
    """

    secrets_client = None
    if LOCALSTACK_URL:
        secrets_client = boto3.client(
            "secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
        )
    else:
        secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)
    # FIXME: brittle
    response = secrets_client.get_secret_value(SecretId=f"{username}_api_key_password")
    secret = response.get("SecretString", "")
    if secret == password:
        return True
    return False


@APP.route("/health")
def healthcheck() -> tuple[str, int]:
    """
    Healthcheck endpoint for the service

    Returns:
        tuple: "OK" + 200 HTTP status code
    """

    return "OK", 200


@APP.route("/<string:pathogen_name>/<string:job_name>")
@AUTH.login_required
def request_work(pathogen_name: str, job_name: str) -> tuple[str, int]:
    """Summary

    Args:
        pathogen_name (str): Name of the pathogen
        job_name (str): Name of the job

    Returns:
        tuple: Message + HTTP status code
    """

    if pathogen_name not in PATHOGENS:
        return f"Jobs for {pathogen_name} not available", 404
    if job_name not in PATHOGEN_JOBS:
        return f"Job {job_name} not available", 404
    if pathogen_name not in PATHOGEN_JOBS.get(job_name):
        return f"Job {job_name} not available for pathogen {pathogen_name}", 404
    run_jobs(pathogen_name, job_name)
    return f"Submitted job {job_name} for pathogen {pathogen_name}", 200


if __name__ == "__main__":
    setup_logger()
    logging.info("Starting server")
    APP.run(FLASK_HOST, FLASK_PORT, debug=FLASK_DEBUG)
