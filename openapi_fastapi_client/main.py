from pathlib import Path

import typer
import yaml

from openapi_fastapi_client.api import Api
from openapi_fastapi_client.schema import Schema

app = typer.Typer()


@app.command()
def main(openapi_file: Path, output_path: Path):
    if not openapi_file.exists():
        raise FileNotFoundError(f"{openapi_file} does not exists.")

    with openapi_file.open("r") as yaml_file:
        yaml_data = yaml.load(yaml_file, Loader=yaml.CFullLoader)

    folder_path = output_path
    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)
        folder_path.cwd()
        with (folder_path / Path("__init__.py")).open("w") as file:
            file.write("\n")

    api = Api(yaml_data["paths"])
    schema = Schema(yaml_data["components"]["schemas"])
    schema.generate_schemas()
    api.generate_apis(schema_path="schema")
    api.write_api(folder_path)
    schema.write_to_file(folder_path, api.query_param_schemas)
