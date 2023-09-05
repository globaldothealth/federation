import logging
from time import sleep

import boto3
import docker

from setup_localstack import setup_logger


LOCALSTACK_URL = "http://localhost:4566"
AWS_REGION = "eu-central-1"

REPO_URL = "localhost.localstack.cloud:4510"
REPO_NAME = "spike"
REPO_URI = "/".join([REPO_URL, REPO_NAME])
REGISTRY_ID = "000000000000"
IMAGE_PATH = "../partner"
IMAGE_NAME = "fake_partner_image"
VERSION_TAG_A = "0.1.0"
VERSION_TAG_B = "0.2.0"
DOCKER_CLIENT = docker.from_env()


def wait_for_repo():
	logging.info("Waiting for ECR repo")
	ecr_client = boto3.client("ecr", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)
	counter = 0
	while counter < 42:
		try:
			response = ecr_client.describe_repositories(registryId=REGISTRY_ID, repositoryNames=[REPO_NAME])
			if response.get("repositories"):
				return
		except Exception:
			logging.exception(f"An exception happened when trying to access {REPO_URI}, retrying")
		counter += 1
		sleep(5)
	raise Exception("ECR repo not available")


def setup_repo():
	logging.info(f"Pushing {IMAGE_NAME} with tag {VERSION_TAG_A} to repo {REPO_URI}")
	image = DOCKER_CLIENT.images.build(path=IMAGE_PATH, tag=IMAGE_NAME)[0]
	image.tag(REPO_URI, VERSION_TAG_A)
	DOCKER_CLIENT.api.push(REPO_URI)
	logging.info("Pushed image")
	logging.info(f"Pushing {IMAGE_NAME} with tag {VERSION_TAG_B} to repo {REPO_URI}")
	image.tag(REPO_URI, VERSION_TAG_B)
	DOCKER_CLIENT.api.push(REPO_URI)
	logging.info("Pushed image")


if __name__ == "__main__":
	setup_logger()
	wait_for_repo()
	setup_repo()
