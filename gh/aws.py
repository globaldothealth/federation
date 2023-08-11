import logging
import json

import boto3

from constants import LOCALSTACK_URL, AWS_REGION, COGNITO_USER_NAME, COGNITO_USER_PASSWORD


def get_encryption_key(partner_name: str) -> bytes:
	logging.debug(f"Getting encryption key for partner {partner_name}")
	secrets_client = boto3.client("secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)
	response = secrets_client.get_secret_value(SecretId=partner_name)
	return response.get("SecretBinary", b"")


def update_encryption_key(partner_name: str, key: bytes):
	logging.debug(f"Updating encryption key for partner {partner_name}")
	secrets_client = boto3.client("secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)
	secrets_client.put_secret_value(SecretId=partner_name, SecretBinary=key)


def get_jwt() -> str:
	logging.debug("Getting JWT")
	cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)
	if LOCALSTACK_URL:
		logging.debug("Using localstack Cognito service")
		cognito_client = boto3.client("cognito-idp", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)

	# List user pools
	response = cognito_client.list_user_pools(
		MaxResults=1
	)
	logging.debug(f"User pools: {response.get('UserPools')}")
	pool_id = response.get("UserPools", [])[0].get("Id")

	# List user pool clients
	response = cognito_client.list_user_pool_clients(
		UserPoolId=pool_id,
		MaxResults=1
	)
	client_id = response.get("UserPoolClients")[0].get("ClientId")

	# Get JWT
	response = cognito_client.initiate_auth(
		AuthFlow="USER_PASSWORD_AUTH",
		AuthParameters={
			"USERNAME": COGNITO_USER_NAME,
			"PASSWORD": COGNITO_USER_PASSWORD
		},
		ClientId=client_id
	)
	token = response.get("AuthenticationResult", {}).get("AccessToken")

	return token


def store_data_in_s3(data: list, bucket_name: str, file_name: str) -> None:
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
	logging.info(f"Storing file {file_name} in bucket {bucket_name}")
	try:
		s3 = boto3.client("s3")
		if LOCALSTACK_URL:
			s3 = boto3.client("s3", endpoint_url=LOCALSTACK_URL)
		s3.upload_file(Filename=file_name, Bucket=bucket_name, Key=f"{folder}/{file_name}")
	except Exception:
		logging.exception("An error occurred while trying to store file in S3")
		raise
	logging.info("Stored file in S3")
