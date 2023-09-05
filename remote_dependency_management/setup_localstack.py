import logging
import os
import sys
from time import sleep

import boto3
import requests


LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION")

ECR_CLIENT = boto3.client("ecr", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)

REPO_NAME = "spike"


def setup_logger():
	h = logging.StreamHandler(sys.stdout)
	rootLogger = logging.getLogger()
	rootLogger.addHandler(h)
	rootLogger.setLevel(logging.DEBUG)


def wait_for_localstack():
	logging.info("Waiting for localstack")
	healthcheck_url = "".join([LOCALSTACK_URL, "/_localstack/health"])
	counter = 0
	while counter < 42:
		try:
			response = requests.get(healthcheck_url)
			ecr_status = response.json().get("services", {}).get("ecr")
			if ecr_status == "running":
				return
			# Lazy loading
			_ = ECR_CLIENT.describe_repositories()
		except requests.exceptions.ConnectionError:
			pass
		counter += 1
		sleep(5)
	raise Exception("Localstack not available")


def setup_ecr():
	logging.info("Setting up ECR repository")
	response = ECR_CLIENT.create_repository(repositoryName=REPO_NAME)
	repo_uri = response.get("repository", {}).get("repositoryUri")
	logging.info(f"Repo set up with URI: {repo_uri}")


if __name__ == "__main__":
	setup_logger()
	logging.info("Starting script")
	wait_for_localstack()
	setup_ecr()
	logging.info("Script completed")
