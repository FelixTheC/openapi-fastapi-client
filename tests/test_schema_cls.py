import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from openapi_fastapi_client.schema import Schema


def test_create_schema_instance(openapi_components):
    schema = Schema(openapi_components)
    assert not schema.data  # empty on creation
    assert not schema.schema_imports  # empty on creation
    assert not schema.query_param_schemas  # empty on creation
    assert not schema.enums  # empty on creation
    assert not schema.referenced_class  # empty on creation

    assert schema.components == openapi_components


def test_create_valid_file(openapi_components, test_folder):
    schema = Schema(openapi_components)
    schema.generate_schemas()
    schema.write_to_file(test_folder)

    assert (test_folder / Path("schema.py")).exists()


def test_create_working_pydantic_models(openapi_components, test_folder):
    schema = Schema(openapi_components)
    schema.generate_schemas()
    schema.write_to_file(test_folder)

    module = importlib.import_module(".schema", ".tests." + test_folder.name)
    module_dir = dir(module)

    for obj in [
        "Address",
        "ApiResponse",
        "Category",
        "Order",
        "Pet",
        "User",
        "PetStatusEnum",
        "OrderStatusEnum",
    ]:
        assert obj in module_dir

    assert module.ApiResponse(code=123, type="example", message="example")
    with pytest.raises(ValidationError):
        module.ApiResponse(code=123, type="example")


def test_create_unique_enums(openapi_components, test_folder):
    schema = Schema(openapi_components)
    schema.generate_schemas()
    schema.write_to_file(test_folder)

    module = importlib.import_module(".schema", ".tests." + test_folder.name)
    assert module.PetStatusEnum.AVAILABLE.value == "available"
    assert module.PetStatusEnum.PENDING.value == "pending"
    assert module.PetStatusEnum.SOLD.value == "sold"

    assert module.OrderStatusEnum.PLACED.value == "placed"
    assert module.OrderStatusEnum.APPROVED.value == "approved"
    assert module.OrderStatusEnum.DELIVERED.value == "delivered"
