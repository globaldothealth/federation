import os
from time import sleep

import pika


AMQP_HOST = os.environ.get("AMQP_HOST")

WAIT_TIME = 10
RETRIES = 5


def wait_for_rabbitmq():
    current_attempt = 0
    while current_attempt < RETRIES:
        try:
            _ = pika.BlockingConnection(pika.ConnectionParameters(host=AMQP_HOST))
            return
        except pika.exceptions.AMQPConnectionError:
            print(f"Could not connect to RabbitMQ server at {AMQP_HOST}. Retrying in {WAIT_TIME} seconds.")
            sleep(WAIT_TIME)
            current_attempt += 1
    raise Exception("Exiting now.")


if __name__ == "__main__":
    wait_for_rabbitmq()
