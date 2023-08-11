from util import PARTNER_A_NAME, PATHOGEN_A, GET_CASES_JOB, get_api_key, send_work_request


def request_cases():
    key = get_api_key(PARTNER_A_NAME)
    send_work_request(PARTNER_A_NAME, key, PATHOGEN_A, GET_CASES_JOB)


if __name__ == "__main__":
    request_cases()
