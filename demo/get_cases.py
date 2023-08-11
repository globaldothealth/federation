from util import PATHOGEN_A, get_data


KEY = "cases"

QUERY = f"""
    query Cases {{
        {KEY}(pathogen: "{PATHOGEN_A}") {{
            locationInformation
        }}
    }}
"""


def get_cases():
    print("Checking for cases in GraphQL service")
    estimates = get_data(QUERY, KEY)
    print(f"Result: {estimates}")


if __name__ == "__main__":
    get_cases()
