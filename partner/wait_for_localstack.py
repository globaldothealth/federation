import logging
from time import sleep

from data_server import get_certificate_arn
from setup_localstack import wait_for_localstack, setup_logger


WAIT_TIME = 5


def wait_for_certificate():
	logging.info("Checking for secrets in Secrets Manager")
	counter = 0
	while counter < 42:
		if get_certificate_arn():
			logging.info("Certificate exists")
			return
		logging.info(f"Did not find certificate in attempt {counter}, waiting {WAIT_TIME} seconds")
		counter += 1
		sleep(WAIT_TIME)
	logging.warning("Could not find secrets")
	raise Exception("Secrets not available")


if __name__ == "__main__":
	setup_logger()
	logging.info("Waiting for secrets")
	wait_for_localstack()
	wait_for_certificate()
