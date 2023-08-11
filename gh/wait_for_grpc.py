import logging
from time import sleep

from aws import get_jwt
from constants import PATHOGEN_A, PartnerA
from grpc_client import get_metadata, get_partner_cases
from util import setup_logger


WAIT_TIME = 2
MAX_ATTEMPTS = 42


def wait_for_grpc():
	logging.info("Waiting for gRPC")
	for _ in range(MAX_ATTEMPTS):
		try:
			token = get_jwt()
			metadata = get_metadata(token)
			_ = get_partner_cases(PATHOGEN_A, PartnerA, metadata)
			logging.info("gRPC ready")
			return
		except Exception:
			logging.exception("Could not get cases from partner, retrying")
			sleep(WAIT_TIME)
	raise Exception(f"gRPC not ready in {WAIT_TIME * MAX_ATTEMPTS} seconds")


if __name__ == "__main__":
	setup_logger()
	wait_for_grpc()
