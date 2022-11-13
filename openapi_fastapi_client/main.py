from pathlib import Path
from typing import Optional

import typer
import yaml

from openapi_fastapi_client.api import Api
from openapi_fastapi_client.schema import Schema

app = typer.Typer()


@app.command()
def main(
    openapi_file: Path,
    output_path: Path,
    sync_req: Optional[bool] = typer.Option(
        True, "--sync", help="All requests to the client are synchronous."
    ),
    async_req: Optional[bool] = typer.Option(
        False, "--async", help="All requests to the client are asynchronous with aiohttp."
    ),
):
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

    api = Api(
        yaml_data["paths"],
        base_url=yaml_data.get("servers", [{"url": "http://localhost:8080"}])[0]["url"],
    )
    schema = Schema(yaml_data["components"]["schemas"])
    schema.generate_schemas()

    client_kind = "sync" if sync_req and not async_req else "async"
    api.generate_apis(schema_path="schema", client_kind=client_kind)  # type: ignore

    api.write_api(folder_path)
    schema.write_to_file(folder_path, api.query_param_schemas)
