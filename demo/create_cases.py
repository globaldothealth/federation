import requests


SIM_HOST = "localhost"
SIM_PORT = 5001
SIM_ENDPOINT = f"http://{SIM_HOST}:{SIM_PORT}/cases"


LOCATION = "USA"
OUTCOME = "recovered"
HOSPITALIZED = "N"


def create_cases():
    cases = []

    for day in range(1, 31):
        date_confirmation = f"01-{day}-2023"
        for _ in range(50):
            cases.append({
                "location": LOCATION,
                "outcome": OUTCOME,
                "date_confirmation": date_confirmation,
                "hospitalized": HOSPITALIZED
            })

    response = requests.post(SIM_ENDPOINT, json=cases)
    print(response)


if __name__ == "__main__":
    create_cases()
