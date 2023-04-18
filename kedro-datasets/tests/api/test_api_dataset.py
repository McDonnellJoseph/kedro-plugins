# pylint: disable=no-member
import json
import socket

import pytest
import requests
import requests_mock
from kedro.io.core import DataSetError

from kedro_datasets.api import APIDataSet

POSSIBLE_METHODS = ["GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", "DELETE"]

TEST_URL = "http://example.com/api/test"
TEST_TEXT_RESPONSE_DATA = "This is a response."
TEST_JSON_RESPONSE_DATA = [{"key": "value"}]

TEST_PARAMS = {"param": "value"}
TEST_URL_WITH_PARAMS = TEST_URL + "?param=value"

TEST_HEADERS = {"key": "value"}

TEST_SAVE_DATA = [json.dumps({"key1": "info1", "key2": "info2"})]


@pytest.mark.parametrize("method", POSSIBLE_METHODS)
class TestAPIDataSet:
    @pytest.fixture
    def requests_mocker(self):
        with requests_mock.Mocker() as mock:
            yield mock

    def test_successfully_load_with_response(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text=TEST_TEXT_RESPONSE_DATA,
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.text == TEST_TEXT_RESPONSE_DATA

    def test_successful_json_load_with_response(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=method,
            json=TEST_JSON_RESPONSE_DATA,
            headers=TEST_HEADERS,
        )
        requests_mocker.register_uri(
            method,
            TEST_URL,
            headers=TEST_HEADERS,
            text=json.dumps(TEST_JSON_RESPONSE_DATA),
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.json() == TEST_JSON_RESPONSE_DATA

    def test_http_error(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text="Nope, not found",
            status_code=requests.codes.FORBIDDEN,
        )

        with pytest.raises(DataSetError, match="Failed to fetch data"):
            api_data_set.load()

    def test_socket_error(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(method, TEST_URL_WITH_PARAMS, exc=socket.error)

        with pytest.raises(DataSetError, match="Failed to connect"):
            api_data_set.load()

    def test_successful_save(self, requests_mocker, method):
        """
        When we want to save some data on a server
        Given an APIDataSet class
        Then check we get a response
        """
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=method,
            params=TEST_PARAMS,
            headers=TEST_HEADERS,
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            status_code=requests.codes.ok,
        )
        response = api_data_set._save(TEST_SAVE_DATA)

        assert isinstance(response, requests.Response)

    def test_successful_save_with_json(self, requests_mocker, method):
        """
        When we want to save with json parameters
        Given an APIDataSet class
        Then check we get a response
        """
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=method,
            json=TEST_JSON_RESPONSE_DATA,
            headers=TEST_HEADERS,
        )
        requests_mocker.register_uri(
            method,
            TEST_URL,
            headers=TEST_HEADERS,
            text=json.dumps(TEST_JSON_RESPONSE_DATA),
        )
        response_list = api_data_set._save(TEST_SAVE_DATA)

        assert isinstance(response_list, requests.Response)

        response_dict = api_data_set._save({"item1": "key1"})
        assert isinstance(response_dict, requests.Response)

        response_json = api_data_set._save(TEST_SAVE_DATA[0])
        assert isinstance(response_json, requests.Response)

    def test_save_http_error(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=method,
            params=TEST_PARAMS,
            headers=TEST_HEADERS,
            save_args={"method": "POST", "chunk_size": 2},
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text="Nope, not found",
            status_code=requests.codes.FORBIDDEN,
        )

        with pytest.raises(DataSetError, match="Failed to send data"):
            api_data_set.save(TEST_SAVE_DATA)

    def test_save_socket_error(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(method, TEST_URL_WITH_PARAMS, exc=socket.error)

        with pytest.raises(
            DataSetError, match="Failed to connect to the remote server"
        ):
            api_data_set.save(TEST_SAVE_DATA)

    def test_exists_http_error(self, requests_mocker, method):
        """
        In case of an unexpected HTTP error,
        ``exists()`` should not silently catch it.
        """
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text="Nope, not found",
            status_code=requests.codes.FORBIDDEN,
        )
        with pytest.raises(DataSetError, match="Failed to fetch data"):
            api_data_set.exists()

    def test_exists_ok(self, requests_mocker, method):
        """
        If the file actually exists and server responds 200,
        ``exists()`` should return True
        """
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text=TEST_TEXT_RESPONSE_DATA,
        )

        assert api_data_set.exists()

    def test_credentials_auth_error(self, method):
        """
        If ``auth`` and ``credentials`` are both provided,
        the constructor should raise a ValueError.
        """
        with pytest.raises(ValueError, match="both auth and credentials"):
            APIDataSet(url=TEST_URL, method=method, auth=[], credentials=[])

    @pytest.mark.parametrize("auth_kwarg", ["auth", "credentials"])
    @pytest.mark.parametrize(
        "auth_seq",
        [
            ("username", "password"),
            ["username", "password"],
            (e for e in ["username", "password"]),  # Generator.
        ],
    )
    def test_auth_sequence(self, requests_mocker, method, auth_seq, auth_kwarg):
        """
        ``auth`` and ``credentials`` should be able to be any Iterable.
        """
        kwargs = {
            "url": TEST_URL,
            "method": method,
            "params": TEST_PARAMS,
            "headers": TEST_HEADERS,
            auth_kwarg: auth_seq,
        }

        api_data_set = APIDataSet(**kwargs)
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text=TEST_TEXT_RESPONSE_DATA,
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.text == TEST_TEXT_RESPONSE_DATA
