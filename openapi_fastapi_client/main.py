from pathlib import Path
from pprint import pprint

import yaml

from openapi_fastapi_client.api import Api
from openapi_fastapi_client.schema import Schema


def main():
    with (Path(__file__).parent / Path("openapi_mdm.yaml")).open("r") as yaml_file:
        yaml_data = yaml.load(yaml_file, Loader=yaml.CFullLoader)

    folder_path = Path("./pet_store")
    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)
        folder_path.cwd()
        with (folder_path / Path("__init__.py")).open("w") as file:
            file.write("\n")

    api = Api(yaml_data["paths"])
    schema = Schema(yaml_data["components"]["schemas"])
    schema.generate_schemas()
    schema.write_to_file(folder_path)
    # api.generate_apis(schema_path="pet_store.schema")
    # api.write_api(folder="")
    # schema.write_to_file(api.query_param_schemas)


if __name__ == '__main__':
    main()
