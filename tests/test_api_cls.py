from pathlib import Path

import pytest

from openapi_fastapi_client.api import Api


def test_create_api_instance(openapi_paths):
    api = Api(openapi_paths, "http://localhost:8080")
    assert not api.data  # empty on creation
    assert not api.schema_imports  # empty on creation
    assert not api.query_param_schemas  # empty on creation

    assert api.paths == openapi_paths
    assert api.base_url == "http://localhost:8080"


def test_create_api_instance_with_url_ending_with_slash_removes_slash(openapi_paths):
    api = Api(openapi_paths, "http://localhost:8080/")
    assert api.base_url == "http://localhost:8080"


@pytest.mark.parametrize("client_kind", (None, "sync", "async"))
def test_base_imports(example_api, client_kind):

    if client_kind:
        assert example_api.generate_base_imports(client_kind) is None
    else:
        assert example_api.generate_base_imports() is None

    if client_kind is None or client_kind == "sync":
        # default is synchronous
        assert "import requests" in example_api.data
    else:
        assert "import aiohttp" in example_api.data

    assert "from typing import Any, Optional" in example_api.data
    assert "BASE_URL = 'http://localhost:8080'" in example_api.data


def test_create_valid_api_file(example_api, test_folder, create_dummy_schema_cls):
    example_api.generate_apis(".pet_test_store.schema")
    example_api.write_api(test_folder)
    assert (test_folder / Path("api.py")).exists()
    with (test_folder / Path("api.py")).open("r") as file:
        exec(file.read(), globals(), {})
