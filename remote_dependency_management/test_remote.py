"""
Test suite for remote dependency management system component
"""

import os
from time import sleep

import boto3
import docker
import pytest
import semver


CONTAINER_NAME = "fake_partner_container"

LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL", "http://localhost:4566")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")

REGISTRY_ID = "000000000000"
REPO_NAME = "spike"

WAIT_TIME = 5
RETRIES = 4


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


def test_new_image_triggers_pull_and_restart():
    """
    After updating a remote image with a version bump the local container should update
    """

    docker_client = docker.from_env()
    current_container = docker_client.containers.get(CONTAINER_NAME)
    current_container_version = current_container.labels.get("version")
    ecr_client = boto3.client(
        "ecr", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION
    )
    response = ecr_client.describe_repositories(registryId=REGISTRY_ID)
    response = ecr_client.list_images(
        registryId=REGISTRY_ID,
        repositoryName=REPO_NAME,
    )
    ecr_images = response.get("imageIds", [])
    ecr_image_version = ecr_images[0].get("imageTag")
    if (
        current_container_version != "0.1.0"
        and current_container_version != ecr_image_version
    ):
        pytest.fail(
            f"Container version {current_container_version} and/or ECR image version {ecr_image_version} wrong"
        )

    updated = False
    for _ in range(RETRIES):
        current_container = docker_client.containers.get(CONTAINER_NAME)
        current_container_version = current_container.labels.get("version")
        ecr_images = response.get("imageIds", [])
        remote_image_tags = []
        for image in ecr_images:
            if tag := image.get("imageTag"):
                remote_image_tags.append(tag)
        ecr_image_version = get_latest_semver_tag(remote_image_tags)
        if (
            current_container_version != "0.1.0"
            and current_container_version == ecr_image_version
        ):
            updated = True
            break
        sleep(WAIT_TIME)
    if not updated:
        pytest.fail("Timed out waiting for updated container version")
