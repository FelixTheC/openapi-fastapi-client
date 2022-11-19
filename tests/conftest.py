from pathlib import Path
from string import Template

import pytest
import yaml

BASE_TEST_DIR = Path(__file__).parent


@pytest.fixture(scope="session")
def openapi_file() -> Path:
    return BASE_TEST_DIR / Path("openapi.yaml")


@pytest.fixture(scope="session")
def openapi_paths(openapi_file) -> dict:
    with openapi_file.open("r") as yaml_file:
        yaml_data = yaml.load(yaml_file, Loader=yaml.CFullLoader)
    return yaml_data["paths"]


@pytest.fixture(scope="session")
def openapi_components(openapi_file) -> dict:
    with openapi_file.open("r") as yaml_file:
        yaml_data = yaml.load(yaml_file, Loader=yaml.CFullLoader)
    return yaml_data["components"]["schemas"]


@pytest.fixture(scope="function")
def example_api(openapi_paths) -> object:
    from openapi_fastapi_client.api import Api

    return Api(openapi_paths, "http://localhost:8080", "pet")


@pytest.fixture(scope="function")
def test_folder():
    test_dir = BASE_TEST_DIR / Path("pet_test_store")
    test_dir.mkdir(exist_ok=True, parents=True)
    file = test_dir / Path("__init__.py")
    file.write_text("\n")
    yield test_dir
    for file in test_dir.glob("*"):
        if file.is_file():
            file.unlink()
    try:
        test_dir.rmdir()
    except OSError:
        pass


@pytest.fixture(scope="function")
def create_dummy_schema_cls(test_folder):
    cls_template = Template(
        """class $cls_name:
        pass
        """
    )
    cls_names = [
        "ApiResponse",
        "Order",
        "Pet",
        "PetGetFindPetsByStatusQuery",
        "PetGetFindPetsByTagsQuery",
        "PetPostUpdatePetWithFormQuery",
        "PetPostUploadFileQuery",
        "User",
        "UserGetLoginUserQuery",
    ]
    classes = [cls_template.substitute(cls_name=obj) for obj in cls_names]
    file = test_folder / Path("schema.py")
    file.write_text("\n\n".join(classes))
