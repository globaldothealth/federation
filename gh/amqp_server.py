import logging
import os

import boto3
from cryptography.fernet import Fernet
from flask import Flask
from flask_httpauth import HTTPBasicAuth
from google.protobuf.json_format import MessageToDict
import pika

from aws import get_jwt, store_data_in_s3, store_file_in_s3, update_encryption_key
from db import store_data_in_db, get_curation_data
from graphics import create_plot
from grpc_client import get_metadata, get_partner_cases, get_partner_rt_estimates
from util import setup_logger, cleanup_file, clean_cases_data, clean_estimates_data
from constants import (PathogenConfig, Partner, AMQP_CONFIG, PATHOGEN_JOBS, PATHOGEN_DATA_SOURCES,
	PATHOGENS, PATHOGEN_DATA_DESTINATIONS, GET_CASES_JOB, ESTIMATE_RT_JOB, RT_ESTIMATES_FOLDER,
	LOCALSTACK_URL, AWS_REGION
)


APP = Flask(__name__)
AUTH = HTTPBasicAuth()

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = os.environ.get("FLASK_PORT", 5000)
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", False)

SECRETS_CLIENT = boto3.client("secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)

AUTO_APPROVE_ROLE = "senior"


def decrypt_response(encrypted_response, encryption_key):
	decrypted_response = []
	fernet = Fernet(encryption_key)
	for elem in encrypted_response:
		decrypted = {}
		for k, v in elem.items():
			decrypted[k] = fernet.decrypt(str(v).encode()).decode()
		decrypted_response.append(decrypted)
	return decrypted_response


def publish_message(message: str, pathogen_config: PathogenConfig) -> None:
	logging.debug(f"Publishing message to exchange {pathogen_config.topic_exchange} with routing key {pathogen_config.topic_route}")
	connection = pika.BlockingConnection(pika.ConnectionParameters(host=AMQP_CONFIG.host))
	channel = connection.channel()
	channel.exchange_declare(exchange=pathogen_config.topic_exchange, exchange_type="topic")
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
			mandatory=True
		)
		logging.debug(f"Message {message} published")
	except Exception:
		logging.exception(f"Message {message} not published")
		raise


def should_auto_approve(curation_data: dict) -> bool:
	if any(AUTO_APPROVE_ROLE in role for role in curation_data.get("roles")):
		logging.debug("Auto-approving new data")
		return True
	return False


def add_curation_data(partner_name: str, curation_data: dict, auto_approve: bool, cleaned_data: list[dict]):
	logging.debug("Adding curation data")
	name = curation_data.get("name", partner_name)
	data_to_add = {
		"createdBy": name
	}
	if auto_approve:
		data_to_add["verifiedBy"] = name
	for data in cleaned_data:
		data.update(data_to_add)


def run_get_cases_job(pathogen_config: PathogenConfig, partner: Partner, metadata: list[tuple], key: bytes):
	logging.info(f"Getting cases for pathogen {pathogen_config.name}")
	proto_cases = get_partner_cases(pathogen_config.name, partner, metadata)
	dict_cases = MessageToDict(proto_cases, preserving_proto_field_name=True).get("cases")
	logging.debug(f"Encrypted new cases: {dict_cases}")
	# TODO: If no data log critical and skip
	decryped_cases = decrypt_response(dict_cases, key)
	logging.debug(f"Decrypted new cases: {decryped_cases}")
	cleaned_cases = clean_cases_data(decryped_cases)
	logging.debug(f"Cleaned new cases: {cleaned_cases}")
	curation_data = get_curation_data(partner.name)
	auto_approve = should_auto_approve(curation_data)
	store_data_in_s3(cleaned_cases, pathogen_config.s3_bucket, f"{pathogen_config.name}.json")
	add_curation_data(partner.name, curation_data, auto_approve, cleaned_cases)
	store_data_in_db(cleaned_cases, pathogen_config.cases_collection)
	# TODO: only publish if created by senior curator
	if auto_approve:
		publish_message("New cases stored", pathogen_config)
	else:
		logging.debug("New cases require manual approval")


def run_estimate_rt_job(pathogen_config: PathogenConfig, partner: Partner, metadata: list[tuple], key: bytes):
	logging.info(f"Estimating R(t) for pathogen {pathogen_config.name}")
	proto_estimates = get_partner_rt_estimates(pathogen_config.name, partner, metadata)
	dict_estimates = MessageToDict(proto_estimates, including_default_value_fields=True).get("estimates")
	logging.debug(f"Encrypted new estimates: {dict_estimates}")
	# TODO: If no data log critical and skip
	decryped_estimates = decrypt_response(dict_estimates, key)
	logging.debug(f"Decrypted new estimates: {decryped_estimates}")
	cleaned_estimates = clean_estimates_data(decryped_estimates)
	logging.debug(f"Cleaned new estimates: {cleaned_estimates}")
	curation_data = get_curation_data(partner.name)
	auto_approve = should_auto_approve(curation_data)
	store_data_in_s3(cleaned_estimates, pathogen_config.s3_bucket, f"{pathogen_config.name}_rt.json")
	add_curation_data(partner.name, curation_data, auto_approve, cleaned_estimates)
	store_data_in_db(cleaned_estimates, pathogen_config.rt_collection)
	file_name = create_plot(cleaned_estimates, partner.name)
	store_file_in_s3(pathogen_config.s3_bucket, RT_ESTIMATES_FOLDER, file_name)
	# TODO: only publish if created by senior curator
	if auto_approve:
		publish_message("New R(t) estimates stored", pathogen_config)
	else:
		logging.debug("New R(t) estimates requires manual approval")
	cleanup_file(file_name)


def run_jobs(pathogen_name: str, job_name: str):
	logging.info(f"Running {job_name} for {pathogen_name}")
	for partner in PATHOGEN_DATA_SOURCES.get(pathogen_name):
		logging.info(f"Running {job_name} for {pathogen_name} with partner {partner.name}")
		token = get_jwt()
		metadata = get_metadata(token)
		pathogen_config = PATHOGEN_DATA_DESTINATIONS.get(pathogen_name)
		key = Fernet.generate_key()
		update_encryption_key(partner.name, key)
		if (job_name == GET_CASES_JOB):
			run_get_cases_job(pathogen_config, partner, metadata, key)
		elif (job_name == ESTIMATE_RT_JOB):
			run_estimate_rt_job(pathogen_config, partner, metadata, key)


@AUTH.verify_password
def verify_password(username, password):
	# FIXME: brittle
	response = SECRETS_CLIENT.get_secret_value(SecretId=f"{username}_api_key_password")
	secret = response.get("SecretString", "")
	if secret == password:
		return True
	return False


@APP.route("/health")
def healthcheck():
	return "OK", 200


@APP.route('/<string:pathogen_name>/<string:job_name>')
@AUTH.login_required
def request_work(pathogen_name: str, job_name: str):
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
