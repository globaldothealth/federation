import os

from util import approve_data


DB_COLLECTION = os.environ.get("PATHOGEN_A", "")


if __name__ == "__main__":
	approve_data(DB_COLLECTION)
