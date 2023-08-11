from util import PATHOGEN_A, get_data

KEY = "estimates"

QUERY = f"""
    query RtEstimates {{
        {KEY}(pathogen: "{PATHOGEN_A}") {{
            date
            cases
            rMean
            rVar
            qLower
            qUpper
        }}
    }}
"""


def get_rt_estimates():
    print("Checking for R(t) estimates in GraphQL service")
    estimates = get_data(QUERY, KEY)
    print(f"Result: {estimates}")


if __name__ == "__main__":
    get_rt_estimates()
