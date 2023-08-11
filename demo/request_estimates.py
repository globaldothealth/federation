from util import PARTNER_A_NAME, PATHOGEN_A, ESTIMATE_RT_JOB, get_api_key, send_work_request


def request_cases():
    key = get_api_key(PARTNER_A_NAME)
    send_work_request(PARTNER_A_NAME, key, PATHOGEN_A, ESTIMATE_RT_JOB)


if __name__ == "__main__":
    request_cases()
