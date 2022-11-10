from pathlib import Path
from pprint import pprint

import yaml

from openapi_fastapi_client.api import Api
from openapi_fastapi_client.schema import Schema


def main():
    with (Path(__file__).parent / Path("openapi_mdm.yaml")).open("r") as yaml_file:
        yaml_data = yaml.load(yaml_file, Loader=yaml.CFullLoader)
    api = Api(yaml_data["paths"])
    schema = Schema(yaml_data["components"]["schemas"])
    schema.generate_schemas()
    # api.generate_apis(schema_path="pet_store.schema")
    # api.write_api(folder="./pet_store")


if __name__ == '__main__':
    main()
