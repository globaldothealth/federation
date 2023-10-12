"""
POC daemon script for remote dependency management
"""

import logging
from time import sleep

import boto3
import docker
import requests
import semver

from setup_localstack import setup_logger


LOCALSTACK_URL = "http://localhost:4566"
AWS_REGION = "eu-central-1"

REPO_URL = "localhost.localstack.cloud:4510"
REPO_NAME = "spike"
REPO_URI = "/".join([REPO_URL, REPO_NAME])
REGISTRY_ID = "000000000000"

LOCAL_IMAGE_NAME = "fake_partner_image"
REMOTE_IMAGE_NAME = "fake_partner_image"

LOCAL_CONTAINER_NAME = "fake_partner_container"

SERVICE_ENDPOINT = "http://localhost:5000/status"


def stop_and_remove_container() -> None:
    """
    Stop the running container and remove it
    """

    logging.info("Stopping container")
    docker_client = docker.from_env()
    container = docker_client.containers.get(LOCAL_CONTAINER_NAME)
    container.stop()
    container.remove()


def pull_image(tag: str) -> None:
    """
    Pull the partner image from the repository

    Args:
        tag (str): Partner image tag
    """

    logging.info(f"Pulling image {REPO_URI}:{tag}")
    docker_client = docker.from_env()
    docker_client.images.pull(repository=REPO_URI, tag=tag)


def start_container(version: str) -> None:
    """
    Start the container and label it with the given version

    Args:
        version (str): Semantic version used as a container label
    """

    logging.info("Starting container")
    docker_client = docker.from_env()
    docker_client.containers.run(
        LOCAL_IMAGE_NAME,
        name=LOCAL_CONTAINER_NAME,
        labels={"version": version},
        detach=True,
    )


def service_idle() -> bool:
    """
    Determine whether the service is idle

    Returns:
        bool: True if idle, False otherwise
    """

    logging.info("Checking for idle service")
    counter = 0
    while counter < 42:
        try:
            response = requests.get(SERVICE_ENDPOINT)
            if response.json().get("status") == "idle":
                logging.info("Service idle")
                return True
            logging.info("Service not idle")
            return False
        except Exception:
            logging.exception("Something went wrong trying to connect to the service")
            counter += 1
            logging.info("Waiting before reattempting")
            sleep(2)
    return False


def update_available() -> str:
    """
    Determine whether there is an updated image available

    Returns:
        str: True if update available, False otherwise
    """

    logging.info("Checking for available update")
    local_image_tag = get_local_container_version_label()
    remote_image_tag = get_latest_remote_image_tag()
    local = semver.Version.parse(local_image_tag)
    if local.compare(remote_image_tag) < 0:
        return remote_image_tag
    return None


def get_local_container_version_label() -> str:
    """
    Get the version from the running container

    Returns:
        str: Version label value
    """

    docker_client = docker.from_env()
    current_container = docker_client.containers.get(LOCAL_CONTAINER_NAME)
    return current_container.labels.get("version", "")


def get_latest_local_image_tag() -> str:
    """
    Get the latest image version tag from local images

    Returns:
        str: The latest image version tag
    """

    docker_client = docker.from_env()
    local_images = docker_client.images.list(name=REPO_URI)
    local_image_tags = []
    for image in local_images:
        for tag in image.tags:
            tag = tag.split(":")[-1]
            local_image_tags.append(tag)
    logging.debug(f"Local image tags: {local_image_tags}")
    return get_latest_semver_tag(local_image_tags)


def get_latest_remote_image_tag() -> str:
    """
    Get the latest image version tag from the repository

    Returns:
        str: The latest image version tag
    """

    ecr_client = boto3.client(
        "ecr", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
    )
    response = ecr_client.describe_images(
        registryId=REGISTRY_ID, repositoryName=REPO_NAME
    )
    remote_images = response.get("imageDetails", [])
    remote_image_tags = []
    for image in remote_images:
        for tag in image.get("imageTags", []):
            remote_image_tags.append(tag)
    logging.debug(f"Remote image tags: {remote_image_tags}")
    return get_latest_semver_tag(remote_image_tags)


def get_latest_semver_tag(tags: list[str]) -> str:
    """
    Get the latest image version tag from a list

    Args:
        tags (list[str]): A list of version tags

    Returns:
        str: The latest version tag

    Raises:
        Exception: At least one tag should follow semantic versioning
    """

    latest_tag = ""
    for tag in tags:
        if semver.Version.is_valid(tag):
            if not latest_tag:
                latest_tag = tag
            else:
                latest = semver.Version.parse(latest_tag)
                if latest.compare(tag) < 0:
                    latest_tag = tag
    if latest_tag:
        return latest_tag
    raise Exception("No semver tags")


if __name__ == "__main__":
    setup_logger()
    logging.info(f"Checking for update for image {LOCAL_IMAGE_NAME}")
    if service_idle():
        logging.debug("Service idle")
        if new_version := update_available():
            logging.info("Update available")
            stop_and_remove_container()
            pull_image(new_version)
            start_container(new_version)
            logging.info("Update complete")
        else:
            logging.info("Update not available")
    else:
        logging.debug("Service not idle")
    logging.info("Exiting")
