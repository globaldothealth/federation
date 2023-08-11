import logging
import os
import sys


ESTIMATE_INT_FIELDS = ["cases"]
ESTIMATE_FLOAT_FIELDS = ["rMean", "rVar", "qLower", "qUpper"]


def setup_logger() -> None:
    h = logging.StreamHandler(sys.stdout)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(h)
    rootLogger.setLevel(logging.DEBUG)


def cleanup_file(file_name: str) -> None:
    logging.info(f"Removing {file_name}")
    if os.path.exists(file_name):
        os.remove(file_name)
        logging.debug(f"Removed {file_name}")
    logging.debug(f"Could not find {file_name}")


def clean_cases_data(cases_data):
    clean_data = []
    for case in cases_data:
        clean_case = {}
        for k, v in case.items():
            clean_case[k] = v
        clean_data.append(clean_case)

    return clean_data


def clean_estimates_data(estimates_data):
    clean_data = []
    for estimate in estimates_data:
        clean_estimate = {}
        for k, v in estimate.items():
            if k in ESTIMATE_INT_FIELDS:
                clean_estimate[k] = int(v)
            elif k in ESTIMATE_FLOAT_FIELDS:
                clean_estimate[k] = float(v)
            else:
                clean_estimate[k] = v
        clean_data.append(clean_estimate)

    return clean_data
