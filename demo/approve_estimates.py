import os

from util import approve_data


DB_COLLECTION = "".join(os.environ.get("PATHOGEN_A", ""), "_RT")


if __name__ == "__main__":
	approve_data(DB_COLLECTION)
