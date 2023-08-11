import os
from unittest.mock import patch

from data_client import get_api_key, send_work_request


PATHOGEN_A = os.environ.get("PATHOGEN_A")


@patch("data_client.requests.get", autospec=True)
def test_api_key_changes(mock_get):
	key_before = get_api_key()
	send_work_request(key_before, PATHOGEN_A, "get_cases")
	key_after = get_api_key()
	assert key_before != key_after
