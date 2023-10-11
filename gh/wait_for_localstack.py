import logging
from time import sleep

from aws import get_certificate
from constants import PartnerA
from setup_localstack import wait_for_localstack
from util import setup_logger


WAIT_TIME = 5


def wait_for_certificates():
	logging.info("Checking for certificate in ACM")
	counter = 0
	while counter < 42:
		certificate = get_certificate(PartnerA.domain_name)
		logging.info(f"Certificate: {certificate}")
		if certificate:
			logging.info("Found certificate")
			return
		logging.info(f"Did not find certificate in attempt {counter}, waiting {WAIT_TIME} seconds")
		counter += 1
		sleep(WAIT_TIME)
	logging.warning("Could not find certificate")
	raise Exception("Certificate not available")


if __name__ == "__main__":
	setup_logger()
	logging.info("Waiting for secrets")
	wait_for_localstack()
	wait_for_certificates()
