import json
import os

import boto3
from pymongo import MongoClient
import requests
from requests.auth import HTTPBasicAuth


LOCALSTACK_URL = os.environ.get("LOCALSTACK_URL", "http://localhost:4566/")
AWS_REGION = os.environ.get("AWS_REGION", "eu-central-1")

DB_CONNECTION = os.environ.get("DB_CONNECTION", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test")

GH_WORK_REQUEST_URL = os.environ.get("GH_WORK_REQUEST_URL", "http://localhost:5000")
GRAPHQL_SERVICE = "http://localhost:8000/graphql"

PARTNER_A_NAME = os.environ.get("PARTNER_A_NAME", "agency_a")
PATHOGEN_A = os.environ.get("PATHOGEN_A")
ESTIMATE_RT_JOB = "EstimateRt"
GET_CASES_JOB = "GetCases"
MODEL_COMPARISONS_JOB = "CompareModels"

SECRETS_CLIENT = boto3.client("secretsmanager", endpoint_url=LOCALSTACK_URL, region_name=AWS_REGION)


def get_api_key(partner_name: str) -> str:
	response = SECRETS_CLIENT.get_secret_value(SecretId=f"{partner_name}_api_key_password")
	return response.get("SecretString")


def send_work_request(partner_name: str, key: str, pathogen: str, job: str):
	auth = HTTPBasicAuth(partner_name, key)
	url = f"{GH_WORK_REQUEST_URL}/{pathogen}/{job}"
	_ = requests.get(url, auth=auth)


def get_data(query: str, key: str) -> list[dict]:
	response = requests.get(url=GRAPHQL_SERVICE, params={"query": query})
	return json.loads(response.text).get(key)


def approve_data(collection_name: str):
	client = MongoClient(DB_CONNECTION)
	db = client[DB_NAME]
	collection = db[collection_name]
	collection.update_many(
		{},
		{"$set": {"verifiedBy": "someoneSenior"}},
		upsert=False,
		array_filters=None
	)
